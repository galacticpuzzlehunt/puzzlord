import json
import time

from django.core.management.base import BaseCommand

from puzzle_editing import status
from puzzle_editing.models import Puzzle
from puzzle_editing.models import PuzzleComment
from puzzle_editing.models import User


class Command(BaseCommand):
    help = """Import JSON feedback."""

    def add_arguments(self, parser):
        parser.add_argument("filename", type=str)
        parser.add_argument("user", type=str)

    def handle(self, *args, **options):
        print(options)
        user = User.objects.get(username=options["user"])
        with open(options["filename"]) as f:
            data = json.load(f)

        for line in data:
            puzzleid, comment, fun, diff = line
            content = (
                f"Feedback from BTS:\n\n{comment}\n\nFun: {fun} / Difficulty: {diff}"
            )
            comment = PuzzleComment.objects.create(
                puzzle=Puzzle.objects.get(id=puzzleid),
                author=user,
                is_system=True,
                content=content,
            )
            comment.save()
