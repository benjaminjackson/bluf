# Template: postmortem

Linear interview with a stated position on blame, taken in writing:

- **Decisions and actions name their actors.** "Maria approved the config
  change" — the standard requires named subjects and a postmortem is made
  of decisions and actions.
- **Causes name systems, not people.** "The deploy pipeline had no canary
  stage", never "Marco broke production". A person appears in a cause only
  as the actor of a decision the cause chain runs through.
- **A person is required only on remediation items.** Every remediation
  has one owner and one date. Nothing else in the document requires
  assigning a person to a failure.

Interviewers using this template do not ask "who broke it". They ask what
happened, which decisions were made and by whom, and what the system
allowed.

## Fields

| id | tier | type | prompt |
|---|---|---|---|
| incident | required | free | One sentence: what happened, when did it start, when did it end (real dates and times)? |
| impact | required | free | Who and what was affected, as numbers with denominators — of how many users, requests, dollars? |
| timeline | optional | free | The key events in order, each with a time and, for actions, the actor. |
| decisions | required | free | Which decisions shaped this incident — before and during? For each: the decision, the named decider, the date. |
| causes | required | free | What allowed this to happen? Name systems and their properties, not people. |
| remediation | required | free | What changes, who owns each item (one name), and by what date? |
| tag | required | closed: fact / estimate / opinion | For each interpretive claim: which tag? |
| recommendation | required | free | One sentence: the single most important thing this incident should change. Opens the document. |

## Skeleton

```
# Postmortem: {incident title}

{recommendation}

## What happened

{incident} {impact}

## Timeline

{timeline — or omit the section}

## Decisions

{decision, named decider, date — one per line}

## Causes

{system-named causes}

## Remediation

{item, one owner, one date — each line}

## Gaps

{marked-unknown convention — omit only when empty}
```
