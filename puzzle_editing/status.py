# Just a fake enum and namespace to keep status-related things in. If we use a
# real Enum, Django weirdly doesn't want to display the human-readable version.

INITIAL_IDEA = "II"
AWAITING_EDITOR = "AE"
AWAITING_REVIEW = "AR"
IDEA_IN_DEVELOPMENT = "ID"
IDEA_IN_DEVELOPMENT_ASSIGNED = "IA"
AWAITING_ANSWER = "AA"
WRITING = "W"
WRITING_FLEXIBLE = "WF"
AWAITING_APPROVAL_FOR_TESTSOLVING = "AT"
TESTSOLVING = "T"
REVISING = "R"
REVISING_POST_TESTSOLVING = "RP"
AWAITING_APPROVAL_POST_TESTSOLVING = "AO"
NEEDS_SOLUTION = "NS"
AWAITING_SOLUTION_APPROVAL = "AS"
NEEDS_POSTPROD = "NP"
AWAITING_POSTPROD_APPROVAL = "AP"
NEEDS_FACTCHECK = "NF"
NEEDS_COPY_EDITS = "NC"
NEEDS_FINAL_REVISIONS = "NR"
NEEDS_HINTS = "NH"
AWAITING_HINTS_APPROVAL = "AH"
DONE = "D"
DEFERRED = "DF"
DEAD = "X"

# for ordering
# unclear if this was a good idea, but it does mean we can insert and reorder
# statuses without a database migration (?)
STATUSES = [
    INITIAL_IDEA,
    AWAITING_EDITOR,
    AWAITING_REVIEW,
    IDEA_IN_DEVELOPMENT,
    IDEA_IN_DEVELOPMENT_ASSIGNED,
    AWAITING_ANSWER,
    WRITING,
    WRITING_FLEXIBLE,
    AWAITING_APPROVAL_FOR_TESTSOLVING,
    TESTSOLVING,
    REVISING,
    REVISING_POST_TESTSOLVING,
    AWAITING_APPROVAL_POST_TESTSOLVING,
    NEEDS_SOLUTION,
    AWAITING_SOLUTION_APPROVAL,
    NEEDS_POSTPROD,
    AWAITING_POSTPROD_APPROVAL,
    NEEDS_FACTCHECK,
    NEEDS_FINAL_REVISIONS,
    NEEDS_COPY_EDITS,
    NEEDS_HINTS,
    AWAITING_HINTS_APPROVAL,
    DONE,
    DEFERRED,
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


# a partition of the statuses that excludes Done, Deferred, Dead for some queries
PRE_TESTSOLVING_STATUSES = STATUSES[: STATUSES.index(REVISING_POST_TESTSOLVING)]
POST_TESTSOLVING_STATUSES = STATUSES[
    STATUSES.index(REVISING_POST_TESTSOLVING) : STATUSES.index(DONE)
]

# Possible blockers:

EDITORS = "editors"
AUTHORS = "authors"
TESTSOLVERS = "testsolvers"
POSTPRODDERS = "postprodders"
FACTCHECKERS = "factcheckers"
NOBODY = "nobody"

BLOCKERS_AND_TRANSITIONS = {
    INITIAL_IDEA: (
        AUTHORS,
        [
            (AWAITING_EDITOR, "✅ Request editor"),
            (DEFERRED, "⏸️  Defer"),
            (DEAD, "⏹️  Mark as dead"),
        ],
    ),
    AWAITING_EDITOR: (EDITORS, [(AWAITING_REVIEW, "✅ Mark as editors assigned"),]),
    AWAITING_REVIEW: (
        EDITORS,
        [
            (IDEA_IN_DEVELOPMENT, "❌ Request revision"),
            (IDEA_IN_DEVELOPMENT_ASSIGNED, "❌ Request revision with answer"),
            (AWAITING_ANSWER, "✅ Approve"),
            (WRITING, "✅ Approve with answer assigned"),
            (TESTSOLVING, "✅ Put into testsolving"),
        ],
    ),
    IDEA_IN_DEVELOPMENT: (
        AUTHORS,
        [
            (AWAITING_REVIEW, "📝 Request review"),
            (IDEA_IN_DEVELOPMENT_ASSIGNED, "✅ Mark as answer assigned"),
            (TESTSOLVING, "✅ Put into testsolving"),
        ],
    ),
    IDEA_IN_DEVELOPMENT_ASSIGNED: (
        AUTHORS,
        [
            (WRITING, "📝 Mark as writing"),
            (AWAITING_APPROVAL_FOR_TESTSOLVING, "📝 Request approval for testsolving"),
            (TESTSOLVING, "✅ Put into testsolving"),
        ],
    ),
    AWAITING_ANSWER: (EDITORS, [(WRITING, "✅ Mark as answer assigned"),]),
    WRITING: (
        AUTHORS,
        [
            (AWAITING_ANSWER, "❌ Reject answer"),
            (AWAITING_APPROVAL_FOR_TESTSOLVING, "📝 Request approval for testsolving"),
        ],
    ),
    WRITING_FLEXIBLE: (
        AUTHORS,
        [
            (WRITING, "✅ Mark as answer assigned"),
            (AWAITING_APPROVAL_FOR_TESTSOLVING, "📝 Request approval for testsolving"),
        ],
    ),
    AWAITING_APPROVAL_FOR_TESTSOLVING: (
        EDITORS,
        [
            (TESTSOLVING, "✅ Put into testsolving"),
            (REVISING, "❌ Request puzzle revision"),
        ],
    ),
    TESTSOLVING: (
        TESTSOLVERS,
        [
            (REVISING, "❌ Request puzzle revision (needs more testsolving)"),
            (
                REVISING_POST_TESTSOLVING,
                "⭕ Request puzzle revision (done with testsolving)",
            ),
            (
                AWAITING_APPROVAL_POST_TESTSOLVING,
                "📝 Accept testsolve; request approval from editors for post-testsolving",
            ),
            (NEEDS_SOLUTION, "✅ Accept testsolve; request solution from authors"),
            (NEEDS_POSTPROD, "⏩ Accept testsolve and solution; request postprod"),
        ],
    ),
    REVISING: (
        AUTHORS,
        [
            (AWAITING_APPROVAL_FOR_TESTSOLVING, "📝 Request approval for testsolving"),
            (TESTSOLVING, "⏩ Put into testsolving"),
            (
                AWAITING_APPROVAL_POST_TESTSOLVING,
                "⏭️  Request approval to skip testsolving",
            ),
        ],
    ),
    REVISING_POST_TESTSOLVING: (
        AUTHORS,
        [
            (
                AWAITING_APPROVAL_POST_TESTSOLVING,
                "📝 Request approval for post-testsolving",
            ),
            (NEEDS_SOLUTION, "⏩ Mark revision as done"),
        ],
    ),
    AWAITING_APPROVAL_POST_TESTSOLVING: (
        EDITORS,
        [
            (
                REVISING_POST_TESTSOLVING,
                "❌ Request puzzle revision (done with testsolving)",
            ),
            (TESTSOLVING, "🔙 Return to testsolving"),
            (NEEDS_SOLUTION, "✅ Accept revision; request solution"),
            (NEEDS_POSTPROD, "⏩ Accept revision and solution; request postprod"),
        ],
    ),
    NEEDS_SOLUTION: (
        AUTHORS,
        [
            (AWAITING_SOLUTION_APPROVAL, "📝 Request approval for solution"),
            (NEEDS_POSTPROD, "✅ Mark solution as finished; request postprod"),
        ],
    ),
    AWAITING_SOLUTION_APPROVAL: (
        EDITORS,
        [
            (NEEDS_SOLUTION, "❌ Request revisions to solution"),
            (NEEDS_POSTPROD, "✅ Mark solution as finished; request postprod"),
        ],
    ),
    NEEDS_POSTPROD: (
        POSTPRODDERS,
        [
            (AWAITING_POSTPROD_APPROVAL, "📝 Request approval for postprod"),
            (NEEDS_FACTCHECK, "⏩ Mark postprod as finished; request factcheck"),
        ],
    ),
    AWAITING_POSTPROD_APPROVAL: (
        EDITORS,
        [
            (NEEDS_POSTPROD, "❌ Request revisions to postprod"),
            (NEEDS_FACTCHECK, "✅ Mark postprod as finished; request factcheck"),
        ],
    ),
    NEEDS_FACTCHECK: (
        FACTCHECKERS,
        [
            (REVISING, "❌ Request large revisions (needs more testsolving)"),
            (
                REVISING_POST_TESTSOLVING,
                "❌ Request large revisions (done with testsolving)",
            ),
            (NEEDS_FINAL_REVISIONS, "🟡 Request minor revisions"),
            (NEEDS_COPY_EDITS, "✅ Request copy edits"),
        ],
    ),
    NEEDS_FINAL_REVISIONS: (
        AUTHORS,
        [
            (NEEDS_FACTCHECK, "📝 Request factcheck (for large revisions)"),
            (NEEDS_COPY_EDITS, "✅ Request copy edits (for small revisions)"),
        ],
    ),
    NEEDS_COPY_EDITS: (FACTCHECKERS, [(NEEDS_HINTS, "✅ Request Hints"),]),
    NEEDS_HINTS: (
        AUTHORS,
        [
            (AWAITING_HINTS_APPROVAL, "📝 Request approval for hints"),
            (DONE, "⏩🎆 Mark as done! 🎆⏩"),
        ],
    ),
    AWAITING_HINTS_APPROVAL: (
        EDITORS,
        [(NEEDS_HINTS, "❌ Request revisions to hints"), (DONE, "✅🎆 Mark as done! 🎆✅"),],
    ),
    DEFERRED: (NOBODY, [(IDEA_IN_DEVELOPMENT, "✅ Return to in development"),]),
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
    INITIAL_IDEA: "Initial Idea",
    AWAITING_EDITOR: "Awaiting Editor",
    AWAITING_REVIEW: "Awaiting Review",
    IDEA_IN_DEVELOPMENT: "Idea in Development",
    IDEA_IN_DEVELOPMENT_ASSIGNED: "Idea in Development (Answer Assigned)",
    AWAITING_ANSWER: "Awaiting Answer",
    WRITING: "Writing (Answer Assigned)",
    WRITING_FLEXIBLE: "Writing (Answer Flexible)",
    AWAITING_APPROVAL_FOR_TESTSOLVING: "Awaiting Approval for Testsolving",
    TESTSOLVING: "Testsolving",
    REVISING: "Revising (Needs Testsolving)",
    REVISING_POST_TESTSOLVING: "Revising (Done with Testsolving)",
    AWAITING_APPROVAL_POST_TESTSOLVING: "Awaiting Approval (Done with Testsolving)",
    NEEDS_SOLUTION: "Needs Solution",
    AWAITING_SOLUTION_APPROVAL: "Awaiting Solution Approval",
    NEEDS_POSTPROD: "Needs Post Production",
    AWAITING_POSTPROD_APPROVAL: "Awaiting Postprod Approval",
    NEEDS_FACTCHECK: "Needs Factcheck",
    NEEDS_FINAL_REVISIONS: "Needs Final Revisions",
    NEEDS_COPY_EDITS: "Needs Copy Edits",
    NEEDS_HINTS: "Needs Hints",
    AWAITING_HINTS_APPROVAL: "Awaiting Hints Approval",
    DONE: "Done",
    DEFERRED: "Deferred",
    DEAD: "Dead",
}

MAX_LENGTH = 2


def get_display(status):
    return DESCRIPTIONS.get(status, status)


ALL_STATUSES = [
    {"value": status, "display": description,}
    for status, description in DESCRIPTIONS.items()
]
