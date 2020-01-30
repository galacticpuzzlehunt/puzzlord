import datetime

from django.contrib.auth.decorators import login_required, permission_required

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.db.models import Exists, F, OuterRef, Count, Q
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
import django.urls as urls

import django.forms as forms

import puzzlord.settings as settings

from puzzle_editing.models import UserProfile, Puzzle, PuzzleComment, TestsolveSession, TestsolveParticipation, TestsolveGuess, PuzzleAnswer, Round, is_spoiled_on, is_author_on, is_discussion_editor_on, is_factchecker_on, is_postprodder_on
import puzzle_editing.status as status

import puzzle_editing.messaging as messaging

def get_sessions_with_joined_and_current(user):
    return TestsolveSession.objects.annotate(
        joined=Exists(
            TestsolveParticipation.objects.filter(
                session=OuterRef('pk'),
                user=user,
            )
        ),
        current=Exists(
            TestsolveParticipation.objects.filter(
                session=OuterRef('pk'),
                user=user,
                ended=None,
            )
        ),
    )

def get_full_display_name(user):
    try:
        if user.profile.display_name:
            return "{} ({})".format(user.profile.display_name, user.username)
        else:
            return user.username
    except UserProfile.DoesNotExist:
        return user.username

def index(request):
    user = request.user

    if not request.user.is_authenticated:
        return render(request, 'index_not_logged_in.html')

    blocked_on_author_puzzles = Puzzle.objects.filter(
        authors=user,
        status__in=status.STATUSES_BLOCKED_ON_AUTHORS,
    )
    current_sessions = get_sessions_with_joined_and_current(user).filter(joined=True, current=True)
    factchecking = Puzzle.objects.filter(
        status=status.NEEDS_FACTCHECK,
        factcheckers=user
    )
    postprodding = Puzzle.objects.filter(
        status=status.NEEDS_POSTPROD,
        postprodders=user
    )

    return render(request, 'index.html', {
        'blocked_on_author_puzzles': blocked_on_author_puzzles,
        'current_sessions': current_sessions,
        'factchecking': factchecking,
        'postprodding': postprodding,
    })

class MarkdownTextarea(forms.Textarea):
    template_name = 'widgets/markdown_textarea.html'

# based on UserCreationForm from Django source
class RegisterForm(forms.ModelForm):
    """
    A form that creates a user, with no privileges, from the given username and
    password.
    """

    password1 = forms.CharField(label="Password",
        widget=forms.PasswordInput)
    password2 = forms.CharField(label="Password confirmation",
        widget=forms.PasswordInput,
        help_text="Enter the same password as above, for verification.")
    email = forms.EmailField(label="Email address",
        required=False,
        help_text="Optional, but you'll get useful email notifications.")

    site_password = forms.CharField(label="Site password",
        widget=forms.PasswordInput,
        help_text="Get this password from the Discord.")

    display_name = forms.CharField(label="Display name", required=False, help_text="(optional)")
    discord_username = forms.CharField(label="Discord username",
        help_text="(required) Discord username and tag (e.g. example#1234)")
    bio = forms.CharField(widget=MarkdownTextarea,
        required=False,
        help_text="(optional) Tell us about yourself. What kinds of puzzle genres or subject matter do you like?")

    class Meta:
        model = User
        fields = ("username","email")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                "The two password fields didn't match.",
                code='password_mismatch',
            )
        return password2

    def clean_site_password(self):
        site_password = self.cleaned_data.get("site_password")
        if site_password and site_password != settings.SITE_PASSWORD:
            raise forms.ValidationError(
                "The site password was incorrect.",
                code='password_mismatch',
            )
        return site_password

    def save(self, commit=True):
        user = super(RegisterForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()

            profile = UserProfile(
                user=user,
                display_name=self.cleaned_data["display_name"],
                discord_username=self.cleaned_data["discord_username"],
                bio=self.cleaned_data["bio"],
            )
            profile.save()
        return user

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/')
        else:
            return render(request, 'register.html', { "form": form })
    else:
        form = RegisterForm()
        return render(request, 'register.html', { "form": form })

class AccountForm(forms.Form):
    email = forms.EmailField(label="Email address",
        required=False,
        help_text="Optional, but you'll get useful email notifications.")

    display_name = forms.CharField(label="Display name", required=False)
    discord_username = forms.CharField(label="Discord username",
        help_text="(required) Discord username and tag (e.g. example#1234)")
    bio = forms.CharField(widget=MarkdownTextarea,
        required=False,
        help_text="(optional) Tell us about yourself. What kinds of puzzle genres or subject matter do you like?")

@login_required
def account(request):
    user = request.user

    if request.method == 'POST':
        form = AccountForm(request.POST)
        if form.is_valid():
            user.email = form.cleaned_data['email']
            user.save()

            try:
                profile = user.profile
                profile.display_name = form.cleaned_data['display_name']
                profile.discord_username = form.cleaned_data['discord_username']
                profile.bio = form.cleaned_data['bio']
                profile.save()
            except UserProfile.DoesNotExist:
                profile = UserProfile(
                    user=user,
                    display_name=form.cleaned_data['display_name'],
                    discord_username=form.cleaned_data['discord_username'],
                    bio=form.cleaned_data['bio'],
                )
                profile.save()

            return render(request, 'account.html', { "form": form, 'success': True })
        else:
            return render(request, 'account.html', { "form": form })
    else:
        try:
            profile = user.profile
            form = AccountForm(initial={
                'email': user.email,
                'display_name': profile.display_name,
                'discord_username': profile.discord_username,
                'bio': profile.bio,
            })
        except UserProfile.DoesNotExist:
            form = AccountForm(initial={ 'email': user.email })

        return render(request, 'account.html', { "form": form })

class UserMultipleChoiceField(forms.ModelMultipleChoiceField):
    def __init__(self, *args, **kwargs):
        if 'queryset' not in kwargs: kwargs['queryset'] = User.objects.all()
        if 'widget' not in kwargs: kwargs['widget'] = forms.CheckboxSelectMultiple()
        super(UserMultipleChoiceField, self).__init__(*args, **kwargs)

    def label_from_instance(self, user):
        return get_full_display_name(user)

class PuzzleInfoForm(forms.ModelForm):
    def __init__(self, user, *args, **kwargs):
        super(PuzzleInfoForm, self).__init__(*args, **kwargs)
        self.fields['authors'] = UserMultipleChoiceField(initial=user)

    class Meta:
        model = Puzzle
        fields = ['name', 'codename', 'authors', 'summary', 'description', 'notes']
        widgets = {
            'authors': forms.CheckboxSelectMultiple(),
        }

@login_required
def new(request):
    user = request.user

    if request.method == 'POST':
        form = PuzzleInfoForm(user, request.POST)
        if form.is_valid():
            new_puzzle = form.save(commit=False)
            new_puzzle.save()
            form.save_m2m()

            new_puzzle.spoiled.add(*new_puzzle.authors.all())

            add_comment(
                request=request,
                puzzle=new_puzzle,
                author=user,
                is_system=True,
                content="Created puzzle",
            )

            return redirect('/authored')
        else:
            return render(request, 'new.html', { "form": form })
    else:
        form = PuzzleInfoForm(request.user)
        return render(request, 'new.html', { "form": form })

# TODO: "authored" is now a misnomer
@login_required
def authored(request):
    puzzles = Puzzle.objects.filter(authors=request.user)
    editing_puzzles = Puzzle.objects.filter(discussion_editors=request.user)
    return render(request, 'authored.html', {
        'puzzles': puzzles,
        'editing_puzzles': editing_puzzles,
    })

@login_required
def all(request):
    puzzles = Puzzle.objects.all()
    return render(request, 'all.html', { 'puzzles': puzzles })

class PuzzleCommentForm(forms.Form):
    content = forms.CharField(widget=MarkdownTextarea)

class PuzzleContentForm(forms.ModelForm):
    class Meta:
        model = Puzzle
        fields = ['content']

class PuzzleSolutionForm(forms.ModelForm):
    class Meta:
        model = Puzzle
        fields = ['solution']

class PuzzlePriorityForm(forms.ModelForm):
    class Meta:
        model = Puzzle
        fields = ['priority']

def add_comment(request, puzzle, author, is_system, content, testsolve_session=None):
    comment = PuzzleComment(
        puzzle=puzzle,
        author=author,
        testsolve_session=testsolve_session,
        is_system=is_system,
        content=content,
    )
    comment.save()

    messaging.send_mail_wrapper(
        "New comment on {}".format(puzzle.spoiler_free_title()),
        "new_comment_email",
        {
            "request": request,
            "puzzle": puzzle,
            "author": author,
            "content": content,
            "is_system": is_system,
            "testsolve_session": testsolve_session,
        },
        puzzle.get_emails(exclude_emails=(author.email,)),
    )

@login_required
def puzzle(request, id):
    puzzle = Puzzle.objects.get(id=id)
    user = request.user

    def add_system_comment_here(message):
        add_comment(
            request=request,
            puzzle=puzzle,
            author=user,
            is_system=True,
            content=message
        )

    if request.method == 'POST':
        if "do_spoil" in request.POST:
            puzzle.spoiled.add(user)
        elif "change_status" in request.POST:
            puzzle.status = request.POST["change_status"]
            puzzle.save()
            add_system_comment_here("Status changed to " + puzzle.get_status_display())
        elif "change_priority" in request.POST:
            form = PuzzlePriorityForm(request.POST, instance=puzzle)
            if form.is_valid():
                form.save()
                add_system_comment_here("Priority changed to " + puzzle.get_priority_display())
        elif    "add_author" in request.POST: puzzle.authors.   add(user); add_system_comment_here(  "Added author " + str(user))
        elif "remove_author" in request.POST: puzzle.authors.remove(user); add_system_comment_here("Removed author " + str(user))
        elif    "add_discussion_editor" in request.POST: puzzle.discussion_editors.   add(user); add_system_comment_here(  "Added discussion editor " + str(user))
        elif "remove_discussion_editor" in request.POST: puzzle.discussion_editors.remove(user); add_system_comment_here("Removed discussion editor " + str(user))
        elif    "add_factchecker" in request.POST: puzzle.factcheckers.   add(user); add_system_comment_here(  "Added factchecker " + str(user))
        elif "remove_factchecker" in request.POST: puzzle.factcheckers.remove(user); add_system_comment_here("Removed factchecker " + str(user))
        elif    "add_postprodder" in request.POST: puzzle.postprodders.   add(user); add_system_comment_here(  "Added postprodder " + str(user))
        elif "remove_postprodder" in request.POST: puzzle.postprodders.remove(user); add_system_comment_here("Removed postprodder " + str(user))
        elif "edit_content" in request.POST:
            form = PuzzleContentForm(request.POST, instance=puzzle)
            if form.is_valid():
                form.save()
                add_system_comment_here("Edited puzzle content")
        elif "edit_solution" in request.POST:
            form = PuzzleSolutionForm(request.POST, instance=puzzle)
            if form.is_valid():
                form.save()
                add_system_comment_here("Edited puzzle solution")
        elif "add_comment" in request.POST:
            comment_form = PuzzleCommentForm(request.POST)
            if comment_form.is_valid():
                add_comment(
                    request=request,
                    puzzle=puzzle,
                    author=user,
                    is_system=False,
                    content=comment_form.cleaned_data["content"],
                )
        # refresh
        return redirect(urls.reverse('puzzle', args=[id]))

    if is_spoiled_on(user, puzzle):
        comments = PuzzleComment.objects.filter(puzzle=puzzle)
        return render(request, 'puzzle.html', {
            'puzzle': puzzle,
            'comments': comments,
            'comment_form': PuzzleCommentForm(),
            'all_statuses': status.ALL_STATUSES,
            'is_author': is_author_on(user, puzzle),
            'is_discussion_editor': is_discussion_editor_on(user, puzzle),
            'is_factchecker': is_factchecker_on(user, puzzle),
            'is_postprodder': is_postprodder_on(user, puzzle),
            'content_form': PuzzleContentForm(instance=puzzle),
            'solution_form': PuzzleSolutionForm(instance=puzzle),
            'priority_form': PuzzlePriorityForm(instance=puzzle),
        })
    else:
        return render(request, 'puzzle_unspoiled.html', { 'puzzle': puzzle })

class AnswerMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, answer):
        opc = answer.other_puzzle_count
        if opc:
            return "{} (assigned to {} other puzzle{})".format(
                answer, opc, "s" if opc != 1 else ""
            )
        else:
            return str(answer)

class PuzzleAnswersForm(forms.ModelForm):
    def __init__(self, user, *args, **kwargs):
        super(PuzzleAnswersForm, self).__init__(*args, **kwargs)

        puzzle = kwargs['instance']

        self.fields['answers'] = AnswerMultipleChoiceField(
            queryset=PuzzleAnswer.objects.filter(round__spoiled=user).annotate(
                other_puzzle_count=Count('puzzles', filter=~Q(puzzles__id=puzzle.id)),
            ),
            widget=forms.CheckboxSelectMultiple(),
        )

    class Meta:
        model = Puzzle
        fields = ['answers']
        widgets = {
            'answers': forms.CheckboxSelectMultiple(),
        }

@login_required
def puzzle_answers(request, id):
    puzzle = Puzzle.objects.get(id=id)
    user = request.user
    spoiled = is_spoiled_on(user, puzzle)

    if request.method == 'POST':
        form = PuzzleAnswersForm(user, request.POST, instance=puzzle)
        if form.is_valid():
            form.save()

            answers = form.cleaned_data['answers']
            if answers:
                if len(answers) == 1:
                    comment = "Assigned answer " + answers[0].answer
                else:
                    comment = "Assigned answers " + ", ".join(answer.answer for answer in answers)
            else:
                comment = "Unassigned answer"

            add_comment(
                request=request,
                puzzle=puzzle,
                author=user,
                is_system=True,
                content=comment
            )

            return redirect(urls.reverse('puzzle', args=[id]))

    unspoiled_rounds = Round.objects.exclude(spoiled=user).count()
    unspoiled_answers = PuzzleAnswer.objects.exclude(round__spoiled=user).count()

    return render(request, 'puzzle_answers.html', {
        'puzzle': puzzle,
        'form': PuzzleAnswersForm(user, instance=puzzle),
        'spoiled': spoiled,
        'unspoiled_rounds': unspoiled_rounds,
        'unspoiled_answers': unspoiled_answers,
    })

class PuzzlePeopleForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(PuzzlePeopleForm, self).__init__(*args, **kwargs)
        self.fields['authors'] = UserMultipleChoiceField()
        self.fields['discussion_editors'] = UserMultipleChoiceField()
        self.fields['factcheckers'] = UserMultipleChoiceField()
        self.fields['postprodders'] = UserMultipleChoiceField()
        self.fields['spoiled'] = UserMultipleChoiceField()
        #     queryset=User.objects.all(),
        #     initial=user,
        #     widget=forms.CheckboxSelectMultiple(),
        # )
    class Meta:
        model = Puzzle
        fields = ['authors', 'discussion_editors', 'factcheckers', 'postprodders', 'spoiled']

@login_required
def puzzle_edit(request, id):
    puzzle = Puzzle.objects.get(id=id)
    user = request.user

    if request.method == 'POST':
        form = PuzzleInfoForm(user, request.POST, instance=puzzle)
        if form.is_valid():
            form.save()

            if form.changed_data:
                add_comment(
                    request=request,
                    puzzle=puzzle,
                    author=user,
                    is_system=True,
                    content="Updated " + ", ".join(form.changed_data),
                )

            return redirect(urls.reverse('puzzle', args=[id]))
    else:
        form = PuzzleInfoForm(user, instance=puzzle)

    return render(request, 'puzzle_edit.html', {
        "puzzle": puzzle,
        "form": form,
        "spoiled": is_spoiled_on(user, puzzle)
    })

@login_required
def puzzle_people(request, id):
    puzzle = Puzzle.objects.get(id=id)
    user = request.user

    if request.method == 'POST':
        form = PuzzlePeopleForm(request.POST, instance=puzzle)
        if form.is_valid():
            form.save()

            if form.changed_data:
                # TODO: changed_data is not strictly user-friendly info
                add_comment(
                    request=request,
                    puzzle=puzzle,
                    author=user,
                    is_system=True,
                    content="Updated " + ", ".join(form.changed_data),
                )

            return redirect(urls.reverse('puzzle', args=[id]))
        else:
            context = {
                "puzzle": puzzle,
                "form": form,
            }
    else:
        context = {
            "puzzle": puzzle,
            "form": PuzzlePeopleForm(instance=puzzle),
        }

    return render(request, 'puzzle_people.html', context)


def warn_about_testsolving(is_spoiled, in_session, has_session):
    reasons = []
    if is_spoiled: reasons.append("you are spoiled")
    if in_session: reasons.append("you are already testsolving it")
    if has_session: reasons.append("there is an existing session you can join")

    if len(reasons) == 3:
        r1, r2, r3 = reasons
        return "{}, {}, and {}".format(*reasons)
    elif len(reasons) == 2:
        return "{} and {}".format(*reasons)
    elif len(reasons) == 1:
        return "{}".format(*reasons)
    else:
        return None

@login_required
def testsolve_main(request):
    user = request.user

    if request.method == 'POST':
        if "start_session" in request.POST:
            puzzle_id = request.POST["start_session"]
            puzzle = Puzzle.objects.get(id=puzzle_id)
            session = TestsolveSession(puzzle=puzzle)
            session.save()

            participation = TestsolveParticipation(session=session, user=user)
            participation.save()

            add_comment(
                request=request,
                puzzle=puzzle,
                author=user,
                is_system=True,
                content="Created testsolve session #{}".format(session.id),
                testsolve_session=session,
            )

            return redirect(urls.reverse('testsolve_one', args=[session.id]))

    sessions = get_sessions_with_joined_and_current(request.user)
    current_sessions = sessions.filter(joined=True, current=True)
    past_sessions = sessions.filter(joined=True, current=False)
    joinable_sessions = sessions.filter(joined=False, joinable=True)

    testsolvable_puzzles = Puzzle.objects.filter(status=status.TESTSOLVING).annotate(
        is_author=Exists(
            User.objects.filter(authored_puzzles=OuterRef('pk'), id=user.id)
        ),
        is_spoiled=Exists(
            User.objects.filter(spoiled_puzzles=OuterRef('pk'), id=user.id)
        ),
        in_session=Exists(
            current_sessions.filter(puzzle=OuterRef('pk'))
        ),
        has_session=Exists(
            joinable_sessions.filter(puzzle=OuterRef('pk'))
        ),
    )

    testsolvable = [{
        'puzzle': puzzle,
        'warning': warn_about_testsolving(puzzle.is_spoiled, puzzle.in_session, puzzle.has_session),
    } for puzzle in testsolvable_puzzles]

    context = {
        'current_sessions': current_sessions,
        'past_sessions': past_sessions,
        'joinable_sessions': joinable_sessions,
        'testsolvable': testsolvable,
    }

    return render(request, 'testsolve_main.html', context)

def normalize_answer(answer):
    return ''.join(c for c in answer if c.isalnum()).upper()

class GuessForm(forms.Form):
    guess = forms.CharField()

@login_required
def testsolve_one(request, id):
    session = TestsolveSession.objects.get(id=id)
    puzzle = session.puzzle
    user = request.user

    if request.method == 'POST':
        if "join" in request.POST:
            if not TestsolveParticipation.objects.filter(session=session, user=user).exists():
                participation = TestsolveParticipation()
                participation.session = session
                participation.user = user
                participation.save()

        elif "do_guess" in request.POST:
            participation = TestsolveParticipation.objects.get(
                session=session,
                user=user,
            )
            guess_form = GuessForm(request.POST)
            if guess_form.is_valid():
                guess = guess_form.cleaned_data["guess"]
                normalized_guess = normalize_answer(guess)
                correct = any(normalized_guess == normalize_answer(answer.answer) for answer in session.puzzle.answers.all())

                guess_model = TestsolveGuess(
                    session=session,
                    user=user,
                    guess=guess,
                    correct=correct,
                )
                guess_model.save()

                if correct and session.joinable:
                    add_comment(
                        request=request,
                        puzzle=puzzle,
                        author=user,
                        testsolve_session=session,
                        is_system=True,
                        content="Automatically marking session as no longer joinable due to correct answer",
                    )

                    session.joinable = False
                    session.save()

        elif "change_joinable" in request.POST:
            session.joinable = request.POST["change_joinable"] == "1"
            session.save()

        elif "add_comment" in request.POST:
            comment_form = PuzzleCommentForm(request.POST)
            if comment_form.is_valid():
                add_comment(
                    request=request,
                    puzzle=puzzle,
                    author=user,
                    testsolve_session=session,
                    is_system=False,
                    content=comment_form.cleaned_data["content"],
                )

        # refresh
        return redirect(urls.reverse('testsolve_one', args=[id]))

    try:
        participation = TestsolveParticipation.objects.get(session=session, user=user)
    except TestsolveParticipation.DoesNotExist:
        participation = None

    spoiled = is_spoiled_on(user, puzzle)
    answers_exist = session.puzzle.answers.exists()
    context = {
        'session': session,
        'participation': participation,
        'spoiled': spoiled,
        'answers_exist': answers_exist,
        'guesses': TestsolveGuess.objects.filter(session=session),
        'guess_form': GuessForm(),
        'comment_form': PuzzleCommentForm(),
    }

    return render(request, 'testsolve_one.html', context)

class PuzzleFinishForm(forms.Form):
    def __init__(self, fun, difficulty, *args, **kwargs):
        super(PuzzleFinishForm, self).__init__(*args, **kwargs)
        self.fields['fun'] = forms.ChoiceField(
            choices=[
                (None, 'n/a'),
                (1, '1: not fun'),
                (2, '2: a little fun'),
                (3, '3: somewhat fun'),
                (4, '4: fun'),
                (5, '5: very fun'),
                (6, '6: extremely fun'),
            ],
            widget=forms.Select(),
            initial=fun,
            required=False,
        )
        self.fields['difficulty'] = forms.ChoiceField(
            choices=[
                (None, 'n/a'),
                (1, '1: very easy'),
                (2, '2: easy'),
                (3, '3: somewhat difficult'),
                (4, '4: difficult'),
                (5, '5: very difficult'),
                (6, '6: extremely difficult'),
            ],
            widget=forms.Select(),
            initial=difficulty,
            required=False,
        )

    comment = forms.CharField(widget=forms.Textarea, required=False)


@login_required
def testsolve_finish(request, id):
    session = TestsolveSession.objects.get(id=id)
    puzzle = session.puzzle
    user = request.user

    try:
        participation = TestsolveParticipation.objects.get(session=session, user=user)
    except TestsolveParticipation.DoesNotExist:
        participation = None

    if request.method == 'POST' and participation:
        form = PuzzleFinishForm(participation.fun_rating, participation.difficulty_rating, request.POST)
        if form.is_valid():
            print("valid")
            fun = form.cleaned_data['fun'] or None
            difficulty = form.cleaned_data['difficulty'] or None
            comment = form.cleaned_data["comment"]
            ratings_text = "Fun: {} / Difficulty: {}".format(fun or "n/a", difficulty or "n/a")
            if comment:
                comment_content = "Finished testsolve with comment:\n\n{}\n\n{}".format(comment, ratings_text)
            else:
                comment_content = "Finished testsolve\n\n{}".format(ratings_text)
            add_comment(
                request=request,
                puzzle=puzzle,
                author=user,
                testsolve_session=session,
                is_system=False,
                content=comment_content,
            )
            participation.fun_rating = fun
            participation.difficulty_rating = difficulty
            participation.ended = datetime.datetime.now()
            participation.save()
            return redirect(urls.reverse('testsolve_one', args=[id]))
        else:
            print("not valid")
            print(form.errors)
            context = {
                'session': session,
                'participation': participation,
                'form': form,
            }

            return render(request, 'testsolve_finish.html', context)

    form = PuzzleFinishForm(participation.fun_rating, participation.difficulty_rating)
    print(participation.fun_rating)
    print(type(participation.fun_rating))
    print(participation.difficulty_rating)
    print(type(participation.difficulty_rating))
    context = {
        'session': session,
        'participation': participation,
        'form': form,
    }

    return render(request, 'testsolve_finish.html', context)

@login_required
def postprod(request):
    postprodding = Puzzle.objects.filter(
        status=status.NEEDS_POSTPROD,
        postprodders=request.user,
    )
    needs_postprod = Puzzle.objects.annotate(
        has_postprodder=Exists(User.objects.filter(postprodding_puzzles=OuterRef('pk')))
    ).filter(status=status.NEEDS_POSTPROD, has_postprodder=False)

    context = {
        'postprodding': postprodding,
        'needs_postprod': needs_postprod,
    }
    return render(request, 'postprod.html', context)

@login_required
def factcheck(request):
    factchecking = Puzzle.objects.filter(
        status=status.NEEDS_FACTCHECK,
        factcheckers=request.user
    )
    needs_factcheck = Puzzle.objects.annotate(
        has_factchecker=Exists(User.objects.filter(factchecking_puzzles=OuterRef('pk')))
    ).filter(status=status.NEEDS_FACTCHECK, has_factchecker=False)

    context = {
        'factchecking': factchecking,
        'needs_factchecking': needs_factcheck,
    }
    return render(request, 'factcheck.html', context)

@login_required
def needs_editor(request):
    needs_editors = Puzzle.objects.annotate(
        remaining_des=(F('needed_discussion_editors') - Count('discussion_editors'))
    ).filter(remaining_des__gt=0)

    context = {
        'needs_editors': needs_editors
    }
    return render(request, 'needs_editor.html', context)

class AnswerForm(forms.ModelForm):
    def __init__(self, round, *args, **kwargs):
        super(AnswerForm, self).__init__(*args, **kwargs)
        self.fields['round'] = forms.ModelChoiceField(
            queryset=Round.objects.all(), # ???
            initial=round,
            widget=forms.HiddenInput(),
        )

    class Meta:
        model = PuzzleAnswer
        fields = ['answer', 'round']

class RoundForm(forms.ModelForm):
    class Meta:
        model = Round
        fields = ['name', 'description']

@login_required
@permission_required('puzzle_editing.change_round')
def rounds(request):
    user = request.user

    new_round_form = RoundForm()
    if request.method == 'POST':
        if 'spoil_on' in request.POST:
            Round.objects.get(id=request.POST['spoil_on']).spoiled.add(user)

        elif 'new_round' in request.POST:
            new_round_form = RoundForm(request.POST)
            if new_round_form.is_valid():
                new_round_form.save()

        elif 'add_answer' in request.POST:
            answer_form = AnswerForm(None, request.POST)
            if answer_form.is_valid():
                answer_form.save()

        elif 'delete_answer' in request.POST:
            PuzzleAnswer.objects.get(id=request.POST['delete_answer']).delete()

        return redirect(urls.reverse('rounds'))

    rounds = [{
        'id': round.id,
        'name': round.name,
        'description': round.description,
        'spoiled': round.spoiled.filter(id=user.id).exists(),
        'answers': [{
            'answer': answer.answer,
            'id': answer.id,
            'puzzles': answer.puzzles.all(),
        } for answer in round.answers.all()],
        'form': AnswerForm(round),
    } for round in Round.objects.all()]

    return render(request, 'rounds.html', {
        'rounds': rounds,
        'new_round_form': RoundForm(),
    })

@login_required
def users(request):
    # distinct=True because https://stackoverflow.com/questions/59071464/django-how-to-annotate-manytomany-field-with-count
    annotation_kwargs = dict()
    for key in ['authored', 'discussing', 'factchecking']:
        annotation_kwargs[key + "_active"]   = Count(key + '_puzzles', filter=~Q(**{ key + '_puzzles__status__in': [status.DEAD, status.DEFERRED, status.DONE] }), distinct=True)

        annotation_kwargs[key + "_dead"]     = Count(key + '_puzzles', filter=Q(**{ key + '_puzzles__status': status.DEAD     }), distinct=True)
        annotation_kwargs[key + "_deferred"] = Count(key + '_puzzles', filter=Q(**{ key + '_puzzles__status': status.DEFERRED }), distinct=True)
        annotation_kwargs[key + "_done"]     = Count(key + '_puzzles', filter=Q(**{ key + '_puzzles__status': status.DONE     }), distinct=True)

    users = User.objects.all().select_related('profile').annotate(**annotation_kwargs)

    users = list(users)
    for user in users:
        user.full_display_name = get_full_display_name(user)
        user.is_meta_editor = user.has_perm('puzzle_editing.change_round')

    return render(request, 'users.html', {
        'users': users,
    })

@csrf_exempt
def preview_markdown(request):
    if request.method == 'POST':
        output = render_to_string('preview_markdown.html', { "input": request.body.decode('utf-8') })
        return JsonResponse({
            'success': True,
            'output': output,
        })
    return JsonResponse({
        'success': False,
        'error': 'No markdown input received',
    })
