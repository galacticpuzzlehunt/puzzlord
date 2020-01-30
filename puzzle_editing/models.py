from django.db import models
from django.db.models import Exists, OuterRef
from django.contrib.auth.models import User
from enum import Enum
import puzzle_editing.status as status

# If we were starting puzzlord over, maybe follow these instructions:
# https://docs.djangoproject.com/en/2.2/topics/auth/customizing/#using-a-custom-user-model-when-starting-a-project
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name="profile")
    display_name = models.CharField(max_length=500, blank=True)
    discord_username = models.CharField(max_length=500, blank=True, help_text="Your Discord username and tag (e.g. example#1234)")
    bio = models.TextField(blank=True, help_text="Tell us about yourself. What kinds of puzzle genres or subject matter do you like?")

class Round(models.Model):
    """A round of answers feeding into the same metapuzzle or set of metapuzzles."""

    name = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    spoiled = models.ManyToManyField(User, blank=True, related_name="spoiled_rounds", help_text="Users spoiled on the round's answers.")

    def __str__(self):
        return "Round: {}".format(self.name)

class PuzzleAnswer(models.Model):
    """An answer. Can be assigned to zero, one, or more puzzles."""

    answer = models.CharField(max_length=500, blank=True)
    round = models.ForeignKey(Round, on_delete=models.PROTECT, related_name="answers")

    def __str__(self):
        return "{} (Round: {})".format(self.answer, self.round.name)

class Puzzle(models.Model):
    """A puzzle, that which Puzzlord keeps track of the writing process of."""

    name = models.CharField(max_length=500)
    codename = models.CharField(max_length=500, blank=True, help_text="A non-spoilery name if you're concerned about the name being a spoiler. Optional.")

    def spoiler_free_name(self):
        if self.codename:
            return "({})".format(self.codename)
        return self.name

    def spoiler_free_title(self):
        return "Puzzle {}: {}".format(self.id, self.spoiler_free_name())

    def spoilery_title(self):
        name = self.name
        if self.codename:
            name += " ({})".format(self.codename)
        return "Puzzle {}: {}".format(self.id, name)

    def __str__(self):
        return self.spoiler_free_title()

    authors = models.ManyToManyField(User, related_name='authored_puzzles', blank=True)
    discussion_editors = models.ManyToManyField(User, related_name='discussing_puzzles', blank=True)
    needed_discussion_editors = models.IntegerField(default=2)
    spoiled = models.ManyToManyField(User, related_name='spoiled_puzzles', blank=True, help_text="Users spoiled on the puzzle.")
    factcheckers = models.ManyToManyField(User, related_name='factchecking_puzzles', blank=True)
    postprodders = models.ManyToManyField(User, related_name='postprodding_puzzles', blank=True)

    # .get_status_display() will get the human-readable text
    status = models.CharField(
        max_length=status.MAX_LENGTH,
        choices=status.DESCRIPTIONS.items(),
        default=status.INITIAL_IDEA
    )
    def get_status_rank(self):
        return status.get_status_rank(self.status)

    def get_blocker(self):
        # just text describing what the category of blocker is, not a list of
        # Users or anything like that
        return status.get_blocker(self.status)

    def get_transitions(self):
        return [{
            "status": s,
            "status_display": status.get_display(s),
            "description": description,
        } for s, description in status.get_transitions(self.status)]

    last_updated = models.DateTimeField(auto_now=True)

    summary = models.TextField(blank=True, help_text="A non-spoilery description. Try to describe your puzzle in a way that potential testsolvers can guess if they'll enjoy your puzzle without being spoiled. Useful to mention: how long or difficult you expect the puzzle to be, whether this is more suitable for one solver or many solvers, etc.")
    description = models.TextField(help_text="A spoilery description of how the puzzle works.")
    answers = models.ManyToManyField(PuzzleAnswer, blank=True, related_name="puzzles")
    notes = models.TextField(blank=True)
    editor_notes = models.TextField(blank=True)
    priority = models.IntegerField(
            choices=(
                (1, "Very High"),
                (2, "High"),
                (3, "Medium"),
                (4, "Low"),
                (5, "Very Low"),
            ),
            default=3)
    content = models.TextField(blank=True, help_text="The puzzle itself. An external link is fine.")
    solution = models.TextField(blank=True)

    def editors_display(self):
        count = self.discussion_editors.count()
        if count:
            return "{} / {}: {}".format(count, self.needed_discussion_editors, ', '.join(editor.username for editor in self.discussion_editors.all()))
        else:
            return "{} / {}".format(count, self.needed_discussion_editors)

    def get_emails(self, exclude_emails=()):
        emails = set(self.authors.values_list('email', flat=True))
        emails |= set(self.discussion_editors.values_list('email', flat=True))
        emails |= set(self.factcheckers.values_list('email', flat=True))
        emails |= set(self.postprodders.values_list('email', flat=True))

        emails -= set(exclude_emails)
        emails -= set(('',))

        return list(emails)

class TestsolveSession(models.Model):
    """An attempt by a group of people to testsolve a puzzle.

    Participants in the session will be able to make comments and see other
    comments in the session. People spoiled on the puzzle can also comment and
    view the participants' comments.
    """

    puzzle = models.ForeignKey(Puzzle, on_delete=models.PROTECT, related_name="testsolve_sessions")
    started = models.DateTimeField(auto_now_add=True)
    joinable = models.BooleanField(default=False, help_text="Whether this puzzle is advertised to other users as a session they can join.")

    def participants(self):
        return User.objects.filter(testsolve_participations__session=self).annotate(
            current=Exists(
                TestsolveParticipation.objects.filter(
                    user=OuterRef('pk'),
                    ended=None
                )
            )
        )

    def __str__(self):
        return "Testsolve session #{} on {}".format(self.id, self.puzzle)

class PuzzleComment(models.Model):
    """A comment on a puzzle.

    All comments on a puzzle are visible to people spoiled on the puzzle.
    Comments may or may not be associated with a testsolve session; if they
    are, they will also be visible to people participating in or viewing the
    session."""

    puzzle = models.ForeignKey(Puzzle, on_delete=models.PROTECT, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name="comments")
    date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    is_system = models.BooleanField()
    testsolve_session = models.ForeignKey(TestsolveSession, on_delete=models.PROTECT, null=True, blank=True, related_name="comments")
    content = models.TextField()

    def __str__(self):
        return "Comment #{} on {}".format(self.id, self.puzzle)

class TestsolveParticipation(models.Model):
    """Represents one user's participation in a testsolve session.

    Used to record the user's start and end time, as well as ratings on the
    testsolve."""

    session = models.ForeignKey(TestsolveSession, on_delete=models.PROTECT, related_name="participations")
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="testsolve_participations")
    started = models.DateTimeField(auto_now_add=True)
    ended = models.DateTimeField(null=True, blank=True)
    fun_rating = models.IntegerField(null=True, blank=True)
    difficulty_rating = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return "Testsolve participation: {} in Session #{}".format(self.user.username, self.session.id)

class TestsolveGuess(models.Model):
    """A guess made by a user in a testsolve session."""

    class Meta:
        verbose_name_plural = "testsolve guesses"

    session = models.ForeignKey(TestsolveSession, on_delete=models.PROTECT, related_name="guesses")
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="guesses")
    guess = models.TextField(max_length=500, blank=True)
    correct = models.BooleanField()
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        correct_text = "Correct" if self.correct else "Incorrect"
        return "{}: {} guess by {} in Session #{}".format(self.guess, correct_text, self.user.username, self.session.id)

def is_spoiled_on(user, puzzle):
    return puzzle.spoiled.filter(id=user.id).exists() # is this really the best way??

def is_author_on(user, puzzle):
    return puzzle.authors.filter(id=user.id).exists()

def is_discussion_editor_on(user, puzzle):
    return puzzle.discussion_editors.filter(id=user.id).exists()

def is_factchecker_on(user, puzzle):
    return puzzle.factcheckers.filter(id=user.id).exists()

def is_postprodder_on(user, puzzle):
    return puzzle.postprodders.filter(id=user.id).exists()
