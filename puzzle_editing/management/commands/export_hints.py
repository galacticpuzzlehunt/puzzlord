import json
import os
import sys
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from puzzle_editing import status
from puzzle_editing.models import Puzzle
from puzzle_editing.models import PuzzleComment
from puzzle_editing.models import User


class Command(BaseCommand):
    help = """Export hints as JSON."""

    def handle(self, *args, **options):
        place = os.path.join(settings.HUNT_REPO, "puzzle")
        for puzzledir in os.listdir(place):
            datafile = os.path.join(place, puzzledir, "metadata.json")
            outdata = []
            try:
                with open(datafile) as data:
                    metadata = json.load(data)
                    puzzle = Puzzle.objects.get(id=metadata["puzzle_idea_id"])
                    for hint in puzzle.hints.all():
                        outdata.append(
                            [hint.order, hint.keywords.split(","), hint.content]
                        )
            except FileNotFoundError:
                pass
            except Exception as e:
                print(datafile, e)
                # sys.exit(1)
            hintfilename = os.path.join(place, puzzledir, "hints.json")
            if outdata:
                with open(hintfilename, "w") as hintfile:
                    json.dump(outdata, hintfile)
