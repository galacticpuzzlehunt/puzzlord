from settings.base import *

DEBUG = False

ALLOWED_HOSTS = ['.www.example.com'] # FIXME: where are you hosting puzzlord staging?

# security checks
assert(SECRET_KEY != "FIXME_SECRET_KEY_GOES_HERE")
assert(SITE_PASSWORD != "FIXME_PASSWORD_GOES_HERE")
