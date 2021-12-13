import json
import os
import shutil
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile

import git
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from puzzle_editing.models import PuzzlePostprod


def extract_uploaded_zip_in_place(zip_path):
    dir_path = os.path.splitext(zip_path)[0]
    if not os.path.isdir(dir_path):
        os.mkdir(dir_path)
        with ZipFile(zip_path, "r") as f:
            f.extractall(dir_path)


def get_upload_url(file_field):
    _, ext = os.path.splitext(file_field.path)
    if ext == ".zip":
        return file_field.url[:-4] + "/"
    return file_field.url


def get_latest_zip(pp):
    try:
        repo = git.Repo.init(settings.HUNT_REPO)
    except BaseException:
        pp.slug = "THIS_URL_IS_FAKE_SINCE_YOU_UPLOADED_THIS_PUZZLE_ON_LOCAL"
        return

    if (
        repo.is_dirty()
        or len(repo.untracked_files) > 0
        or repo.head.reference.name != "master"
    ):
        raise Exception("Repository is in a broken state.")

    origin = repo.remotes.origin
    origin.pull()

    puzzleFolder = os.path.join(settings.HUNT_REPO, "puzzle")
    puzzlePath = os.path.join(puzzleFolder, pp.slug)
    zipPath = f"/tmp/puzzle{pp.puzzle.id}.zip"

    if os.path.exists(zipPath):
        os.remove(zipPath)

    with ZipFile(zipPath, "w", ZIP_DEFLATED) as zipHandle:
        for root, dirs, files in os.walk(puzzlePath):
            for file in files:
                if file != "metadata.json":
                    zipHandle.write(
                        os.path.join(root, file),
                        os.path.relpath(os.path.join(root, file), puzzlePath),
                    )

    return zipPath


def deploy_puzzle(pp, deploy_zip=True):
    try:
        repo = git.Repo.init(settings.HUNT_REPO)
    except BaseException:
        pp.slug = "THIS_URL_IS_FAKE_SINCE_YOU_UPLOADED_THIS_PUZZLE_ON_LOCAL"
        return

    if (
        repo.is_dirty()
        or len(repo.untracked_files) > 0
        or repo.head.reference.name != "master"
    ):
        raise Exception("Repository is in a broken state.")

    origin = repo.remotes.origin
    origin.pull()

    puzzleFolder = os.path.join(settings.HUNT_REPO, "puzzle")
    answers = pp.puzzle.answers.all()
    answer = "???"
    if answers:
        answer = ", ".join(a.answer for a in answers)
    metadata = {
        "puzzle_title": pp.puzzle.name,
        "credits": "by %s" % (pp.authors),
        "answer": answer,
        "puzzle_idea_id": pp.puzzle.id,
        "puzzle_slug": pp.slug,
    }
    puzzlePath = os.path.join(puzzleFolder, pp.slug)
    if deploy_zip:
        if os.path.exists(puzzlePath):
            shutil.rmtree(puzzlePath)
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
        repo.git.commit("-m", "Postprodding '%s'." % (pp.slug))
        origin.push()
