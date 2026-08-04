# Triage Output Contract

This document is the contract between `/bluf:triage` and its grading harness.
Triage describes documents the user *received*. It extracts the actual state
of the world, then names what is missing. It never lints: the sender never
sees it, so citing rules at them is noise. **No SEE-100 rule numbers appear
anywhere in triage output — not in prose, not in JSON.**

The harness grades JSON only. It never parses rendered prose.

## Shape: extraction first, gaps second

The failure mode this contract exists to prevent: triage shipping as lint
with the headers renamed. The negative example: "Rule 5.4: no owner" is a
failure. The target: "Three of the five commitments name no owner; the two
that do are both Dana."

Rendered output, in order:

1. **Lead line.** One plain sentence stating what the document establishes.
   For a document with zero extractable facts, this line IS the product:
   "This update states no decision, names no owner, and gives no date."
2. **Extraction.** Facts grouped per commitment or per person — never per
   sentence, never in document order for its own sake.
3. **Contradictions** (threads only). Cross-message conflicts, dated and
   attributed: "On Jul 2 Dana wrote Aug 15. On Jul 20 Dana wrote 'early
   September.'"
4. **Gaps.** Ranked by consequence, capped (see budget).
5. **Questions.** A short block of neutral questions the user can paste into
   a reply verbatim.
6. **Skipped.** One line naming what the output budget dropped.

## Fact types

Extraction scope is closed: **decisions** (with decider and date),
**commitments** (with owner and date), **numbers** (with baseline),
**risks**, and **claimed states**. Everything else is out of scope — dropped,
and named in `skipped` so the omission is visible.

## Provenance

Every fact carries the verbatim quote it came from and a provenance label:

- `stated` — the document says it.
- `inferred` — the document implies it; the `inference` field shows the
  reasoning in one sentence. A fact with any inferred component is labeled
  `inferred`, and the inference names which component.

Absent facts are not facts — they are gaps.

**Banned inferences**, by name. Each of these is fabrication, not inference:

- An owner from the `From:` line or signature of an **ownerless** statement.
  "A rollback plan will be written", sent by Dana, has no owner — crediting
  Dana is fabrication. Resolving an explicit first person ("I'll send X",
  written by Marco) to the speaker is not inference; the document names its
  owner and the fact stays `stated`.
- A date from surrounding context ("the thread is about Q3, so ~September").
- A decision from a discussion of a decision. Talking about deciding is a
  claimed state at most.

One invented owner in a forwarded document destroys the tool permanently.
When in doubt, the fact is a gap.

## Relative dates

"By Friday" and "end of next week" resolve only against an explicit anchor
in the document itself — a send date, a dateline, a dated message header.
No anchor: the date surfaces unresolved, with the reason: "'Friday' — the
document carries no send date, so this cannot be resolved." Today's date is
never an anchor; the document may be months old.

A fact whose only date is an unresolved relative phrase keeps that phrase
verbatim in its `date` field ("Friday") — the document does state it — and
the phrase also appears in `unresolved_dates`. What the fact may never carry
is a calendar date the document does not support.

## Tone

Triage describes the document, never indicts the sender. "The date for the
migration is not stated," never "Dana dodged the date." Gaps and questions
are worded so the user can forward them without editing the accusation out.

## Output budget

Output length does not scale with input length:

- Facts: the 12 most consequential. Beyond that, count the rest in `skipped`.
- Gaps: 5, ranked. A missing owner on a dated commitment outranks a missing
  denominator in an aside.
- Questions: 5.
- The rendered output must be shorter than the input.

Whatever the caps drop is named: "Skipped: 14 routine status lines, 2
numbers in the appendix."

## Degenerate cases

- **Zero extractable facts** (pure hedge): lead with the plain-words verdict,
  then the gaps. Never an empty template.
- **Fully compliant document**: "Everything needed is stated" is a correct,
  complete answer. Inventing gaps for a clean document is a graded failure,
  symmetric with fabricating facts.

## Triage JSON

On request ("emit triage JSON") the skill appends one fenced json block:

```json
{
  "version": 1,
  "verdict": "Two commitments, one dated; the decision is claimed but has no decider.",
  "facts": [
    {
      "type": "commitment",
      "statement": "Dana moves the two remaining services by Sep 5",
      "owner": "Dana",
      "date": "Sep 5",
      "quote": "I'll move the last two services over by Sep 5",
      "provenance": "stated",
      "speaker": "Dana",
      "message_date": "Jul 20"
    }
  ],
  "contradictions": [
    {
      "about": "migration date",
      "quotes": ["done by Aug 15", "realistically early September"],
      "speakers": ["Dana", "Dana"],
      "message_dates": ["Jul 2", "Jul 20"]
    }
  ],
  "unresolved_dates": [
    {"quote": "by Friday", "reason": "no send date in the document"}
  ],
  "gaps": [
    {"rank": 1, "missing": "owner", "about": "the rollback plan",
     "quote": "a rollback plan is being drafted"}
  ],
  "questions": ["Who owns the rollback plan, and by what date is it done?"],
  "skipped": "3 paragraphs of background on the vendor evaluation"
}
```

Field rules:

- `type` — `decision`, `commitment`, `number`, `risk`, or `claimed_state`.
- `statement` — the fact in triage's words, one sentence. For rendering;
  the harness does not grade it.
- `quote` — verbatim from the document; the location mechanism, exactly as
  in the findings contract. Required on every fact and every span gap.
- `provenance` — `stated` or `inferred`; `inferred` requires `inference`.
- `owner` / `date` / `decider` / `value` / `baseline` — present only when the
  document supports them. A missing slot on an extracted fact is expressed
  as a gap, not as `null` — omit the key entirely.
- Field values keep the document's own written form: "ten" stays "ten",
  never `10`; "four" never becomes `4`. Normalizing a value is rewriting
  the document, and the harness grades it as fabrication.
- `baseline` only when the document states a prior value. Restating the
  current value as its own baseline ("four, the current level") invents a
  comparison the document never made.
- `speaker` / `message_date` — required when the input is a thread; omitted
  for single documents.
- `verdict` — the lead line, as one string. The rendered lead line and this
  field say the same thing.
- `gaps[].missing` — the absent slot, named with one of: `owner`, `date`,
  `decider`, `decision`, `value`, `baseline`, `denominator`.
- `gaps[].about` — a short noun phrase naming the thing the slot is missing
  from ("the rollback plan"), plus a `quote` when a span exists.
- `gaps[].rank` — 1 is most consequential; ranks are unique.
- Grading (see the corpus README): recall is scored against a hand-written
  gold fact list; any asserted fact absent from the gold list is fabrication
  and a hard fail. A gap claiming something is missing that the document
  states ("no date appears" when one does) counts as fabrication too.
