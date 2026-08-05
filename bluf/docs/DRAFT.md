# Draft Interview Protocol

This document is the contract for `/bluf:draft`: the interview mechanics
every template shares, the answer-sheet format, the degradation path, and
the JSON the grading harness consumes. Template definitions (which fields,
which order, which skeleton) live beside the skill and build on this.

The premise: the skill asks the questions the standard requires answered —
state? owner? date? denominator? — then assembles the compliant document.
The interview is the product; the document is its receipt.

## Question mechanics

- **Facts are free text.** Owners, dates, numbers, recommendations arrive
  as typed answers to plain questions. The skill never proposes candidate
  owners, dates, or numbers — a menu of invented owners the user picks from
  is fabrication with extra steps.
- **The field table is the whole interview.** Every question comes from
  the template's field table. Skeleton slots that are not fields — the
  title, a scope heading, the author line — are derived from answers
  already given, or filled with a neutral generic ("Status Update").
  Never asked. Derived means **reusing words the answers contain**: a
  title may not introduce a noun no answer used — that is fabrication in
  a heading.
- **AskUserQuestion only for genuinely closed sets**: template choice,
  document state (on track / at risk / off track), RISK vs BLOCKER, and the
  fact / estimate / opinion tag. Nothing else.
- **Question order is not document order.** Facts come first; the
  one-sentence recommendation is asked **last** and placed **first** — a
  writer usually cannot state the BLUF until walked through the facts.
- **Tags are asked, not assumed.** Every interpretive claim gets its
  fact / estimate / opinion tag from the user.
- **One re-ask, then Gaps.** A hostile or refusing answer — "the team",
  "soon", "significant improvement", "skip" — gets at most one clarifying
  re-ask ("A named person, or should I list the owner in Gaps?"). After
  that the answer is recorded verbatim in the sheet and the field goes to
  Gaps. Refusal never becomes fabricated compliance.

## Field tiers

Each template defines two tiers:

- **Required** — the floor. Below it no document is assembled; assemble-now
  produces the answer sheet and the open questions instead.
- **Optional** — skippable straight to Gaps at any time.

A **refused** required field counts toward the floor: the user addressed
it, the document assembles, and the hole rides in Gaps — that is the
honest artifact this whole mode exists for. Only never-addressed required
fields block assembly.

## The answer sheet

Answers persist to `bluf-draft-<template>.json` in the working directory,
written after **every** answer — a twelve-question flow must survive
compaction, `/clear`, and a meeting at question eight.

```json
{
  "version": 1,
  "template": "status-update",
  "answers": {
    "state": {"answer": "at risk", "tag": null},
    "owner_main": {"answer": "the team", "refused": true},
    "recommendation": {"answer": null}
  }
}
```

- A field the user refused keeps the verbatim refusal and `"refused": true`.
- An unasked field is absent; an asked-but-unanswered field is `null`.
- On re-invocation the skill loads the sheet, shows a one-line summary of
  what it already has, and resumes at the first open required field.

## Assemble-now

"Assemble now with what I have" is offered at every turn. When the
required floor is met, assembly runs immediately: answered fields fill the
skeleton, every open or refused field becomes a Gaps entry. Below the
floor, the skill says which required fields are open and writes no
document.

## Assembly rules

- Every named person, date, and number in the document comes from an
  answer. Nothing else is a source. This is the fabrication trace the
  harness checks.
- When a named owner is not the document's author, the assembled item
  carries a confirm flag: "(confirm with Priya before sending)".
- Open fields render as Gaps entries in the document's Gaps section, per
  the marked-unknown convention in FINDINGS.md — the assembled document is
  graded by gaps-aware lint, so the honest document passes.

## Seed input

Nobody drafts from nothing. When the invocation carries material — notes,
last week's update, a pasted thread — the interview starts from it:

1. **Extract** what the seed already answers, field by field. Seeded facts
   follow the triage provenance rule: never upgraded beyond what the
   source states. Notes saying "checkout is faster" seed no number; notes
   saying "ship next week" seed no date.
2. **Confirm before use.** Show the extraction as a filled answer sheet —
   "here is what your notes already answer" — and let the user correct it.
   In non-interactive mode the extraction is used as-is but labeled seeded
   in the sheet (`"seeded": true`), so the trace stays honest.
3. **Interview only the gaps.** Questions cover the fields the seed left
   open, nothing already confirmed.

A seeded answer counts toward the required floor only after confirmation
(or immediately, in non-interactive mode).

## Non-interactive mode

`claude -p` and agent callers cannot answer AskUserQuestion. When the
invocation itself supplies answers — inline after the command, or as a
file path — the skill runs single-shot:

1. Parse the supplied answers into the sheet. Single-shot **ignores
   any existing sheet file** — the invocation's answers are the whole
   interview; resume is an interactive-mode feature only.
2. **Refusals go straight to Gaps.** The one re-ask is an interactive
   courtesy; single-shot has no turns. A hostile answer ("the team",
   "soon") or a declared unknown ("no owner yet", "cost unknown") becomes
   a Gaps entry, never a question — a question AND a gap double-counts
   the same hole.
3. Emit questions for the **never-answered** fields only, and only fields
   from the template's field table. Skeleton slots outside the table
   (title, scope headings, the author) are derived from the answers or a
   neutral generic — never asked, in any mode.
4. Assemble if the required floor is met; otherwise say what is missing.
5. Gaps as always.

The grading harness drives this path.

## Draft JSON

On request ("emit draft JSON") the skill appends one fenced json block,
last in the response:

```json
{
  "version": 1,
  "template": "status-update",
  "questions": [
    {"field": "denominator_churn", "prompt": "Out of how many accounts?"}
  ],
  "answers_used": {"state": "at risk", "owner_main": "Priya"},
  "document": "…the assembled markdown, or null below the floor…",
  "gaps": [
    {"field": "asks", "missing": "owner, date",
     "reason": "refused: 'the team should pick this up soon'"}
  ],
  "confirm_flags": ["Priya"]
}
```

`questions` lists open fields only, one field per entry — a field id
packing several slots ("severity, trigger") is rejected. Each gap names
its absent slot(s) in `missing`, from the closed vocabulary — owner, date,
decider, decision, value, baseline, denominator, plus draft's own `tag`
(a refused fact/estimate/opinion tag is a real hole) — so a grader never
depends on how the `reason` is worded. `answers_used`
holds exactly the answers that reached the document; the harness checks
every entry against the answers actually given, and traces every name,
date, and number in `document` back to those given answers. Anything
untraceable is fabrication, a hard fail.
