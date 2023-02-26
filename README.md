# Puzzlord

A Django app for editing/testing puzzles for a puzzlehunt. [Puzzletron](https://github.com/mysteryhunt/puzzle-editing/) reincarnate.

Primarily maintained by [@betaveros](https://github.com/betaveros). Lots of infrastructure by [@mitchgu](https://github.com/mitchgu). Many contributions from [@jakob223](https://github.com/jakob223), [@dvorak42](https://github.com/dvorak42), and [@fortenforge](https://github.com/fortenforge).

Contains a lightly modified copy of [sorttable.js](https://kryogenix.org/code/browser/sorttable/), licensed under the X11 license.

## Design

Some goals and consequences of Puzzlord's design:

- Simplicity and low maintenance costs, with the goal of letting Puzzlord last many years without continuous development effort:
    - Few roles; Puzzlord only distinguishes superusers, meta editors, and everybody else.
    - JavaScript dependence is minimized. When useful, we use modern JS and don't try to support old browsers.
    - To reduce code, we rely on Django built-in features when possible.
    - No uploading files for puzzles or solutions. Instead, you can just paste links to external files or docs, which is what we almost always did when using Puzzletron anyway.
    - ~~No direct connection to postprodding. It is expected that postprodders will format the puzzle elsewhere and simply report what they did in Puzzlord.~~ We ended up implementing postprodding in Puzzlord, but it's probably one of the trickier parts to get working, and you can ignore it in some workflows.
- Permissiveness, which dovetails with simplicity, and is OK because we generally trust our writing team:
    - Anybody can change the status of puzzles and add/remove themselves or other people to/from any puzzle-related role (author, discussion editor, factchecker, postprodder, spoiled).
- Improved spoiler safety:
    - Puzzles can have custom codenames, which Puzzlord will try to show to non-spoiled people.
    - Unlike in Puzzletron, where clicking to a puzzle page spoils you with no warning, Puzzlord always shows you an interstitial and requires you to confirm that you would like to be spoiled. You cannot accidentally spoil yourself on puzzles or metas.
- Generally, work with GPH's workflow:
    - Factchecking comes after postprodding
    - Some additional useful puzzle statuses

Some features are still missing.

## First Time Setup with Virtualenv

- Make sure you have `pip3` (maybe `pip`) and python 3.8+.
- Get virtualenv: `pip3 install virtualenv`
- `cd` into the root of this repo
- Create a virtualenv: `virtualenv venv --python python3`.
	- This allows you to install this project's dependencies in a folder called `venv` without polluting your computer's global packages
	- If you don't have both Python 2 and Python 3 on your system, you may be able to omit the `--python python3`.
	- If this doesn't work, you may have to add to your path; try `python -m virtualenv venv` instead if you don't want to do that.
- Activate the virtualenv with `source venv/bin/activate`
	- Alternatively use `venv/bin/activate.csh` or `venv/bin/activate.fish` if you're using csh or fish
	- Use `venv\Scripts\activate` on Windows.
- Install the required packages (mainly Django): `pip3 install -r requirements.txt`
	- Are you getting `fatal error: Python.h: No such file or directory`? Try installing `python-dev` libraries first (e.g. `sudo apt-get install python-dev`).
- Create a folder for logs to go in: `mkdir logs`
- **Fix all the configuration options, secret keys and credentials:**
	- the SECRET_KEY and SITE_PASSWORD in `settings/base.py` (the SECRET_KEY should be a highly secure random string, which Django uses for hashes, CSRF tokens, and such; the SITE_PASSWORD is what you will give out to users to let them register accounts)
	- the sender and reply-to email in `puzzle_editing/messaging.py`
	- email credentials in `settings/base.py`
	- the hosts in `settings/staging.py` and `settings/prod.py`
- Make sure the database schema is up to date with `python manage.py migrate`
- Make a superuser with `python manage.py createsuperuser`
- Install pre-commit hooks `pre-commit install` (may need to `pip3 install pre-commit` first)
- Start the development server with `python manage.py runserver`
- If you get a warning (red text) about making migrations run `python manage.py migrate`

If all went well, the dev server should start, the local IP and port should be
printed to stdout, and it should helpfully tell you you're running Django
4.0.3.

Later, when you're done working on the project and want to leave the virtualenv,
run `deactivate`.

If you ever need to install more pip packages for this project, make sure you've
activated the virtualenv first. Then add the dependency to `requirements.txt`.

### Troubleshooting
 - Did you forget to source the virtualenv?
 - Did you forget to install all the requirements?
 - Are you running python 2? If `python version` starts with 2, you might need to install python 3, or to swap `python` to `python3` at the beginning of your commands.

## How to use `manage.py`

 - You can always run `python manage.py --help` to get a list of subcommands
 - To create a superuser (so you can access the `/admin` page locally) run `python manage.py createsuperuser`
 - If you get a warning (red text) about making migrations run `python manage.py migrate`

## Where are things?

The root of this repository is the Django project
Site-wide configuration lives inside the `puzzlord` directory.

The Django project (currently) has only one app, called "puzzle_editing". Most
business logic and UI lives inside the `puzzle_editing` directory.

### Static files

Static files (CSS etc.) live in `puzzle_editing/static`.
