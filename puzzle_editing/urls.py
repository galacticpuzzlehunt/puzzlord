from django.contrib.auth.views import LoginView
from django.contrib.auth.views import LogoutView
from django.contrib.auth.views import PasswordChangeDoneView
from django.contrib.auth.views import PasswordChangeView
from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("new", views.new, name="new"),
    path("login", LoginView.as_view(template_name="login.html"), name="login"),
    path("logout", LogoutView.as_view(template_name="logout.html"), name="logout"),
    path(
        "change-password",
        PasswordChangeView.as_view(template_name="change-password.html"),
    ),
    path(
        "change-password/done",
        PasswordChangeDoneView.as_view(template_name="change-password-done.html"),
        name="password_change_done",
    ),
    path("register", views.register, name="register"),
    path("authored", views.authored, name="authored"),
    path("all", views.all, name="all"),
    path("random_answers", views.random_answers, name="random_answers"),
    path("puzzle/<int:id>", views.puzzle, name="puzzle"),
    path("puzzle/<int:id>/edit", views.puzzle_edit, name="puzzle_edit"),
    path("puzzle/<int:id>/people", views.puzzle_people, name="puzzle_people"),
    path("puzzle/<int:id>/answers", views.puzzle_answers, name="puzzle_answers"),
    path("puzzle/<int:id>/tags", views.puzzle_tags, name="puzzle_tags"),
    path("puzzle/<int:id>/postprod", views.puzzle_postprod, name="puzzle_postprod"),
    path("puzzle/<int:id>/escape", views.puzzle_escape, name="puzzle_escape"),
    path("puzzle/postprodded/<int:id>.zip", views.postprod_zip, name="postprod_zip"),
    path("comment/<int:id>/edit", views.edit_comment, name="edit_comment"),
    path("hint/<int:id>", views.edit_hint, name="edit_hint"),
    path("testsolve", views.testsolve_main, name="testsolve_main"),
    path("testsolve_finder", views.testsolve_finder, name="testsolve_finder"),
    path("testsolve/<int:id>", views.testsolve_one, name="testsolve_one"),
    path("testsolve/<int:id>/finish", views.testsolve_finish, name="testsolve_finish"),
    path("postprod", views.postprod, name="postprod"),
    path("needs_editor", views.needs_editor, name="needs_editor"),
    path("awaiting_editor", views.awaiting_editor, name="awaiting_editor"),
    path("factcheck", views.factcheck, name="factcheck"),
    path("rounds", views.rounds, name="rounds"),
    path("answer/<int:id>", views.edit_answer, name="edit_answer"),
    path("rounds/<int:id>/edit", views.edit_round, name="edit_round"),
    path("rounds/<int:id>/bulk_add", views.bulk_add_answers, name="bulk_add_answers"),
    path("users", views.users, name="users"),
    path("users/editors", views.editors, name="editors"),
    path("users_statuses", views.users_statuses, name="users_statuses"),
    path("user/<str:username>", views.user, name="user"),
    path("account", views.account, name="account"),
    path("tags", views.tags, name="tags"),
    path("spoiled", views.spoiled, name="spoiled"),
    path("statistics", views.statistics, name="statistics"),
    path("tags/new", views.new_tag, name="new_tag"),
    path("tags/<int:id>", views.single_tag, name="single_tag"),
    path("tags/<int:id>/edit", views.edit_tag, name="edit_tag"),
    path("preview_markdown", views.preview_markdown, name="preview_markdown"),
]
