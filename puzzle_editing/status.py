# Just a fake enum and namespace to keep status-related things in. If we use a
# real Enum, Django weirdly doesn't want to display the human-readable version.

CONCEPT = "C"
WRITING = "W"
TESTSOLVING = "T"
REVISION = "R"
FACTCHECK = "F"
POSTPROD = "P"
DONE = "D"
DEAD = "X"

# for ordering
# unclear if this was a good idea, but it does mean we can insert and reorder
# statuses without a database migration (?)
STATUSES = [
    CONCEPT,
    WRITING,
    TESTSOLVING,
    REVISION,
    FACTCHECK,
    POSTPROD,
    DONE,
    DEAD,
]


def get_status_rank(status):
    try:
        return STATUSES.index(status)
    except ValueError:  # not worth crashing imo
        return -1


def past_writing(status):
    return get_status_rank(status) > get_status_rank(
        WRITING_FLEXIBLE
    ) and get_status_rank(status) <= get_status_rank(DONE)


def past_testsolving(status):
    return get_status_rank(status) > get_status_rank(REVISING) and get_status_rank(
        status
    ) <= get_status_rank(DONE)


# Possible blockers:

EDITORS = "editors"
AUTHORS = "authors"
TESTSOLVERS = "testsolvers"
POSTPRODDERS = "postprodders"
FACTCHECKERS = "factcheckers"
NOBODY = "nobody"

BLOCKERS_AND_TRANSITIONS = {

    CONCEPT: (
        AUTHORS,
        [
            (WRITING, "📝 Start writing puzzle"),
            (DEAD, "🗑 Mark as dead"),
        ],
    ),
    WRITING: (
		EDITORS,
		[
			(TESTSOLVING, "📥 Open puzzle to testsolving"),
			(DEAD, "🗑 Mark as dead"),
		]
	),
    TESTSOLVING: (
        EDITORS,
        [
            (REVISION, "🛠 Request puzzle revision"),
            (FACTCHECK, "🔍 Accept testsolving; flag puzzle for fact-check"),
        ],
    ),
    REVISION: (
        AUTHORS,
        [
            (TESTSOLVING, "📥 Put puzzle back into testsolving"),
        ],
    ),
    FACTCHECK: (
        AUTHORS,
        [
            (POSTPROD, "💻 Accept fact-check; flag puzzle for post-prod"),
			(REVISION, "🛠 Request puzzle revision;"),
        ],
    ),
    POSTPROD: ( 
		EDITORS,
		[
			(DONE, "🎉 Mark puzzle as complete 🎉"),
		]
	),
}


def get_blocker(status):
    value = BLOCKERS_AND_TRANSITIONS.get(status)
    if value:
        return value[0]
    else:
        return NOBODY


def get_transitions(status):
    value = BLOCKERS_AND_TRANSITIONS.get(status)
    if value:
        return value[1]
    else:
        return []


STATUSES_BLOCKED_ON_EDITORS = [
    status
    for status, (blocker, _) in BLOCKERS_AND_TRANSITIONS.items()
    if blocker == EDITORS
]
STATUSES_BLOCKED_ON_AUTHORS = [
    status
    for status, (blocker, _) in BLOCKERS_AND_TRANSITIONS.items()
    if blocker == AUTHORS
]

DESCRIPTIONS = {
	CONCEPT: "Initial puzzle concept",
    WRITING: "Writing puzzle",
    TESTSOLVING: "Testsolving",
    REVISION: "Revising puzzle",
    FACTCHECK: "Factchecking puzzle",
    POSTPROD: "Postproducing puzzle",
    DONE: "Done",
    DEAD: "Dead",
}

MAX_LENGTH = 2


def get_display(status):
    return DESCRIPTIONS.get(status, status)


ALL_STATUSES = [
    {"value": status, "display": description,}
    for status, description in DESCRIPTIONS.items()
]
