from django.contrib import admin

from .models import Puzzle
from .models import PuzzleAnswer
from .models import PuzzleComment
from .models import Round
from .models import StatusSubscription
from .models import TestsolveGuess
from .models import TestsolveParticipation
from .models import TestsolveSession
from .models import UserProfile
from .models import Hint

admin.site.register(UserProfile)
admin.site.register(Round)
admin.site.register(PuzzleAnswer)
admin.site.register(Puzzle)
admin.site.register(StatusSubscription)
admin.site.register(TestsolveSession)
admin.site.register(PuzzleComment)
admin.site.register(TestsolveParticipation)
admin.site.register(TestsolveGuess)
admin.site.register(Hint)
