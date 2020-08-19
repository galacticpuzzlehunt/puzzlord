import json
import os
import shutil
from zipfile import ZipFile

import git
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from puzzle_editing.models import PuzzlePostprod


class Command(BaseCommand):
    help = """Sync puzzles into Hunt Repository."""

    def handle(self, *args, **options):
        repo = git.Repo.init(settings.HUNT_REPO)
        if (
            repo.is_dirty()
            or len(repo.untracked_files) > 0
            or repo.head.reference.name != "master"
        ):
            raise CommandError("Repository is in a broken state.")

        origin = repo.remotes.origin
        origin.pull()

        puzzleFolder = os.path.join(settings.HUNT_REPO, "puzzle")

        shutil.rmtree(puzzleFolder)
        os.makedirs(puzzleFolder)

        for pp in PuzzlePostprod.objects.all():
            answers = pp.puzzle.answers.all()
            answer = "???"
            if answers:
                answer = ", ".join(answers)
            metadata = {
                "puzzle_title": pp.puzzle.name,
                "credits": "by %s" % (pp.authors),
                "answer": answer,
                "puzzle_idea_id": pp.puzzle.id,
                "puzzle_slug": pp.slug,
            }
            puzzlePath = os.path.join(puzzleFolder, pp.slug)
            os.makedirs(puzzlePath)
            zipFile = pp.zip_file
            with ZipFile(zipFile) as zf:
                zf.extractall(puzzlePath)
            with open(os.path.join(puzzlePath, "metadata.json"), "w") as mf:
                json.dump(metadata, mf)
            repo.git.add(puzzlePath)

        if repo.is_dirty() or len(repo.untracked_files) > 0:
            repo.git.add(update=True)
            repo.git.add(A=True)
            repo.git.commit("-m", "Postprodding all puzzles.")
            origin.push()
