---
name: triage
description: Extract the actual state of the world from a document or email thread the user received — decisions, owners, dates, numbers, risks — then name what is evasively missing. Use when the user runs /bluf:triage, pastes a status update or thread they got from someone else, or asks "what does this actually say" or "what's missing here".
---

# /bluf:triage

Triage a document the user *received*. Extract what it establishes, then name
what it leaves out. The sender never sees this output and never has to change
anything — triage asks nothing of them.

Triage is not lint. **Never cite SEE-100 rule numbers** — not in prose, not
in JSON. "Three of the five commitments name no owner" is the register;
"Rule 5.4: no owner" is a failure.

## Procedure

1. Read `${CLAUDE_PLUGIN_ROOT}/docs/TRIAGE.md` — the output contract. It
   wins over this file wherever they differ.
2. Classify the input: single document, or a pasted email thread. A thread
   is anything with message headers, reply prefixes (`>` quote levels), or
   forwarded sections.
3. For a thread, segment before extracting:
   - Split per message. Attribute every statement to its speaker, including
     statements inside quote levels — a quoted line belongs to its original
     author, not the person quoting it.
   - The newest statement by the same speaker on the same subject wins;
     older ones feed the contradiction report.
   - Discard signature blocks, bottom-quoted history that merely repeats
     messages already seen above, and HTML artifacts. They are noise, not
     facts.
4. Extract facts of exactly five types: decisions (decider + date),
   commitments (owner + date), numbers (value + baseline), risks, claimed
   states. Everything else is skipped and counted.
   - Every field value keeps the document's written form: "ten" stays
     "ten", never 10. Omit a field you cannot support — never emit null.
   - A promise of future work with no owner ("A rollback plan will be
     written") is still a **commitment** — no owner field, and an owner
     gap. Do not soften it to a claimed state.
   - `baseline` only when the document states a prior value. The current
     value is never its own baseline.
5. Provenance for every fact: the verbatim `quote`, labeled `stated` or
   `inferred` (with the inference spelled out). The banned inferences —
   owner from the From: line or signature, date from surrounding context,
   decision from a discussion of a decision — are fabrication. When in
   doubt, the fact is a gap instead.
6. Relative dates ("by Friday") resolve only against an explicit anchor in
   the document: a send date, dateline, or dated message header. Today's
   date is never an anchor. No anchor → the date surfaces as unresolved,
   with the reason.
7. Compare across messages: same subject, different dates, numbers, or
   owners → a dated, attributed contradiction entry. This is the report no
   single-document pass can make; do not bury it in prose.
8. Rank gaps by consequence, measured in what the document itself states —
   money, deadlines, named accounts. An undecided item carrying a dollar
   amount and a deadline outranks everything that carries neither; a
   missing owner on a dated commitment outranks a missing denominator in
   an aside. Never let an appendix statistic push a funded, dated gap out
   of the top five. Then write the questions: a
   short block of neutral questions the user can paste into a reply without
   editing. Describe the document, never indict the sender: "the date for
   the migration is not stated", never "Dana dodged the date".

## Output, in order

1. **Lead line** — one plain sentence stating what the document establishes.
2. **Extraction** — grouped per commitment or per person, never per
   sentence. At most the 12 most consequential facts.
3. **Contradictions** (threads only) — dated and attributed.
4. **Gaps** — at most 5, ranked.
5. **Questions** — at most 5, paste-able verbatim.
6. **Skipped** — one line naming what the caps dropped.

The output must be shorter than the input.

Degenerate cases:

- Zero extractable facts: the lead line is the product — "This update
  states no decision, names no owner, and gives no date." Then the gaps.
  Never an empty template.
- Fully compliant document: "Everything needed is stated" is the correct,
  complete answer. Inventing gaps for a clean document is as wrong as
  inventing facts.

If the request contains "emit triage JSON", append one fenced `json` block
in the TRIAGE.md schema. No prose inside the block.

## Failure behavior

If `${CLAUDE_PLUGIN_ROOT}/docs/TRIAGE.md` cannot be read: stop and report
the exact path that failed. Never triage from memory of the contract.
