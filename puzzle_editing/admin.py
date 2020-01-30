from django.contrib import admin

from .models import UserProfile, Round, PuzzleAnswer, Puzzle, TestsolveSession, PuzzleComment, TestsolveParticipation, TestsolveGuess

admin.site.register(UserProfile)
admin.site.register(Round)
admin.site.register(PuzzleAnswer)
admin.site.register(Puzzle)
admin.site.register(TestsolveSession)
admin.site.register(PuzzleComment)
admin.site.register(TestsolveParticipation)
admin.site.register(TestsolveGuess)
