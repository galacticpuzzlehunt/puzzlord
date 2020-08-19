import datetime
import os
import random
import re

import django.forms as forms
import django.urls as urls
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.db.models import Exists
from django.db.models import F
from django.db.models import Max
from django.db.models import OuterRef
from django.db.models import Q
from django.db.models import Subquery
from django.db.models.functions import Lower
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.views.static import serve

import puzzle_editing.messaging as messaging
import puzzle_editing.status as status
import puzzle_editing.utils as utils
import puzzlord.settings as settings
from puzzle_editing.graph import curr_puzzle_graph_b64
from puzzle_editing.models import get_user_role
from puzzle_editing.models import is_author_on
from puzzle_editing.models import is_discussion_editor_on
from puzzle_editing.models import is_factchecker_on
from puzzle_editing.models import is_postprodder_on
from puzzle_editing.models import is_spoiled_on
from puzzle_editing.models import Puzzle
from puzzle_editing.models import PuzzleAnswer
from puzzle_editing.models import PuzzleComment
from puzzle_editing.models import PuzzlePostprod
from puzzle_editing.models import PuzzleTag
from puzzle_editing.models import PuzzleVisited
from puzzle_editing.models import Round
from puzzle_editing.models import StatusSubscription
from puzzle_editing.models import TestsolveGuess
from puzzle_editing.models import TestsolveParticipation
from puzzle_editing.models import TestsolveSession
from puzzle_editing.models import UserProfile


def get_sessions_with_joined_and_current(user):
    return TestsolveSession.objects.annotate(
        joined=Exists(
            TestsolveParticipation.objects.filter(session=OuterRef("pk"), user=user,)
        ),
        current=Exists(
            TestsolveParticipation.objects.filter(
                session=OuterRef("pk"), user=user, ended=None,
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


def get_credits_name(user):
    try:
        return user.profile.credits_name or user.profile.display_name or user.username
    except UserProfile.DoesNotExist:
        return user.username


def index(request):
    user = request.user

    if not request.user.is_authenticated:
        return render(request, "index_not_logged_in.html")

    blocked_on_author_puzzles = Puzzle.objects.filter(
        authors=user, status__in=status.STATUSES_BLOCKED_ON_AUTHORS,
    )
    blocked_on_editor_puzzles = Puzzle.objects.filter(
        discussion_editors=user, status__in=status.STATUSES_BLOCKED_ON_EDITORS,
    )
    current_sessions = get_sessions_with_joined_and_current(user).filter(
        joined=True, current=True
    )
    factchecking = Puzzle.objects.filter(
        status=status.NEEDS_FACTCHECK, factcheckers=user
    )
    postprodding = Puzzle.objects.filter(
        status=status.NEEDS_POSTPROD, postprodders=user
    )
    inbox_puzzles = (
        user.spoiled_puzzles.exclude(status=status.DEAD)
        .annotate(
            last_comment_date=Max("comments__date"),
            last_visited_date=Subquery(
                PuzzleVisited.objects.filter(puzzle=OuterRef("pk"), user=user).values(
                    "date"
                )
            ),
        )
        .filter(
            Q(last_visited_date__isnull=True)
            | Q(last_comment_date__gt=F("last_visited_date"))
        )
    )

    return render(
        request,
        "index.html",
        {
            "blocked_on_author_puzzles": blocked_on_author_puzzles,
            "blocked_on_editor_puzzles": blocked_on_editor_puzzles,
            "current_sessions": current_sessions,
            "factchecking": factchecking,
            "inbox_puzzles": inbox_puzzles,
            "postprodding": postprodding,
        },
    )


class MarkdownTextarea(forms.Textarea):
    template_name = "widgets/markdown_textarea.html"


# based on UserCreationForm from Django source
class RegisterForm(forms.ModelForm):
    """
    A form that creates a user, with no privileges, from the given username and
    password.
    """

    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(
        label="Password confirmation",
        widget=forms.PasswordInput,
        help_text="Enter the same password as above, for verification.",
    )
    email = forms.EmailField(
        label="Email address",
        required=False,
        help_text="Optional, but you'll get useful email notifications.",
    )

    site_password = forms.CharField(
        label="Site password",
        widget=forms.PasswordInput,
        help_text="Get this password from the Discord.",
    )

    display_name = forms.CharField(
        label="Display name", required=False, help_text="(optional)"
    )
    discord_username = forms.CharField(
        label="Discord username",
        help_text="(required) Discord username and tag (e.g. example#1234)",
    )
    credits_name = forms.CharField(
        label="Credits name",
        help_text="(required) Name you want displayed in the credits for hunt and author field on your puzzles, likely your full name",
    )
    bio = forms.CharField(
        widget=MarkdownTextarea,
        required=False,
        help_text="(optional) Tell us about yourself. What kinds of puzzle genres or subject matter do you like?",
    )

    class Meta:
        model = User
        fields = ("username", "email")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                "The two password fields didn't match.", code="password_mismatch",
            )
        return password2

    def clean_site_password(self):
        site_password = self.cleaned_data.get("site_password")
        if site_password and site_password != settings.SITE_PASSWORD:
            raise forms.ValidationError(
                "The site password was incorrect.", code="password_mismatch",
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
                credits_name=self.cleaned_data["credits_name"],
            )
            profile.save()
        return user


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(urls.reverse("index"))
        else:
            return render(request, "register.html", {"form": form})
    else:
        form = RegisterForm()
        return render(request, "register.html", {"form": form})


class AccountForm(forms.Form):
    email = forms.EmailField(
        label="Email address",
        required=False,
        help_text="Optional, but you'll get useful email notifications.",
    )

    display_name = forms.CharField(label="Display name", required=False)
    discord_username = forms.CharField(
        label="Discord username",
        help_text="(required) Discord username and tag (e.g. example#1234)",
    )
    credits_name = forms.CharField(
        label="Credits name",
        help_text="(required) Name you want displayed in the credits for hunt and author field on your puzzles, likely your full name",
    )
    bio = forms.CharField(
        widget=MarkdownTextarea,
        required=False,
        help_text="(optional) Tell us about yourself. What kinds of puzzle genres or subject matter do you like?",
    )
    keyboard_shortcuts = forms.BooleanField(
        label="Enable keyboard shortcuts",
        required=False,
        help_text="On puzzle pages only. Press ? for help.",
    )


@login_required
def account(request):
    user = request.user

    if request.method == "POST":
        form = AccountForm(request.POST)
        if form.is_valid():
            user.email = form.cleaned_data["email"]
            user.save()

            try:
                profile = user.profile
                profile.display_name = form.cleaned_data["display_name"]
                profile.discord_username = form.cleaned_data["discord_username"]
                profile.bio = form.cleaned_data["bio"]
                profile.credits_name = form.cleaned_data["credits_name"]
                profile.enable_keyboard_shortcuts = form.cleaned_data[
                    "keyboard_shortcuts"
                ]
                profile.save()
            except UserProfile.DoesNotExist:
                profile = UserProfile(
                    user=user,
                    display_name=form.cleaned_data["display_name"],
                    discord_username=form.cleaned_data["discord_username"],
                    bio=form.cleaned_data["bio"],
                    enable_keyboard_shortcuts=form.cleaned_data["keyboard_shortcuts"],
                )
                profile.save()

            return render(request, "account.html", {"form": form, "success": True})
        else:
            return render(request, "account.html", {"form": form})
    else:
        try:
            profile = user.profile
            form = AccountForm(
                initial={
                    "email": user.email,
                    "display_name": profile.display_name,
                    "discord_username": profile.discord_username,
                    "credits_name": profile.credits_name
                    or profile.display_name
                    or user.username,
                    "bio": profile.bio,
                    "keyboard_shortcuts": profile.enable_keyboard_shortcuts,
                }
            )
        except UserProfile.DoesNotExist:
            form = AccountForm(initial={"email": user.email})

        return render(request, "account.html", {"form": form})


class UserCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    template_name = "widgets/user_checkbox_select_multiple.html"


class UserMultipleChoiceField(forms.ModelMultipleChoiceField):
    def __init__(self, *args, **kwargs):
        orderings = []
        if kwargs.get("editors_first", False):
            orderings.append("-user_permissions")
            del kwargs["editors_first"]
        orderings.append(Lower("username"))
        if "queryset" not in kwargs:
            kwargs["queryset"] = User.objects.all().order_by(*orderings)
        if "widget" not in kwargs:
            kwargs["widget"] = UserCheckboxSelectMultiple()
        super(UserMultipleChoiceField, self).__init__(*args, **kwargs)

    def label_from_instance(self, user):
        return get_full_display_name(user)


class PuzzleInfoForm(forms.ModelForm):
    def __init__(self, user, *args, **kwargs):
        super(PuzzleInfoForm, self).__init__(*args, **kwargs)
        self.fields["authors"] = UserMultipleChoiceField(initial=user)

    class Meta:
        model = Puzzle
        fields = ["name", "codename", "authors", "summary", "description", "notes"]
        widgets = {
            "authors": forms.CheckboxSelectMultiple(),
        }


@login_required
def new(request):
    user = request.user

    if request.method == "POST":
        form = PuzzleInfoForm(user, request.POST)
        if form.is_valid():
            new_puzzle = form.save(commit=False)
            new_puzzle.status_mtime = datetime.datetime.now()
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

            return redirect(urls.reverse("authored"))
        else:
            return render(request, "new.html", {"form": form})
    else:
        form = PuzzleInfoForm(request.user)
        return render(request, "new.html", {"form": form})


@login_required
def random_answers(request):
    answers = list(PuzzleAnswer.objects.filter(puzzles__isnull=True))
    available = random.sample(answers, min(3, len(answers)))
    return render(request, "random_answers.html", {"answers": available})


# TODO: "authored" is now a misnomer
@login_required
def authored(request):
    puzzles = Puzzle.objects.filter(authors=request.user)
    editing_puzzles = Puzzle.objects.filter(discussion_editors=request.user)
    return render(
        request,
        "authored.html",
        {"puzzles": puzzles, "editing_puzzles": editing_puzzles,},
    )


@login_required
def all(request):
    puzzles = Puzzle.objects.all()
    return render(request, "all.html", {"puzzles": puzzles})


class PuzzleCommentForm(forms.Form):
    content = forms.CharField(widget=MarkdownTextarea)


class PuzzleContentForm(forms.ModelForm):
    class Meta:
        model = Puzzle
        fields = ["content"]


class PuzzleSolutionForm(forms.ModelForm):
    class Meta:
        model = Puzzle
        fields = ["solution"]


class PuzzlePriorityForm(forms.ModelForm):
    class Meta:
        model = Puzzle
        fields = ["priority"]


class PuzzlePostprodForm(forms.ModelForm):
    class Meta:
        model = PuzzlePostprod
        exclude = []
        widgets = {
            "puzzle": forms.HiddenInput(),
            "zip_file": forms.FileInput(attrs={"accept": ".zip"}),
            "authors": forms.Textarea(attrs={"rows": 3, "cols": 40}),
        }

    def __init__(self, *args, **kwargs):
        super(PuzzlePostprodForm, self).__init__(*args, **kwargs)
        self.fields["zip_file"].required = False

    def clean_zip_file(self):
        zip_file = self.cleaned_data["zip_file"]
        puzzle = self.cleaned_data["puzzle"]
        if not zip_file and not puzzle.has_postprod():
            raise ValidationError("This field is required the first time you postprod.")
        return zip_file


def add_comment(request, puzzle, author, is_system, content, testsolve_session=None):
    comment = PuzzleComment(
        puzzle=puzzle,
        author=author,
        testsolve_session=testsolve_session,
        is_system=is_system,
        content=content,
    )
    comment.save()

    if testsolve_session:
        subject = "New comment on {} (testsolve #{})".format(
            puzzle.spoiler_free_title(), testsolve_session.id
        )
        emails = testsolve_session.get_emails(exclude_emails=(author.email,))
    else:
        subject = "New comment on {}".format(puzzle.spoiler_free_title())
        emails = puzzle.get_emails(exclude_emails=(author.email,))

    messaging.send_mail_wrapper(
        subject,
        "new_comment_email",
        {
            "request": request,
            "puzzle": puzzle,
            "author": author,
            "content": content,
            "is_system": is_system,
            "testsolve_session": testsolve_session,
        },
        emails,
    )


@login_required  # noqa: C901
def puzzle(request, id):
    puzzle = get_object_or_404(Puzzle, id=id)
    user = request.user

    vis, vis_created = PuzzleVisited.objects.get_or_create(puzzle=puzzle, user=user)
    if not vis_created:
        # update the auto_now=True DateTimeField anyway
        vis.save()

    def add_system_comment_here(message):
        add_comment(
            request=request, puzzle=puzzle, author=user, is_system=True, content=message
        )

    if request.method == "POST":
        if "do_spoil" in request.POST:
            puzzle.spoiled.add(user)
        elif "change_status" in request.POST:
            new_status = request.POST["change_status"]
            puzzle.status = new_status
            puzzle.save()

            status_display = status.get_display(new_status)
            add_system_comment_here("Status changed to " + status_display)

            for session in puzzle.testsolve_sessions.filter(joinable=True):
                session.joinable = False
                add_comment(
                    request=request,
                    puzzle=puzzle,
                    author=user,
                    testsolve_session=session,
                    is_system=True,
                    content="Puzzle status changed, automaticaly marking session as no longer joinable",
                )
                session.save()

            subscriptions = (
                StatusSubscription.objects.filter(status=new_status)
                .exclude(user__email="")
                .values_list("user__email", flat=True)
            )
            if subscriptions:
                messaging.send_mail_wrapper(
                    "{} entered status {}".format(
                        puzzle.spoiler_free_title(), status_display
                    ),
                    "status_update_email",
                    {
                        "request": request,
                        "puzzle": puzzle,
                        "user": user,
                        "status": status_display,
                    },
                    subscriptions,
                )

        elif "change_priority" in request.POST:
            form = PuzzlePriorityForm(request.POST, instance=puzzle)
            if form.is_valid():
                form.save()
                add_system_comment_here(
                    "Priority changed to " + puzzle.get_priority_display()
                )
        elif "add_author" in request.POST:
            puzzle.authors.add(user)
            add_system_comment_here("Added author " + str(user))
        elif "remove_author" in request.POST:
            puzzle.authors.remove(user)
            add_system_comment_here("Removed author " + str(user))
        elif "add_discussion_editor" in request.POST:
            puzzle.discussion_editors.add(user)
            add_system_comment_here("Added discussion editor " + str(user))
        elif "remove_discussion_editor" in request.POST:
            puzzle.discussion_editors.remove(user)
            add_system_comment_here("Removed discussion editor " + str(user))
        elif "add_factchecker" in request.POST:
            puzzle.factcheckers.add(user)
            add_system_comment_here("Added factchecker " + str(user))
        elif "remove_factchecker" in request.POST:
            puzzle.factcheckers.remove(user)
            add_system_comment_here("Removed factchecker " + str(user))
        elif "add_postprodder" in request.POST:
            puzzle.postprodders.add(user)
            add_system_comment_here("Added postprodder " + str(user))
        elif "remove_postprodder" in request.POST:
            puzzle.postprodders.remove(user)
            add_system_comment_here("Removed postprodder " + str(user))
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
        return redirect(urls.reverse("puzzle", args=[id]))

    if is_spoiled_on(user, puzzle):
        comments = PuzzleComment.objects.filter(puzzle=puzzle)
        unread_puzzles = user.spoiled_puzzles.annotate(
            last_comment_date=Max("comments__date"),
            last_visited_date=Subquery(
                PuzzleVisited.objects.filter(puzzle=OuterRef("pk"), user=user).values(
                    "date"
                )
            ),
        ).filter(
            Q(last_visited_date__isnull=True)
            | Q(last_comment_date__gt=F("last_visited_date"))
        )

        # FIXME
        try:
            enable_keyboard_shortcuts = user.profile.enable_keyboard_shortcuts
        except UserProfile.DoesNotExist:
            enable_keyboard_shortcuts = False

        return render(
            request,
            "puzzle.html",
            {
                "puzzle": puzzle,
                "comments": comments,
                "comment_form": PuzzleCommentForm(),
                "testsolve_sessions": TestsolveSession.objects.filter(puzzle=puzzle),
                "all_statuses": status.ALL_STATUSES,
                "is_author": is_author_on(user, puzzle),
                "is_discussion_editor": is_discussion_editor_on(user, puzzle),
                "is_factchecker": is_factchecker_on(user, puzzle),
                "is_postprodder": is_postprodder_on(user, puzzle),
                "content_form": PuzzleContentForm(instance=puzzle),
                "solution_form": PuzzleSolutionForm(instance=puzzle),
                "priority_form": PuzzlePriorityForm(instance=puzzle),
                "enable_keyboard_shortcuts": enable_keyboard_shortcuts,
                "next_unread_puzzle_id": unread_puzzles[0].id
                if unread_puzzles.count()
                else None,
            },
        )
    else:
        return render(
            request,
            "puzzle_unspoiled.html",
            {"puzzle": puzzle, "role": get_user_role(user, puzzle)},
        )


# https://stackoverflow.com/a/55129913/3243497
class AnswerCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    template_name = "widgets/answer_checkbox_select_multiple.html"

    def create_option(self, name, value, *args, **kwargs):
        option = super().create_option(name, value, *args, **kwargs)
        if value:
            option["instance"] = self.choices.queryset.get(pk=value)  # get instance
        return option

    # smuggle extra stuff through to the template
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["options"] = list(self.options(name, context["widget"]["value"], attrs))
        return context


class AnswerMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, answer):
        # don't display the round, which would be in the default str; our
        # custom widget is taking care of that
        return answer.answer


class PuzzleAnswersForm(forms.ModelForm):
    def __init__(self, user, *args, **kwargs):
        super(PuzzleAnswersForm, self).__init__(*args, **kwargs)

        puzzle = kwargs["instance"]

        self.fields["answers"] = AnswerMultipleChoiceField(
            queryset=PuzzleAnswer.objects.filter(round__spoiled=user)
            .order_by("round__id")
            .annotate(
                other_puzzle_count=Count("puzzles", filter=~Q(puzzles__id=puzzle.id)),
            ),
            widget=AnswerCheckboxSelectMultiple(),
            required=False,
        )

    class Meta:
        model = Puzzle
        fields = ["answers"]
        widgets = {
            "answers": forms.CheckboxSelectMultiple(),
        }


@login_required
def puzzle_answers(request, id):
    puzzle = get_object_or_404(Puzzle, id=id)
    user = request.user
    spoiled = is_spoiled_on(user, puzzle)

    if request.method == "POST":
        form = PuzzleAnswersForm(user, request.POST, instance=puzzle)
        if form.is_valid():
            form.save()

            answers = form.cleaned_data["answers"]
            if answers:
                if len(answers) == 1:
                    comment = "Assigned answer " + answers[0].answer
                else:
                    comment = "Assigned answers " + ", ".join(
                        answer.answer for answer in answers
                    )
            else:
                comment = "Unassigned answer"

            add_comment(
                request=request,
                puzzle=puzzle,
                author=user,
                is_system=True,
                content=comment,
            )

            return redirect(urls.reverse("puzzle", args=[id]))

    unspoiled_rounds = Round.objects.exclude(spoiled=user).count()
    unspoiled_answers = PuzzleAnswer.objects.exclude(round__spoiled=user).count()

    return render(
        request,
        "puzzle_answers.html",
        {
            "puzzle": puzzle,
            "form": PuzzleAnswersForm(user, instance=puzzle),
            "spoiled": spoiled,
            "unspoiled_rounds": unspoiled_rounds,
            "unspoiled_answers": unspoiled_answers,
        },
    )


class TagMultipleChoiceField(forms.ModelMultipleChoiceField):
    def __init__(self, *args, **kwargs):
        if "queryset" not in kwargs:
            kwargs["queryset"] = PuzzleTag.objects.all()
        if "widget" not in kwargs:
            kwargs["widget"] = forms.CheckboxSelectMultiple()
        super(TagMultipleChoiceField, self).__init__(*args, **kwargs)

    def label_from_instance(self, tag):
        tpc = tag.puzzles.count()
        return "{} ({} puzzle{})".format(tag.name, tpc, "s" if tpc != 1 else "")


class PuzzleTaggingForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(PuzzleTaggingForm, self).__init__(*args, **kwargs)

        self.fields["tags"] = TagMultipleChoiceField(required=False)

    class Meta:
        model = Puzzle
        fields = ["tags"]
        widgets = {
            "tags": forms.CheckboxSelectMultiple(),
        }


@login_required
def puzzle_tags(request, id):
    puzzle = get_object_or_404(Puzzle, id=id)
    user = request.user
    spoiled = is_spoiled_on(user, puzzle)

    if request.method == "POST":
        form = PuzzleTaggingForm(request.POST, instance=puzzle)
        if form.is_valid():
            form.save()

            tags = form.cleaned_data["tags"]
            comment = "Changed tags: " + (
                ", ".join(tag.name for tag in tags) or "(none)"
            )

            add_comment(
                request=request,
                puzzle=puzzle,
                author=user,
                is_system=True,
                content=comment,
            )

            return redirect(urls.reverse("puzzle", args=[id]))

    return render(
        request,
        "puzzle_tags.html",
        {
            "puzzle": puzzle,
            "form": PuzzleTaggingForm(instance=puzzle),
            "spoiled": spoiled,
        },
    )


@login_required
def puzzle_postprod(request, id):
    puzzle = get_object_or_404(Puzzle, id=id)
    user = request.user
    spoiled = is_spoiled_on(user, puzzle)

    if request.method == "POST":
        instance = puzzle.postprod if puzzle.has_postprod() else None
        form = PuzzlePostprodForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            pp = form.save()

            add_comment(
                request=request,
                puzzle=puzzle,
                author=user,
                is_system=True,
                content="Postprod updated.",
            )

            utils.deploy_puzzle(pp)

            return redirect(urls.reverse("puzzle", args=[id]))
    else:
        if puzzle.has_postprod():
            form = PuzzlePostprodForm(instance=puzzle.postprod)
        else:
            default_slug = re.sub(
                r'[<>#%\'"|{}\[\])(\\\^?=`;@&,]',
                "",
                re.sub(r"[ \/]+", "-", puzzle.name),
            ).lower()
            authors = [get_credits_name(user) for user in puzzle.authors.all()]
            authors.sort(key=lambda a: a.upper())
            form = PuzzlePostprodForm(
                initial={
                    "puzzle": puzzle,
                    "slug": default_slug,
                    "authors": ", ".join(authors),
                }
            )

    return render(
        request,
        "puzzle_postprod.html",
        {"puzzle": puzzle, "form": form, "spoiled": spoiled,},
    )


@login_required
def postprod_zip(request, id):
    pp = get_object_or_404(PuzzlePostprod, puzzle__id=id)
    loc = utils.get_latest_zip(pp)
    return serve(request, os.path.basename(loc), os.path.dirname(loc))


class PuzzlePeopleForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(PuzzlePeopleForm, self).__init__(*args, **kwargs)
        self.fields["authors"] = UserMultipleChoiceField(required=False)
        self.fields["discussion_editors"] = UserMultipleChoiceField(
            required=False, editors_first=True
        )
        self.fields["factcheckers"] = UserMultipleChoiceField(required=False)
        self.fields["postprodders"] = UserMultipleChoiceField(required=False)
        self.fields["spoiled"] = UserMultipleChoiceField(required=False)
        #     queryset=User.objects.all(),
        #     initial=user,
        #     widget=forms.CheckboxSelectMultiple(),
        # )

    class Meta:
        model = Puzzle
        fields = [
            "authors",
            "discussion_editors",
            "factcheckers",
            "postprodders",
            "spoiled",
        ]


@login_required
def puzzle_edit(request, id):
    puzzle = get_object_or_404(Puzzle, id=id)
    user = request.user

    if request.method == "POST":
        form = PuzzleInfoForm(user, request.POST, instance=puzzle)
        if form.is_valid():
            form.save()

            if form.changed_data:
                add_comment(
                    request=request,
                    puzzle=puzzle,
                    author=user,
                    is_system=True,
                    content=get_changed_data_message(form),
                )

            return redirect(urls.reverse("puzzle", args=[id]))
    else:
        form = PuzzleInfoForm(user, instance=puzzle)

    return render(
        request,
        "puzzle_edit.html",
        {"puzzle": puzzle, "form": form, "spoiled": is_spoiled_on(user, puzzle)},
    )


def get_changed_data_message(form):
    """Given a filled-out valid form, describe what changed.

    Somewhat automagically produce a system comment message that includes all
    the updated fields and particularly lists all new users for
    `UserMultipleChoiceField`s with an "Assigned" sentence."""

    normal_fields = []
    lines = []

    for field in form.changed_data:
        print(form.fields[field])
        if isinstance(form.fields[field], UserMultipleChoiceField):
            users = form.cleaned_data[field]
            field_name = field.replace("_", " ")
            if users:
                user_display = ", ".join(str(u) for u in users)
                # XXX haxx
                if len(users) == 1 and field_name.endswith("s"):
                    field_name = field_name[:-1]
                lines.append("Assigned {} as {}".format(user_display, field_name))
            else:
                lines.append("Unassigned all {}".format(field.replace("_", " ")))

        else:
            normal_fields.append(field)

    if normal_fields:
        lines.insert(0, "Updated {}".format(", ".join(normal_fields)))

    return "<br/>".join(lines)


@login_required
def puzzle_people(request, id):
    puzzle = get_object_or_404(Puzzle, id=id)
    user = request.user

    if request.method == "POST":
        form = PuzzlePeopleForm(request.POST, instance=puzzle)
        if form.is_valid():
            form.save()

            if form.changed_data:
                add_comment(
                    request=request,
                    puzzle=puzzle,
                    author=user,
                    is_system=True,
                    content=get_changed_data_message(form),
                )

            return redirect(urls.reverse("puzzle", args=[id]))
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

    return render(request, "puzzle_people.html", context)


@login_required
def edit_comment(request, id):
    comment = get_object_or_404(PuzzleComment, id=id)

    if request.user != comment.author:
        return render(
            request, "edit_comment.html", {"comment": comment, "not_author": True,}
        )
    elif comment.is_system:
        return render(
            request, "edit_comment.html", {"comment": comment, "is_system": True,}
        )

    if request.method == "POST":
        form = PuzzleCommentForm(request.POST)
        if form.is_valid():
            comment.content = form.cleaned_data["content"]
            comment.save()

            return redirect(urls.reverse("edit_comment", args=[id]))
        else:
            return render(
                request, "edit_comment.html", {"comment": comment, "form": form}
            )

    return render(
        request,
        "edit_comment.html",
        {"comment": comment, "form": PuzzleCommentForm({"content": comment.content}),},
    )


def warn_about_testsolving(is_spoiled, in_session, has_session):
    reasons = []
    if is_spoiled:
        reasons.append("you are spoiled")
    if in_session:
        reasons.append("you are already testsolving it")
    if has_session:
        reasons.append("there is an existing session you can join")

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

    if request.method == "POST":
        if "start_session" in request.POST:
            puzzle_id = request.POST["start_session"]
            puzzle = get_object_or_404(Puzzle, id=puzzle_id)
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

            return redirect(urls.reverse("testsolve_one", args=[session.id]))

    sessions = get_sessions_with_joined_and_current(request.user)
    current_sessions = sessions.filter(joined=True, current=True)

    part_subquery = TestsolveParticipation.objects.filter(
        session=OuterRef("pk"), user=user
    )[:1]
    past_sessions = sessions.filter(joined=True, current=False).annotate(
        fun_rating=Subquery(part_subquery.values("fun_rating")),
        difficulty_rating=Subquery(part_subquery.values("difficulty_rating")),
    )
    joinable_sessions = sessions.filter(joined=False, joinable=True)

    testsolvable_puzzles = (
        Puzzle.objects.filter(status=status.TESTSOLVING)
        .annotate(
            is_author=Exists(
                User.objects.filter(authored_puzzles=OuterRef("pk"), id=user.id)
            ),
            is_spoiled=Exists(
                User.objects.filter(spoiled_puzzles=OuterRef("pk"), id=user.id)
            ),
            in_session=Exists(current_sessions.filter(puzzle=OuterRef("pk"))),
            has_session=Exists(joinable_sessions.filter(puzzle=OuterRef("pk"))),
        )
        .order_by("priority")
    )

    testsolvable = [
        {
            "puzzle": puzzle,
            "warning": warn_about_testsolving(
                puzzle.is_spoiled, puzzle.in_session, puzzle.has_session
            ),
        }
        for puzzle in testsolvable_puzzles
    ]

    context = {
        "current_sessions": current_sessions,
        "past_sessions": past_sessions,
        "joinable_sessions": joinable_sessions,
        "testsolvable": testsolvable,
    }

    return render(request, "testsolve_main.html", context)


def normalize_answer(answer):
    return "".join(c for c in answer if c.isalnum()).upper()


class TestsolveSessionNotesForm(forms.ModelForm):
    notes = forms.CharField(widget=MarkdownTextarea, required=False)

    class Meta:
        model = TestsolveSession
        fields = ["notes"]


class GuessForm(forms.Form):
    guess = forms.CharField()


@login_required
def testsolve_one(request, id):
    session = get_object_or_404(TestsolveSession, id=id)
    puzzle = session.puzzle
    user = request.user

    if request.method == "POST":
        if "join" in request.POST:
            if not TestsolveParticipation.objects.filter(
                session=session, user=user
            ).exists():
                participation = TestsolveParticipation()
                participation.session = session
                participation.user = user
                participation.save()

                add_comment(
                    request=request,
                    puzzle=puzzle,
                    author=user,
                    testsolve_session=session,
                    is_system=True,
                    content="Joined testsolve session #{}".format(session.id),
                )

        elif "edit_notes" in request.POST:
            notes_form = TestsolveSessionNotesForm(request.POST, instance=session)
            if notes_form.is_valid():
                notes_form.save()

        elif "do_guess" in request.POST:
            participation = get_object_or_404(
                TestsolveParticipation, session=session, user=user,
            )
            guess_form = GuessForm(request.POST)
            if guess_form.is_valid():
                guess = guess_form.cleaned_data["guess"]
                normalized_guess = normalize_answer(guess)
                correct = any(
                    normalized_guess == normalize_answer(answer.answer)
                    for answer in session.puzzle.answers.all()
                )

                guess_model = TestsolveGuess(
                    session=session, user=user, guess=guess, correct=correct,
                )
                guess_model.save()

                if correct and session.joinable:
                    add_comment(
                        request=request,
                        puzzle=puzzle,
                        author=user,
                        testsolve_session=session,
                        is_system=True,
                        content="Correct answer: {}. Automatically marking session as no longer joinable".format(
                            guess
                        ),
                    )

                    session.joinable = False
                    session.save()
                else:
                    message = "{} answer guess: {}".format(
                        "Correct" if correct else "Incorrect", guess,
                    )
                    add_comment(
                        request=request,
                        puzzle=puzzle,
                        author=user,
                        testsolve_session=session,
                        is_system=True,
                        content=message,
                    )

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
        return redirect(urls.reverse("testsolve_one", args=[id]))

    try:
        participation = TestsolveParticipation.objects.get(session=session, user=user)
    except TestsolveParticipation.DoesNotExist:
        participation = None

    spoiled = is_spoiled_on(user, puzzle)
    answers_exist = session.puzzle.answers.exists()
    context = {
        "session": session,
        "participation": participation,
        "spoiled": spoiled,
        "answers_exist": answers_exist,
        "guesses": TestsolveGuess.objects.filter(session=session),
        "notes_form": TestsolveSessionNotesForm(instance=session),
        "guess_form": GuessForm(),
        "comment_form": PuzzleCommentForm(),
    }

    return render(request, "testsolve_one.html", context)


@login_required
def spoiled(request):
    puzzles = Puzzle.objects.filter(
        status__in=[status.TESTSOLVING, status.REVISING]
    ).annotate(
        is_spoiled=Exists(
            User.objects.filter(spoiled_puzzles=OuterRef("pk"), id=request.user.id)
        )
    )
    context = {"puzzles": puzzles}
    return render(request, "spoiled.html", context)


class PuzzleFinishForm(forms.Form):
    def __init__(self, fun, difficulty, hours_spent, *args, **kwargs):
        super(PuzzleFinishForm, self).__init__(*args, **kwargs)
        self.fields["fun"] = forms.ChoiceField(
            choices=[
                (None, "n/a"),
                (1, "1: not fun"),
                (2, "2: a little fun"),
                (3, "3: somewhat fun"),
                (4, "4: fun"),
                (5, "5: very fun"),
                (6, "6: extremely fun"),
            ],
            widget=forms.Select(),
            initial=fun,
            required=False,
        )
        self.fields["difficulty"] = forms.ChoiceField(
            choices=[
                (None, "n/a"),
                (1, "1: very easy"),
                (2, "2: easy"),
                (3, "3: somewhat difficult"),
                (4, "4: difficult"),
                (5, "5: very difficult"),
                (6, "6: extremely difficult"),
            ],
            widget=forms.Select(),
            initial=difficulty,
            required=False,
        )
        self.fields["hours_spent"] = forms.FloatField(
            widget=forms.NumberInput(),
            initial=hours_spent,
            required=False,
            min_value=0.0,
            help_text="Your best estimate of how many hours you spent on this puzzle. Decimal numbers are allowed.",
        )
        self.fields["spoil_me"] = forms.BooleanField(
            help_text="If checked, you will be spoiled on this puzzle and redirected to the puzzle discussion page.",
            initial=True,
            required=False,
        )
        self.fields["leave_session"] = forms.BooleanField(
            help_text="If checked, you will be removed from the session and will not receive notifications about comments or answer submissions. You can also use this to close duplicate sessions.",
            initial=False,
            required=False,
        )

    comment = forms.CharField(widget=MarkdownTextarea, required=False)


@login_required
def testsolve_finish(request, id):
    session = get_object_or_404(TestsolveSession, id=id)
    puzzle = session.puzzle
    user = request.user

    try:
        participation = TestsolveParticipation.objects.get(session=session, user=user)
    except TestsolveParticipation.DoesNotExist:
        participation = None

    if request.method == "POST" and participation:
        form = PuzzleFinishForm(
            participation.fun_rating,
            participation.difficulty_rating,
            participation.hours_spent,
            request.POST,
        )
        already_spoiled = is_spoiled_on(user, puzzle)
        if form.is_valid():
            print("valid")
            fun = form.cleaned_data["fun"] or None
            difficulty = form.cleaned_data["difficulty"] or None
            hours_spent = form.cleaned_data["hours_spent"] or None
            comment = form.cleaned_data["comment"]
            spoil_me = form.cleaned_data["spoil_me"]
            leave_session = form.cleaned_data["leave_session"]

            if already_spoiled:
                spoil_message = "(solver was already spoiled)"
            elif spoil_me:
                spoil_message = "👀 solver is now spoiled"
            elif leave_session:
                spoil_message = "🚪 solver left session"
            else:
                spoil_message = "❌ solver was not spoiled"

            ratings_text = "Fun: {} / Difficulty: {} / Hours spent: {} / {}".format(
                fun or "n/a", difficulty or "n/a", hours_spent or "n/a", spoil_message
            )

            if comment:
                comment_content = "Finished testsolve with comment:\n\n{}\n\n{}".format(
                    comment, ratings_text
                )
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
            participation.hours_spent = hours_spent
            participation.ended = datetime.datetime.now()
            participation.save()
            if leave_session:
                participation.delete()
            if spoil_me:
                if not already_spoiled:
                    puzzle.spoiled.add(user)
                return redirect(urls.reverse("puzzle", args=[puzzle.id]))
            else:
                return redirect(urls.reverse("testsolve_one", args=[id]))
        else:
            print("not valid")
            print(form.errors)
            context = {
                "session": session,
                "participation": participation,
                "form": form,
            }

            return render(request, "testsolve_finish.html", context)

    if participation:
        form = PuzzleFinishForm(
            participation.fun_rating,
            participation.difficulty_rating,
            participation.hours_spent,
        )
    else:
        form = None

    context = {
        "session": session,
        "participation": participation,
        "form": form,
    }

    return render(request, "testsolve_finish.html", context)


@login_required
def postprod(request):
    postprodding = Puzzle.objects.filter(
        status=status.NEEDS_POSTPROD, postprodders=request.user,
    )
    needs_postprod = Puzzle.objects.annotate(
        has_postprodder=Exists(User.objects.filter(postprodding_puzzles=OuterRef("pk")))
    ).filter(status=status.NEEDS_POSTPROD, has_postprodder=False)

    context = {
        "postprodding": postprodding,
        "needs_postprod": needs_postprod,
    }
    return render(request, "postprod.html", context)


@login_required
def factcheck(request):
    factchecking = Puzzle.objects.filter(
        (Q(status=status.NEEDS_FACTCHECK) | Q(status=status.NEEDS_COPY_EDITS))
        & Q(factcheckers=request.user)
    )
    needs_factcheck = Puzzle.objects.annotate(
        has_factchecker=Exists(User.objects.filter(factchecking_puzzles=OuterRef("pk")))
    ).filter(status=status.NEEDS_FACTCHECK, has_factchecker=False)

    needs_copyedit = Puzzle.objects.annotate(
        has_factchecker=Exists(User.objects.filter(factchecking_puzzles=OuterRef("pk")))
    ).filter(status=status.NEEDS_COPY_EDITS, has_factchecker=False)

    needs_copyedit_all = Puzzle.objects.filter(status=status.NEEDS_COPY_EDITS)

    context = {
        "factchecking": factchecking,
        "needs_factchecking": needs_factcheck,
        "needs_copyediting": needs_copyedit,
        "needs_copyediting_all": needs_copyedit_all,
    }
    return render(request, "factcheck.html", context)


@login_required
def awaiting_editor(request):
    return render(
        request,
        "awaiting_editor.html",
        {
            "puzzles": Puzzle.objects.filter(status=status.AWAITING_EDITOR)
            | Puzzle.objects.filter(
                tags__name="edit me"
            )  # TODO: remove this when we've moved to the new system
        },
    )


@login_required
def needs_editor(request):
    needs_editors = Puzzle.objects.annotate(
        remaining_des=(F("needed_discussion_editors") - Count("discussion_editors"))
    ).filter(remaining_des__gt=0)

    context = {"needs_editors": needs_editors}
    return render(request, "needs_editor.html", context)


class AnswerForm(forms.ModelForm):
    def __init__(self, round, *args, **kwargs):
        super(AnswerForm, self).__init__(*args, **kwargs)
        self.fields["round"] = forms.ModelChoiceField(
            queryset=Round.objects.all(),  # ???
            initial=round,
            widget=forms.HiddenInput(),
        )

    class Meta:
        model = PuzzleAnswer
        fields = ["answer", "round", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3, "cols": 40}),
        }


class RoundForm(forms.ModelForm):
    class Meta:
        model = Round
        fields = ["name", "description"]


@login_required
@permission_required("puzzle_editing.change_round")
def rounds(request):
    user = request.user

    new_round_form = RoundForm()
    if request.method == "POST":
        if "spoil_on" in request.POST:
            get_object_or_404(Round, id=request.POST["spoil_on"]).spoiled.add(user)

        elif "new_round" in request.POST:
            new_round_form = RoundForm(request.POST)
            if new_round_form.is_valid():
                new_round_form.save()

        elif "add_answer" in request.POST:
            answer_form = AnswerForm(None, request.POST)
            if answer_form.is_valid():
                answer_form.save()

        elif "delete_answer" in request.POST:
            get_object_or_404(PuzzleAnswer, id=request.POST["delete_answer"]).delete()

        return redirect(urls.reverse("rounds"))

    rounds = [
        {
            "id": round.id,
            "name": round.name,
            "description": round.description,
            "spoiled": round.spoiled.filter(id=user.id).exists(),
            "answers": [
                {
                    "answer": answer.answer,
                    "id": answer.id,
                    "notes": answer.notes,
                    "puzzles": answer.puzzles.all(),
                }
                for answer in round.answers.all()
            ],
            "form": AnswerForm(round),
        }
        for round in Round.objects.all()
    ]

    return render(
        request, "rounds.html", {"rounds": rounds, "new_round_form": RoundForm(),}
    )


@login_required
@permission_required("puzzle_editing.change_round")
def edit_round(request, id):
    round = get_object_or_404(Round, id=id)
    if request.method == "POST":
        print(request.POST)
        if request.POST.get("delete") and request.POST.get("sure-delete") == "on":
            round.delete()
            return redirect(urls.reverse("rounds"))
        form = RoundForm(request.POST, instance=round)
        if form.is_valid():
            form.save()

            return redirect(urls.reverse("rounds"))
        else:
            return render(request, "edit_round.html", {"form": form})
    return render(
        request,
        "edit_round.html",
        {
            "form": RoundForm(instance=round),
            "round": round,
            "has_answers": round.answers.count(),
        },
    )


@login_required
@permission_required("puzzle_editing.change_round")
def bulk_add_answers(request, id):
    round = get_object_or_404(Round, id=id)
    if request.method == "POST":
        lines = request.POST["bulk_add_answers"].split("\n")
        answers = [line.strip() for line in lines]

        PuzzleAnswer.objects.bulk_create(
            [PuzzleAnswer(answer=answer, round=round) for answer in answers if answer]
        )

        return redirect(urls.reverse("bulk_add_answers", args=[id]))

    return render(request, "bulk_add_answers.html", {"round": round,})


@login_required
def tags(request):
    return render(
        request,
        "tags.html",
        {"tags": PuzzleTag.objects.all().annotate(count=Count("puzzles"))},
    )


@login_required
def statistics(request):
    all_counts = (
        Puzzle.objects.values("status")
        .order_by("status")
        .annotate(count=Count("status"))
    )
    rest = dict((p["status"], p["count"]) for p in all_counts)
    tags = PuzzleTag.objects.filter(important=True)
    tag_counts = {}
    for tag in tags:
        query = (
            Puzzle.objects.filter(tags=tag)
            .values("status")
            .order_by("status")
            .annotate(count=Count("status"))
        )
        tag_counts[tag.name] = dict((p["status"], p["count"]) for p in query)
        for p in query:
            rest[p["status"]] -= p["count"]
    statuses = []
    for p in sorted(all_counts, key=lambda x: status.get_status_rank(x["status"])):
        status_obj = {
            "status": status.get_display(p["status"]),
            "count": p["count"],
            "rest_count": rest[p["status"]],
        }
        for tag in tags:
            status_obj[tag.name] = tag_counts[tag.name].get(p["status"], 0)
        statuses.append(status_obj)
    answers = {
        "assigned": PuzzleAnswer.objects.filter(puzzles__isnull=False).count(),
        "rest": PuzzleAnswer.objects.filter(puzzles__isnull=False).count(),
        "waiting": PuzzleAnswer.objects.filter(puzzles__isnull=True).count(),
    }
    for tag in tags:
        answers[tag.name] = PuzzleAnswer.objects.filter(
            puzzles__isnull=False, puzzles__tags=tag
        ).count()
        answers["rest"] -= answers[tag.name]

    image_base64 = curr_puzzle_graph_b64(request.GET.get("time", "alltime"))

    return render(
        request,
        "statistics.html",
        {
            "status": statuses,
            "tags": tags,
            "answers": answers,
            "image_base64": image_base64,
        },
    )


class PuzzleTagForm(forms.ModelForm):
    description = forms.CharField(
        widget=MarkdownTextarea,
        required=False,
        help_text="(optional) Elaborate on the meaning of this tag.",
    )

    class Meta:
        model = PuzzleTag
        fields = ["name", "description", "important"]


@login_required
def new_tag(request):
    if request.method == "POST":
        form = PuzzleTagForm(request.POST)
        if form.is_valid():
            form.save()

            return redirect(urls.reverse("tags"))
        else:
            return render(request, "new_tag.html", {"form": form})
    return render(request, "new_tag.html", {"form": PuzzleTagForm()})


@login_required
def single_tag(request, id):
    tag = get_object_or_404(PuzzleTag, id=id)

    count = tag.puzzles.count()
    if count == 1:
        label = "1 puzzle"
    else:
        label = "{} puzzles".format(count)
    return render(request, "single_tag.html", {"tag": tag, "count_label": label,})


@login_required
def edit_tag(request, id):
    tag = get_object_or_404(PuzzleTag, id=id)
    if request.method == "POST":
        form = PuzzleTagForm(request.POST, instance=tag)
        if form.is_valid():
            form.save()

            return redirect(urls.reverse("tags"))
        else:
            return render(request, "edit_tag.html", {"form": form, "tag": tag})
    return render(
        request, "edit_tag.html", {"form": PuzzleTagForm(instance=tag), "tag": tag,}
    )


@login_required
def users(request):
    # distinct=True because https://stackoverflow.com/questions/59071464/django-how-to-annotate-manytomany-field-with-count
    annotation_kwargs = dict()
    for key in ["authored", "discussing", "factchecking"]:
        annotation_kwargs[key + "_active"] = Count(
            key + "_puzzles",
            filter=~Q(
                **{
                    key
                    + "_puzzles__status__in": [
                        status.DEAD,
                        status.DEFERRED,
                        status.DONE,
                    ]
                }
            ),
            distinct=True,
        )

        annotation_kwargs[key + "_dead"] = Count(
            key + "_puzzles",
            filter=Q(**{key + "_puzzles__status": status.DEAD}),
            distinct=True,
        )
        annotation_kwargs[key + "_deferred"] = Count(
            key + "_puzzles",
            filter=Q(**{key + "_puzzles__status": status.DEFERRED}),
            distinct=True,
        )
        annotation_kwargs[key + "_done"] = Count(
            key + "_puzzles",
            filter=Q(**{key + "_puzzles__status": status.DONE}),
            distinct=True,
        )
    annotation_kwargs["testsolving_done"] = Count(
        "testsolve_participations",
        filter=Q(testsolve_participations__ended__isnull=False),
        distinct=True,
    )
    annotation_kwargs["testsolving_in_progress"] = Count(
        "testsolve_participations",
        filter=Q(testsolve_participations__ended__isnull=True),
        distinct=True,
    )

    users = User.objects.all().select_related("profile").annotate(**annotation_kwargs)

    users = list(users)
    for user in users:
        user.full_display_name = get_full_display_name(user)
        user.is_meta_editor = user.has_perm("puzzle_editing.change_round")

    return render(request, "users.html", {"users": users,})


@login_required
def users_statuses(request):
    # distinct=True because https://stackoverflow.com/questions/59071464/django-how-to-annotate-manytomany-field-with-count
    annotation_kwargs = {
        stat: Count(
            "authored_puzzles", filter=Q(authored_puzzles__status=stat), distinct=True
        )
        for stat in status.STATUSES
    }

    users = User.objects.all().select_related("profile").annotate(**annotation_kwargs)

    users = list(users)
    for user in users:
        user.full_display_name = get_full_display_name(user)
        user.is_meta_editor = user.has_perm("puzzle_editing.change_round")
        user.stats = [getattr(user, stat) for stat in status.STATUSES]

    return render(
        request,
        "users_statuses.html",
        {
            "users": users,
            "statuses": [status.DESCRIPTIONS[stat] for stat in status.STATUSES],
        },
    )


@login_required
def user(request, username: str):
    them = get_object_or_404(User, username=username)
    return render(
        request,
        "user.html",
        {
            "them": them,
            "testsolving_sessions": TestsolveSession.objects.filter(
                participations__user=them.id
            ),
        },
    )


@csrf_exempt
def preview_markdown(request):
    if request.method == "POST":
        output = render_to_string(
            "preview_markdown.html", {"input": request.body.decode("utf-8")}
        )
        return JsonResponse({"success": True, "output": output,})
    return JsonResponse({"success": False, "error": "No markdown input received",})
