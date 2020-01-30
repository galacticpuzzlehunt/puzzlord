# Just a fake enum and namespace to keep status-related things in. If we use a
# real Enum, Django weirdly doesn't want to display the human-readable version.

INITIAL_IDEA = "II"
IDEA_IN_DEVELOPMENT = "ID"
IDEA_IN_DEVELOPMENT_ASSIGNED = "IA"
AWAITING_ANSWER = "AA"
WRITING = "W"
WRITING_FLEXIBLE = "WF"
AWAITING_APPROVAL_FOR_TESTSOLVING = "AT"
TESTSOLVING = "T"
REVISING = "R"
NEEDS_SOLUTION = "NS"
NEEDS_POSTPROD = "NP"
NEEDS_FACTCHECK = "NF"
DONE = "D"
DEFERRED = "DF"
DEAD = "X"

# for ordering
# unclear if this was a good idea, but it does mean we can insert and reorder
# statuses without a database migration (?)
STATUSES = [INITIAL_IDEA, IDEA_IN_DEVELOPMENT, IDEA_IN_DEVELOPMENT_ASSIGNED, AWAITING_ANSWER, WRITING, WRITING_FLEXIBLE, AWAITING_APPROVAL_FOR_TESTSOLVING, TESTSOLVING, REVISING, NEEDS_SOLUTION, NEEDS_POSTPROD, NEEDS_FACTCHECK, DONE, DEFERRED, DEAD]

def get_status_rank(status):
    try:
        return STATUSES.index(status)
    except ValueError: # not worth crashing imo
        return -1

# Possible blockers:

EDITORS = "editors"
AUTHORS = "authors"
TESTSOLVERS = "testsolvers"
POSTPRODDERS = "postprodders"
FACTCHECKERS = "factcheckers"
NOBODY = "nobody"

BLOCKERS_AND_TRANSITIONS = {
    INITIAL_IDEA: (EDITORS, [
        (IDEA_IN_DEVELOPMENT, "❌ Request revision"),
        (AWAITING_ANSWER, "✅ Approve"),
        (WRITING, "✅ Approve with answer assigned"),
        (DEFERRED, "⏸️  Defer"),
    ]),
    IDEA_IN_DEVELOPMENT: (AUTHORS, [
        (INITIAL_IDEA, "📝 Request review"),
    ]),
    IDEA_IN_DEVELOPMENT_ASSIGNED: (AUTHORS, [
        (WRITING, "📝 Mark as writing"),
        (AWAITING_APPROVAL_FOR_TESTSOLVING, "📝 Request approval for testsolving"),
    ]),
    AWAITING_ANSWER: (EDITORS, [
        (WRITING, "✅ Mark as answer assigned"),
    ]),
    WRITING: (AUTHORS, [
        (AWAITING_ANSWER, "❌ Reject answer"),
        (AWAITING_APPROVAL_FOR_TESTSOLVING, "📝 Request approval for testsolving"),
    ]),
    WRITING_FLEXIBLE: (AUTHORS, [
        (WRITING, "✅ Mark as answer assigned"),
        (AWAITING_APPROVAL_FOR_TESTSOLVING, "📝 Request approval for testsolving"),
    ]),
    AWAITING_APPROVAL_FOR_TESTSOLVING: (EDITORS, [
        (TESTSOLVING, "✅ Put into testsolving"),
        (REVISING, "❌ Request puzzle revision"),
    ]),
    TESTSOLVING: (TESTSOLVERS, [
        (REVISING, "❌ Request puzzle revision"),
        (NEEDS_SOLUTION, "✅ Accept testsolve; request solution"),
        (NEEDS_POSTPROD, "⏩ Accept testsolve and solution; request postprod"),
    ]),
    REVISING: (AUTHORS, [
        (AWAITING_APPROVAL_FOR_TESTSOLVING, "📝 Request approval for testsolving"),
        (NEEDS_SOLUTION, "⏩ Mark revision as done without testsolving"),
    ]),
    NEEDS_SOLUTION: (AUTHORS, [
        (NEEDS_POSTPROD, "✅ Mark solution as finished; request postprod"),
    ]),
    NEEDS_POSTPROD: (POSTPRODDERS, [
        (NEEDS_FACTCHECK, "✅ Mark postprod as finished; request factcheck"),
    ]),
    NEEDS_FACTCHECK: (FACTCHECKERS, [
        (DONE, "✅🎆 Mark as done! 🎆✅"),
    ]),
    DEFERRED: (NOBODY, [
        (IDEA_IN_DEVELOPMENT, "✅ Return to in development"),
    ]),
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

STATUSES_BLOCKED_ON_EDITORS = [status for status, (blocker, _) in BLOCKERS_AND_TRANSITIONS.items() if blocker == EDITORS]
STATUSES_BLOCKED_ON_AUTHORS = [status for status, (blocker, _) in BLOCKERS_AND_TRANSITIONS.items() if blocker == AUTHORS]

DESCRIPTIONS = {
    INITIAL_IDEA: "Initial Idea",
    IDEA_IN_DEVELOPMENT: "Idea in Development",
    IDEA_IN_DEVELOPMENT_ASSIGNED: "Idea in Development (Answer Assigned)",
    AWAITING_ANSWER: "Awaiting Answer",
    WRITING: "Writing (Answer Assigned)",
    WRITING_FLEXIBLE: "Writing (Answer Flexible)",
    AWAITING_APPROVAL_FOR_TESTSOLVING: "Awaiting Approval for Testsolving",
    TESTSOLVING: "Testsolving",
    REVISING: "Revising",
    NEEDS_SOLUTION: "Needs Solution",
    NEEDS_POSTPROD: "Needs Post Production",
    NEEDS_FACTCHECK: "Needs Factcheck",
    DONE: "Done",
    DEFERRED: "Deferred",
    DEAD: "Dead",
}

MAX_LENGTH = 2

def get_display(status):
    return DESCRIPTIONS.get(status, status)

ALL_STATUSES = [{
    'value': status,
    'display': description,
} for status, description in DESCRIPTIONS.items()]
