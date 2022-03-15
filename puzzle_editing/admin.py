from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CommentReaction
from .models import Hint
from .models import Puzzle
from .models import PuzzleAnswer
from .models import PuzzleComment
from .models import PuzzlePostprod
from .models import PuzzleTag
from .models import PuzzleVisited
from .models import Round
from .models import SiteSetting
from .models import StatusSubscription
from .models import TestsolveGuess
from .models import TestsolveParticipation
from .models import TestsolveSession
from .models import User

admin.site.register(User, UserAdmin)
admin.site.register(Round)
admin.site.register(PuzzleAnswer)
admin.site.register(Puzzle)
admin.site.register(PuzzleTag)
admin.site.register(PuzzlePostprod)
admin.site.register(PuzzleVisited)
admin.site.register(StatusSubscription)
admin.site.register(TestsolveSession)
admin.site.register(PuzzleComment)
admin.site.register(TestsolveParticipation)
admin.site.register(TestsolveGuess)
admin.site.register(Hint)
admin.site.register(CommentReaction)
admin.site.register(SiteSetting)
