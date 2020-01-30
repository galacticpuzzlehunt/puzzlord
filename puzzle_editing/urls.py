from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('new', views.new, name='new'),
    path('login', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout', LogoutView.as_view(template_name='logout.html'), name='logout'),
    path('change-password', PasswordChangeView.as_view(template_name='change-password.html')),
    path('register', views.register, name='register'),
    path('authored', views.authored, name='authored'),
    path('all', views.all, name='all'),
    path('puzzle/<int:id>', views.puzzle, name='puzzle'),
    path('puzzle/<int:id>/edit', views.puzzle_edit, name='puzzle_edit'),
    path('puzzle/<int:id>/people', views.puzzle_people, name='puzzle_people'),
    path('puzzle/<int:id>/answers', views.puzzle_answers, name='puzzle_answers'),
    path('testsolve', views.testsolve_main, name='testsolve_main'),
    path('testsolve/<int:id>', views.testsolve_one, name='testsolve_one'),
    path('testsolve/<int:id>/finish', views.testsolve_finish, name='testsolve_finish'),
    path('postprod', views.postprod, name='postprod'),
    path('needs_editor', views.needs_editor, name='needs_editor'),
    path('factcheck', views.factcheck, name='factcheck'),
    path('rounds', views.rounds, name='rounds'),
    path('users', views.users, name='users'),
    path('account', views.account, name='account'),

    path('preview_markdown', views.preview_markdown, name='preview_markdown'),
]
