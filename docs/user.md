# How to Use Puzzlord

This page tries to give a broad overview of Puzzlord and all the features accessible by every user, which is most of them.

There are a few permission-gated features and pages for [editors](editor.md) and [admins/superusers](admin.md) covered separately, but editors and admins should read this guide first too.

Also, while Puzzlord encourages a workflow similar to the one we developed for GPH, it doesn't enforce it and also leaves many details unspecified, so you may wish to create your own guide for your puzzle-writing team based on this.

(Specific note: If you're coming from Puzzletron, we at GPH have put factchecking after postprodding in our workflow.)

## Overview

Puzzlord helps guide puzzles through the full puzzle production process: writing, revising, testsolving, post-production, copy-editing, and so on. The main way this is tracked is the "puzzle status". Each puzzle has a status; Puzzlord has a long list of the available statuses (in `status.py`), and of the encouraged transitions between statuses, which are more easily accessible than other transitions.

However, note that most puzzle statuses don't have much inherent meaning to Puzzlord. Puzzlord doesn't place any hard restrictions on which status changes can actually happen or on who can change statuses. So usually, if you find that a status doesn't make sense to you or doesn't fit in your workflow, you can skip it or repurpose it as desired.

The most visible feature that all puzzle statuses have is that each status is *blocked* on a group. The majority of statuses are either blocked on the authors or on the editors of the puzzle; a few statuses are blocked on testsolvers, postprodders, factcheckers, and "nobody". All this means is that the puzzle will be shown more prominently to that group of people or on a page of the website meant for them. The hope is that, for each puzzle, the status will always unambiguously specify whose responsibility it is to take the next steps, to try to avoid situations where people are waiting on each other. However, this does not prevent any other group of people from taking action on the puzzle.

The "Testsolving", "Needs Postprod", "Needs Factcheck", and "Needs Copy Edits" statuses make the puzzles visible in particular pages linked from the top bar. In particular, the "Testsolving" status makes the puzzle visible in the Testsolving tab and allows testsolvers to create testsolving sessions. This is covered in more detail later. Testsolving is unusual because it's the only Puzzlord activity you do on a puzzle where you must be unspoiled and must avoid the main puzzle page.

A few more statuses are often handled specially in other ways. Puzzles that are "Dead" or "Deferred" are hidden from most puzzle lists by default, and they're also either omitted or treated separately in most statistics. You can still view them in lists by unchecking "Hide dead puzzles" and "Hide deferred puzzles". Puzzles in "Initial Idea" are also sometimes omitted or separated out, since in our experience people often submit hundreds more half-baked puzzle ideas than they can work on or than can go into the hunt, and many of those ideas stay in "Initial Idea" forever.

## Creating an Account

Click "Register" to make an account. The fields are mostly self-explanatory. You will need a "Site password", which somebody setting up the server should have configured (if you are configuring the site, it's specified in `settings.py`). There are some specific references to Discord just because GPH has organized all our puzzlehunt writing on Discord and we want to be able to match accounts on Puzzlord and Discord, but Puzzlord doesn't actually integrate with Discord other than display the username; you might want to change these fields, or ask your admin to do so.

## Authoring a Puzzle

To submit a puzzle idea, click "New puzzle" and follow instructions. "Notes" are optional and won't be shown to unspoiled people; use them as you wish.

Puzzlord does not dictate the exact workflow after that, but you and other people can leave comments on the puzzle, edit the puzzle and solution, and change the puzzle status.

If your workflow is like ours, the next step is to change the status to "Awaiting Editor", at which point somebody else will assign an editor or editors to your puzzle. (Note: An admin can set up a "status subscription" to notify an editor in chief when any puzzle enters this status; see the [admin docs](admin.md).) You can then discuss the puzzle idea with editors, and either of you might change the puzzle status a few times. Eventually, they should assign an answer to allow you to write the puzzle. The biggest qualitative change comes when the puzzle enters the Testsolving status.

## Testsolving

Testsolving occurs, of course, on the Testsolve page linked from the top bar. Testsolving is organized into "testsolving sessions" (a concept that doesn't exist in Puzzletron). A testsolving session represents one attempt by a person or a group of people to solve a particular puzzle.

To start a testsolving session on a puzzle, go to the Testsolving page and click "Start new session" next to a puzzle under "Puzzles you can testsolve". This includes all puzzles in the Testsolving status, although puzzles you are an author on are hidden by default and puzzles you are spoiled on or that have an ongoing session display a warning. Puzzlord allows you to testsolve puzzles you're marked as spoiled on in cases where, say, you spoiled yourself on the puzzle early in its lifecycle and then paid little enough attention to it that you can still give a useful testsolve. You're also technically allowed to testsolve puzzles you're an author on just to keep the logic simple and permissive, but you should rarely want to do that.

Alternatively, you can join an ongoing session in the "Testsolving sessions you can join" section. Whether a session is "joinable" is a switch that participants in the session can flip. Note that "joinable" really means something like "publicly advertised as joinable" and just controls whether a session will be in this section. The idea is that the flag can be used to indicate whether a session is looking for new participants, and be turned off after the testsolve group has gotten big enough or made enough progress that a separate testsolve would be deemed more useful. However, anybody can join a testsolving session if they have or guess the URL to the session itself and click the Join button. So, if you already have a group of people you want to testsolve a puzzle with, you can create a session and send them the link, and they will be able to join without touching this switch.

Sessions you are part of and haven't finished are linked in the top "Testsolving sessions you are in" section. On a testsolve session's page, you can leave comments, which will be visible to other participants viewing the session as well as to the puzzle author or anybody else viewing the spoilery puzzle page itself. You can use this comment box to link to your solving sheet and provide freeform progress updates and feedback; authors and editors can also reply.

When you are done with the testsolve (either because you've solved the puzzle or because you've given up), click "Done with the puzzle?" to be taken to a page where you can leave more detailed feedback. (This link will be greatly emphasized after you have submitted a correct answer.) Submitting this form will mark your participation in the session as done. Note that there is no concept of a session finishing, only of individual participants finishing their participation in the session, because we want every participant to fill out feedback. You can select if you want to spoil yourself on the puzzle or leave the testsolving session altogether; the implications are explained on this page.

Also note that you can fill out this form multiple times after you've finished; the fun/difficulty/hours spent ratings from your most recent submission will be taken. (This isn't great UI/UX and I should figure out how to fix it.)

As an author or editor on a puzzle, basically you should just look at the incoming testsolves and decide when you want to take the puzzle out of the testsolving status.

## Postprodding

Puzzlord allows you to upload a zip file and automatically push it to a Git repository, if you set that up. I'm not sure how it works, sorry.

## Hint-Writing

Hints were a fairly late addition to Puzzlord in 2021. The numbers and keywords don't have any inherent meaning in Puzzlord; the intent is for them to be exported into other systems.

## Tags

Tags are useful for, well, tagging puzzles. You can assign tags to puzzles and then view a list of all puzzles with a particular tag.

Some ways tags can be useful:

- Tag metapuzzles.
- Tag puzzles in unusual rounds or with unusual gimmicks.
- Tag puzzles in a particular genre (e.g. cryptic crosswords, logic puzzles) or about a subject (e.g. math, video games), to ensure you don't have too few or too many of them and try to spread them out among rounds.
- Tag puzzles that need or are looking for authors or editors with particular skill sets (e.g. audio/video editing, foreign language fluency).
- Tag puzzles that need special attention later (e.g. they depend on current events and need to be re-factchecked, or they rely on external resources that need to be rehosted).
- Tag backup puzzles or puzzles that can take any answer.

A tag can be "important", which means that the tag will be visible next to the puzzle title in most places.

## Users, Statistics, etc.

These are hopefully self-explanatory?
