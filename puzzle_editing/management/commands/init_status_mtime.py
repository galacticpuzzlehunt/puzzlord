import time

from django.core.management.base import BaseCommand

from puzzle_editing import status
from puzzle_editing.models import Puzzle
from puzzle_editing.models import PuzzleComment

rev_status_map = {}
for st in status.STATUSES:
    rev_status_map[status.get_display(st)] = st


def parse_comment(comment: str):
    if comment == "Created puzzle":
        return status.INITIAL_IDEA
    elif comment.startswith("Status changed to "):
        if comment[18:] in rev_status_map:
            return rev_status_map[comment[18:]]
        else:
            print("Missing status in map:", comment)
            return None


class Command(BaseCommand):
    help = """Fix up the status mtime field."""

    def handle(self, *args, **options):
        comments = PuzzleComment.objects.filter(is_system=True).order_by("date")
        last_updates = {}
        for comment in comments:
            if parse_comment(comment.content):
                last_updates[comment.puzzle.pk] = comment.date

        for pk, mtime in last_updates.items():
            time.sleep(0.1)  # this avoids strange database overload issues
            print(f"Processing puzzle #{pk}")
            Puzzle.objects.filter(pk=pk).update(status_mtime=mtime)
