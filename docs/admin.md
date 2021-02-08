# How to admin

I assume you have already created a superuser account with `python manage.py createsuperuser`. The main thing you can do as a superuser that editors and normal users can't is go to the Django `/admin/` page and edit most aspects of the data in the database freely. Wield your power wisely.

One thing that currently (early 2021) must be done from the `/admin/` page is making other users editors and/or superusers. To make a user an editor, find them under "Users" and give them the "**Can change round**" premission. (Maybe we should have a non-Django-admin UI to do this, but you have to do this so few times that it's not high priority.)

Another thing that is only accessible from `/admin/` is the creation of "status subscriptions". These are completely invisible on the main website (which is maybe something we should fix), but each status subscription sends an email to a specific user whenever *any* puzzle enters a specific puzzle status. Some ways ✈✈✈ Galactic Trendsetters ✈✈✈ has used status subscriptions:

- We had editors in chief who are in charge of assigning editors to puzzles when they need one. We gave them subscriptions to the "Awaiting Editor" status and told puzzle authors to set their puzzle to that status when they wanted an editor.
- Similarly, we had a head factchecker and a head copy editor, and we gave them subscriptions to the Needs Factcheck and Needs Copy Edits statuses so they would get an email whenever a puzzle entered those statuses.
- We had some people who really wanted to testsolve puzzles, so we gave them subscriptions to the Testsolving status so they would get an email whenever a puzzle entered testsolving.

Finally, there are a few "Site settings" that just look at the values associated with specific hardcoded keys in the codebase, so that you can change them without changing the code.
