import logging
from datetime import datetime

import django.urls as urls
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.test import TestCase

from . import status
from . import views
from .models import Puzzle
from .models import Round
from .models import TestsolveParticipation
from .models import TestsolveSession

logging.disable(logging.DEBUG)  # there's a particular template lookup failure
# in a view that really doesn't seem relevant


def create_user(name):
    return User.objects.create_user(
        username=name, email=name + "@example.com", password=name + "secret"
    )


class Misc(TestCase):
    def setUp(self):
        self.a = User.objects.create_user(
            username="a", email="a@example.com", password="secret"
        )
        self.b = User.objects.create_user(
            username="b", email="b@example.com", password="password"
        )
        self.c = User.objects.create_user(
            username="c", email="c@example.com", password="password"
        )

        # meta editor
        permission = Permission.objects.get(
            content_type=ContentType.objects.get_for_model(Round),
            codename="change_round",
        )
        self.a.user_permissions.add(permission)

        self.puzzle1 = Puzzle(
            name="Spoilery Title",
            codename="codename",
            status=status.TESTSOLVING,
            status_mtime=datetime.fromtimestamp(0),
        )
        self.puzzle1.save()
        self.puzzle1.authors.add(self.a)
        self.puzzle1.spoiled.add(self.a)
        self.puzzle2 = Puzzle(
            name="Spoilery Title 2",
            codename="codename 2",
            status_mtime=datetime.fromtimestamp(0),
        )
        self.puzzle2.save()
        self.puzzle2.authors.add(self.b)
        self.puzzle2.spoiled.add(self.b)
        self.puzzle3 = Puzzle(
            name="Spoilery Title 3",
            codename="codename 3",
            status_mtime=datetime.fromtimestamp(0),
        )
        self.puzzle3.save()
        self.puzzle3.authors.add(self.a)
        self.puzzle3.spoiled.add(self.a)
        self.puzzle3.spoiled.add(self.b)
        self.puzzle3.editors.add(self.b)

        self.session1 = TestsolveSession(puzzle=self.puzzle1)
        self.session1.save()

        self.participation1 = TestsolveParticipation(session=self.session1, user=self.b)
        self.participation1.save()

    def test_index(self):
        c = Client()
        c.login(username="b", password="password")

        response = c.get(urls.reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(
            response.context["inbox_puzzles"].order_by("id"),
            [repr(self.puzzle2), repr(self.puzzle3)],
        )

        response = c.get(urls.reverse("puzzle", args=[self.puzzle2.id]))
        response = c.get(urls.reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(
            response.context["inbox_puzzles"].order_by("id"), [repr(self.puzzle3)]
        )

    def test_authored(self):
        c = Client()
        c.login(username="b", password="password")

        response = c.get(urls.reverse("authored"))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context["puzzles"], [repr(self.puzzle2)])
        self.assertQuerysetEqual(
            response.context["editing_puzzles"], [repr(self.puzzle3)]
        )

    def test_all(self):
        c = Client()
        c.login(username="b", password="password")

        response = c.get(urls.reverse("all"))
        self.assertEqual(response.status_code, 200)
        # TODO add more

    def test_puzzle(self):
        c = Client()
        c.login(username="b", password="password")

        response = c.get(urls.reverse("puzzle", args=[self.puzzle1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "puzzle_unspoiled.html")

        response = c.get(urls.reverse("puzzle", args=[self.puzzle2.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "puzzle.html")
        self.assertTrue(response.context["is_author"])
        self.assertFalse(response.context["is_editor"])

        response = c.get(urls.reverse("puzzle", args=[self.puzzle3.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "puzzle.html")
        self.assertFalse(response.context["is_author"])
        self.assertTrue(response.context["is_editor"])

    def test_puzzle_subpage_sanity(self):
        c = Client()
        c.login(username="a", password="secret")

        for urlname in [
            "puzzle_edit",
            "puzzle_people",
            "puzzle_answers",
            "puzzle_tags",
            "puzzle_postprod",
        ]:
            self.assertEqual(
                c.get(urls.reverse(urlname, args=[self.puzzle1.id])).status_code, 200
            )

    def test_testsolve_main(self):
        c = Client()
        c.login(username="b", password="password")

        response = c.get(urls.reverse("testsolve_main"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["testsolvable"]), 1)
        self.assertEqual(
            response.context["testsolvable"][0]["puzzle"].id, self.puzzle1.id
        )

    def test_testsolve_one(self):
        ac = Client()
        ac.login(username="a", password="secret")

        response = ac.get(urls.reverse("testsolve_one", args=[self.session1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["spoiled"])
        self.assertIsNone(response.context["participation"])

        bc = Client()
        bc.login(username="b", password="password")

        response = bc.get(urls.reverse("testsolve_one", args=[self.session1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["spoiled"])
        self.assertIsNotNone(response.context["participation"])

        cc = Client()
        cc.login(username="c", password="password")

        response = cc.get(urls.reverse("testsolve_one", args=[self.session1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["spoiled"])
        self.assertIsNone(response.context["participation"])

    def test_testsolve_finish(self):
        ac = Client()
        ac.login(username="a", password="secret")

        response = ac.get(urls.reverse("testsolve_finish", args=[self.session1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["participation"])

        bc = Client()
        bc.login(username="b", password="password")

        response = bc.get(urls.reverse("testsolve_finish", args=[self.session1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["participation"])

    def test_rest_sanity(self):
        ac = Client()
        ac.login(username="a", password="secret")

        bc = Client()
        bc.login(username="b", password="password")

        for client in [ac, bc]:
            for urlname in [
                "postprod",
                "needs_editor",
                "awaiting_editor",
                "factcheck",
                "users",
                "users_statuses",
                "account",
                "tags",
                "spoiled",
                "statistics",
                "new_tag",
            ]:
                self.assertEqual(
                    client.get(urls.reverse(urlname)).status_code, 200, urlname
                )

        self.assertEqual(
            ac.get(urls.reverse("rounds")).status_code,
            200,
            "rounds works for meta editor",
        )
        self.assertEqual(
            bc.get(urls.reverse("rounds")).status_code,
            302,
            "rounds doesn't work for non-meta-editor",
        )
