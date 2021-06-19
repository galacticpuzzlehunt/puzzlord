import os
import random
import time
from enum import Enum

import django.urls as urls
from django import forms
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Avg
from django.db.models import Exists
from django.db.models import OuterRef
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.html import format_html
from django.utils.html import format_html_join
from django.utils.html import mark_safe

import puzzle_editing.status as status


# If we were starting puzzlord over, maybe follow these instructions:
# https://docs.djangoproject.com/en/2.2/topics/auth/customizing/#using-a-custom-user-model-when-starting-a-project
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name="profile")
    display_name = models.CharField(max_length=500, blank=True)
    discord_username = models.CharField(
        max_length=500,
        blank=True,
        help_text="Your Discord username and tag (e.g. example#1234)",
    )
    credits_name = models.CharField(
        max_length=80,
        help_text="How you want your name to appear in puzzle credits, e.g. Ben Bitdiddle",
    )
    bio = models.TextField(
        blank=True,
        help_text="Tell us about yourself. What kinds of puzzle genres or subject matter do you like?",
    )
    enable_keyboard_shortcuts = models.BooleanField(default=False)

    @staticmethod
    def profile_display_name_of(user):
        try:
            return user.profile.display_name
        except UserProfile.DoesNotExist:
            return None

    # Some of this templating is done in an inner loop, so doing it with
    # inclusion tags turns out to be a big performance hit. They're also small
    # enough to be pretty easy to write in Python. Separating out the versions
    # that don't even bother taking a User and just take two strings might be a
    # bit premature, but I think skipping prefetching and model construction is
    # worth it in an inner loop...
    @staticmethod
    def html_user_display_of_flat(username, display_name, linkify):
        if display_name:
            ret = format_html('<span title="{}">{}</span>', username, display_name)
        else:
            ret = username

        if linkify:
            return format_html(
                '<a href="{}">{}</a>', urls.reverse("user", args=[username]), ret
            )
        else:
            return ret

    @staticmethod
    def html_user_display_of(user, linkify):
        return UserProfile.html_user_display_of_flat(
            user.username, UserProfile.profile_display_name_of(user), linkify
        )

    @staticmethod
    def html_user_list_of_flat(ud_pairs, linkify):
        # iterate over ud_pairs exactly once
        s = format_html_join(
            ", ",
            "{}",
            (
                (UserProfile.html_user_display_of_flat(un, dn, linkify),)
                for un, dn in ud_pairs
            ),
        )
        return s or mark_safe('<span class="empty">(none)</span>')

    @staticmethod
    def html_user_list_of(users, linkify):
        return UserProfile.html_user_list_of_flat(
            (
                (user.username, UserProfile.profile_display_name_of(user))
                for user in users
            ),
            linkify,
        )

    def __str__(self):
        return "Profile of {}".format(self.user)


class Round(models.Model):
    """A round of answers feeding into the same metapuzzle or set of metapuzzles."""

    name = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    spoiled = models.ManyToManyField(
        User,
        blank=True,
        related_name="spoiled_rounds",
        help_text="Users spoiled on the round's answers.",
    )

    def __str__(self):
        return "Round: {}".format(self.name)


class PuzzleAnswer(models.Model):
    """An answer. Can be assigned to zero, one, or more puzzles."""

    answer = models.CharField(max_length=500, blank=True)
    round = models.ForeignKey(Round, on_delete=models.PROTECT, related_name="answers")
    notes = models.TextField(blank=True)

    def __str__(self):
        return "{} (Round: {})".format(self.answer, self.round.name)


class PuzzleTag(models.Model):
    """A tag to classify puzzles."""

    name = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    important = models.BooleanField(
        default=False,
        help_text="Important tags are displayed prominently with the puzzle title.",
    )

    def __str__(self):
        return "Tag: {}".format(self.name)


class Puzzle(models.Model):
    """A puzzle, that which Puzzlord keeps track of the writing process of."""

    name = models.CharField(max_length=500)
    codename = models.CharField(
        max_length=500,
        blank=True,
        help_text="A non-spoilery name if you're concerned about the name being a spoiler. Optional.",
    )

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

    def important_tag_names(self):
        if hasattr(self, "prefetched_important_tag_names"):
            return self.prefetched_important_tag_names
        return self.tags.filter(important=True).values_list("name", flat=True)

    # This is done in an inner loop, so doing it with inclusion tags turns
    # out to be a big performance hit. They're also small enough to be pretty
    # easy to write in Python.
    def html_display(self):
        return format_html(
            "{}: {} {}",
            self.id,
            format_html_join(
                " ",
                "<sup>[{}]</sup>",
                ((name,) for name in self.important_tag_names()),
            ),
            self.spoiler_free_name(),
        )

    def html_link(self):
        return format_html(
            """<a href="{}" class="puzzle-link">{}</a>""",
            urls.reverse("puzzle", args=[self.id]),
            self.html_display(),
        )

    def __str__(self):
        return self.spoiler_free_title()

    authors = models.ManyToManyField(User, related_name="authored_puzzles", blank=True)
    editors = models.ManyToManyField(User, related_name="editing_puzzles", blank=True)
    needed_editors = models.IntegerField(default=2)
    spoiled = models.ManyToManyField(
        User,
        related_name="spoiled_puzzles",
        blank=True,
        help_text="Users spoiled on the puzzle.",
    )
    factcheckers = models.ManyToManyField(
        User, related_name="factchecking_puzzles", blank=True
    )
    postprodders = models.ManyToManyField(
        User, related_name="postprodding_puzzles", blank=True
    )

    # .get_status_display() will get the human-readable text
    status = models.CharField(
        max_length=status.MAX_LENGTH,
        choices=status.DESCRIPTIONS.items(),
        default=status.INITIAL_IDEA,
    )
    status_mtime = models.DateTimeField(editable=False)

    def get_status_rank(self):
        return status.get_status_rank(self.status)

    def get_blocker(self):
        # just text describing what the category of blocker is, not a list of
        # Users or anything like that
        return status.get_blocker(self.status)

    def get_transitions(self):
        return [
            {
                "status": s,
                "status_display": status.get_display(s),
                "description": description,
            }
            for s, description in status.get_transitions(self.status)
        ]

    last_updated = models.DateTimeField(auto_now=True)

    summary = models.TextField(
        blank=True,
        help_text="A non-spoilery description. Try to describe your puzzle in a way that potential testsolvers can guess if they'll enjoy your puzzle without being spoiled. Useful to mention: how long or difficult you expect the puzzle to be, whether this is more suitable for one solver or many solvers, etc.",
    )
    description = models.TextField(
        help_text="A spoilery description of how the puzzle works."
    )
    answers = models.ManyToManyField(PuzzleAnswer, blank=True, related_name="puzzles")
    notes = models.TextField(blank=True)
    editor_notes = models.TextField(blank=True)
    tags = models.ManyToManyField(PuzzleTag, blank=True, related_name="puzzles")
    priority = models.IntegerField(
        choices=(
            (1, "Very High"),
            (2, "High"),
            (3, "Medium"),
            (4, "Low"),
            (5, "Very Low"),
        ),
        default=3,
    )

    content = models.TextField(
        blank=True,
        help_text="The puzzle itself. An external link is fine.",
    )

    def uploaded_content_path(instance, filename):
        _, ext = os.path.splitext(filename.lower())
        return f"uploaded_content/{instance.id}/{int(time.time())}-{random.randrange(1000000)}{ext}"

    uploaded_content = models.FileField(
        upload_to=uploaded_content_path,
        null=True,
        blank=True,
        help_text="An uploaded file of the puzzle itself. It may be a text file, PDF, etc. or it may be a zip file containing an index.html page as well as additional assets.",
    )

    solution = models.TextField(
        blank=True,
    )

    def uploaded_solution_path(instance, filename):
        _, ext = os.path.splitext(filename.lower())
        return f"uploaded_solution/{instance.id}/{int(time.time())}-{random.randrange(1000000)}{ext}"

    uploaded_solution = models.FileField(
        upload_to=uploaded_solution_path,
        null=True,
        blank=True,
        help_text="An uploaded file of the puzzle solution. It may be a text file, PDF, etc. or it may be a zip file containing an index.html page as well as additional assets.",
    )

    def get_emails(self, exclude_emails=()):
        emails = set(self.authors.values_list("email", flat=True))
        emails |= set(self.editors.values_list("email", flat=True))
        emails |= set(self.factcheckers.values_list("email", flat=True))
        emails |= set(self.postprodders.values_list("email", flat=True))

        emails -= set(exclude_emails)
        emails -= set(("",))

        return list(emails)

    def has_postprod(self):
        try:
            return self.postprod is not None
        except PuzzlePostprod.DoesNotExist:
            return False

    def has_hints(self):
        return self.hints.count() > 0

    def ordered_hints(self):
        return self.hints.order_by("order")

    def has_answer(self):
        return self.answers.count() > 0


@receiver(pre_save, sender=Puzzle)
def set_status_mtime(sender, instance, **kwargs):
    try:
        obj = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        pass  # Object is new
    else:
        if obj.status != instance.status:  # Field has changed
            instance.status_mtime = timezone.now()


def get_location_for_upload(instance, filename):
    return f"puzzle_postprods/puzzle_{instance.puzzle.id}.zip"


def sizeof_fmt(num, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, "Yi", suffix)


class PuzzlePostprod(models.Model):
    puzzle = models.OneToOneField(
        Puzzle, on_delete=models.CASCADE, related_name="postprod"
    )
    slug = models.CharField(
        max_length=50,
        null=False,
        blank=False,
        validators=[RegexValidator(regex=r'[^<>#%"\'|{})(\[\]\/\\\^?=`;@&, ]{1,50}')],
        help_text="The part of the URL on the hunt site referrring to this puzzle. E.g. for https://puzzle.hunt/puzzle/fifty-fifty, this would be 'fifty-fifty'.",
    )
    zip_file = models.FileField(
        upload_to=get_location_for_upload,
        help_text="A zip file as described above. Leave it blank to keep it the same if you already uploaded one and just want to change the metadata.",
        validators=[FileExtensionValidator(["zip"])],
    )
    authors = models.CharField(
        max_length=200,
        null=False,
        blank=False,
        help_text="The puzzle authors, as displayed on the solution page",
    )
    complicated_deploy = models.BooleanField(
        help_text="Check this box if your puzzle involves a serverside component of some sort, and it is not entirely contained in the zip file. If you don't know what this means, you probably don't want to check this box."
    )
    mtime = models.DateTimeField(auto_now=True)

    def get_size(self):
        if self.zip_file:
            return sizeof_fmt(self.zip_file.size)
        else:
            return "(Could not obtain size, zip file does not exist!)"


class StatusSubscription(models.Model):
    """An indication to email a user when any puzzle enters this status."""

    status = models.CharField(
        max_length=status.MAX_LENGTH,
        choices=status.DESCRIPTIONS.items(),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return "{} subscription to {}".format(
            self.user, status.get_display(self.status)
        )


class PuzzleVisited(models.Model):
    """A model keeping track of when a user last visited a puzzle page."""

    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{} visited {}".format(self.user.username, self.puzzle)


class TestsolveSession(models.Model):
    """An attempt by a group of people to testsolve a puzzle.

    Participants in the session will be able to make comments and see other
    comments in the session. People spoiled on the puzzle can also comment and
    view the participants' comments.
    """

    puzzle = models.ForeignKey(
        Puzzle, on_delete=models.PROTECT, related_name="testsolve_sessions"
    )
    started = models.DateTimeField(auto_now_add=True)
    joinable = models.BooleanField(
        default=False,
        help_text="Whether this puzzle is advertised to other users as a session they can join.",
    )
    notes = models.TextField(blank=True)

    def participants(self):
        return User.objects.filter(testsolve_participations__session=self).annotate(
            current=Exists(
                TestsolveParticipation.objects.filter(user=OuterRef("pk"), ended=None)
            )
        )

    def active_participants(self):
        return User.objects.filter(
            testsolve_participations__session=self, testsolve_participations__ended=None
        )

    def get_done_participants_display(self):
        participations = TestsolveParticipation.objects.filter(session=self)
        done_participations = participations.filter(ended__isnull=False)
        return "{} / {}".format(done_participations.count(), participations.count())

    def has_correct_guess(self):
        return TestsolveGuess.objects.filter(session=self, correct=True).exists()

    def get_average_fun(self):
        return TestsolveParticipation.objects.filter(session=self).aggregate(
            Avg("fun_rating")
        )["fun_rating__avg"]

    def get_average_diff(self):
        return TestsolveParticipation.objects.filter(session=self).aggregate(
            Avg("difficulty_rating")
        )["difficulty_rating__avg"]

    def get_average_hours(self):
        return TestsolveParticipation.objects.filter(session=self).aggregate(
            Avg("hours_spent")
        )["hours_spent__avg"]

    def get_emails(self, exclude_emails=()):
        emails = set(self.puzzle.get_emails())
        emails |= set(self.participants().values_list("email", flat=True))

        emails -= set(exclude_emails)
        emails -= set(("",))

        return list(emails)

    def __str__(self):
        return "Testsolve session #{} on {}".format(self.id, self.puzzle)


class PuzzleComment(models.Model):
    """A comment on a puzzle.

    All comments on a puzzle are visible to people spoiled on the puzzle.
    Comments may or may not be associated with a testsolve session; if they
    are, they will also be visible to people participating in or viewing the
    session."""

    puzzle = models.ForeignKey(
        Puzzle, on_delete=models.PROTECT, related_name="comments"
    )
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name="comments")
    date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    is_system = models.BooleanField()
    testsolve_session = models.ForeignKey(
        TestsolveSession,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="comments",
    )
    content = models.TextField(
        blank=True,
        help_text="The content of the comment. Should probably only be blank if the status_change is set.",
    )
    status_change = models.CharField(
        max_length=status.MAX_LENGTH,
        choices=status.DESCRIPTIONS.items(),
        blank=True,
        help_text="Any status change caused by this comment. Only used for recording history and computing statistics; not a source of truth (i.e. the puzzle will still store its current status, and this field's value on any comment doesn't directly imply anything about that in any technically enforced way).",
    )

    def __str__(self):
        return "Comment #{} on {}".format(self.id, self.puzzle)


class CommentReaction(models.Model):
    # Since these are frivolous and display-only, I'm not going to bother
    # restricting them on the database model layer.
    EMOJI_OPTIONS = ["👍", "👎", "🎉", "❤️", "😄", "🤔", "😕", "❓", "👀", "✈️"]
    emoji = models.CharField(max_length=8)
    comment = models.ForeignKey(
        PuzzleComment, on_delete=models.CASCADE, related_name="reactions"
    )
    reactor = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reactions"
    )

    def __str__(self):
        return "{} reacted {} on {}".format(
            self.reactor.username, self.emoji, self.comment
        )

    class Meta:
        unique_together = ("emoji", "comment", "reactor")

    @classmethod
    def toggle(cls, emoji, comment, reactor):
        # This just lets you react with any string to a comment, but it's
        # not the end of the world.
        my_reactions = cls.objects.filter(comment=comment, emoji=emoji, reactor=reactor)
        # Force the queryset instead of checking if it's empty because, if
        # it's not empty, we care about its contents.
        if len(my_reactions) > 0:
            my_reactions.delete()
        else:
            cls(emoji=emoji, comment=comment, reactor=reactor).save()


class TestsolveParticipation(models.Model):
    """Represents one user's participation in a testsolve session.

    Used to record the user's start and end time, as well as ratings on the
    testsolve."""

    session = models.ForeignKey(
        TestsolveSession, on_delete=models.PROTECT, related_name="participations"
    )
    user = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="testsolve_participations"
    )
    started = models.DateTimeField(auto_now_add=True)
    ended = models.DateTimeField(null=True, blank=True)
    fun_rating = models.IntegerField(null=True, blank=True)
    difficulty_rating = models.IntegerField(null=True, blank=True)
    hours_spent = models.FloatField(null=True, blank=True)

    def __str__(self):
        return "Testsolve participation: {} in Session #{}".format(
            self.user.username, self.session.id
        )


class TestsolveGuess(models.Model):
    """A guess made by a user in a testsolve session."""

    class Meta:
        verbose_name_plural = "testsolve guesses"

    session = models.ForeignKey(
        TestsolveSession, on_delete=models.PROTECT, related_name="guesses"
    )
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="guesses")
    guess = models.TextField(max_length=500, blank=True)
    correct = models.BooleanField()
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        correct_text = "Correct" if self.correct else "Incorrect"
        return "{}: {} guess by {} in Session #{}".format(
            self.guess, correct_text, self.user.username, self.session.id
        )


def is_spoiled_on(user, puzzle):
    return puzzle.spoiled.filter(id=user.id).exists()  # is this really the best way??


def is_author_on(user, puzzle):
    return puzzle.authors.filter(id=user.id).exists()


def is_editor_on(user, puzzle):
    return puzzle.editors.filter(id=user.id).exists()


def is_factchecker_on(user, puzzle):
    return puzzle.factcheckers.filter(id=user.id).exists()


def is_postprodder_on(user, puzzle):
    return puzzle.postprodders.filter(id=user.id).exists()


def get_user_role(user, puzzle):
    if is_author_on(user, puzzle):
        return "author"
    elif is_editor_on(user, puzzle):
        return "editor"
    elif is_postprodder_on(user, puzzle):
        return "postprodder"
    elif is_factchecker_on(user, puzzle):
        return "factchecker"
    else:
        return None


class Hint(models.Model):
    class Meta:
        ordering = ["order"]

    puzzle = models.ForeignKey(Puzzle, on_delete=models.PROTECT, related_name="hints")
    order = models.FloatField(
        blank=False,
        null=False,
        help_text="Order in the puzzle - use 0 for a hint at the very beginning of the puzzle, or 100 for a hint on extraction, and then do your best to extrapolate in between. Decimals are okay. For multiple subpuzzles, assign a whole number to each subpuzzle and use decimals off of that whole number for multiple hints in the subpuzzle.",
    )
    keywords = models.CharField(
        max_length=100,
        blank=True,
        null=False,
        help_text="Comma-separated keywords to look for in hunters' hint requests before displaying this hint suggestion",
    )
    content = models.CharField(
        max_length=1000,
        blank=False,
        null=False,
        help_text="Canned hint to give a team (can be edited by us before giving it)",
    )

    def get_keywords(self):
        return self.keywords.split(",")

    def __str__(self):
        return f"Hint #{self.order} for {self.puzzle}"


class SiteSetting(models.Model):
    """Arbitrary settings we don't want to customize from code."""

    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()

    def __str__(self):
        return "{} = {}".format(self.key, self.value)

    @classmethod
    def get_setting(cls, key):
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_int_setting(cls, key):
        try:
            return int(cls.objects.get(key=key).value)
        except cls.DoesNotExist:
            return None
        except ValueError:
            return None
