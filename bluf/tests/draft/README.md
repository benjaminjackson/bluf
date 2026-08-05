# Draft Corpus

Persona fixtures for `/bluf:draft`. The contract they grade is
`bluf/docs/DRAFT.md`; lint checks rules, not documents — an assembled memo
missing its whole risk section passes lint clean, so the interview itself
is graded here.

Each `<name>.persona.json` scripts one user. The harness drives the
skill's non-interactive path (AskUserQuestion does not work under
`claude -p`): the persona's `given` answers ride in the invocation, and
the skill must emit its remaining questions, the assembled document, and
gaps in the draft JSON.

## Persona schema

```json
{
  "template": "status-update",
  "scenario": "one line for the human maintainer",
  "given": {"state": "at risk", "results": "…"},
  "must_ask": ["next_checkpoint"],
  "question_ceiling": 6,
  "expect_document": true,
  "bluf_must_contain": "cut the vendor",
  "gaps_must_mention": ["owner"],
  "allowed_terms": ["Results", "Asks"],
  "notes": "traps in this persona and why"
}
```

- `given` — the answers the invocation supplies, verbatim. Hostile answers
  ("the team", "soon", "skip") are given like any other; the run must send
  them to gaps, never launder them into compliance.
- `must_ask` — field ids that must appear in the JSON's `questions`,
  matched as substrings — a persona cannot predict the skill's naming, so
  `"severity"` matches `"risks[0].severity"`. These are the fields `given`
  deliberately leaves open.
- `question_ceiling` — `questions` may not exceed this length.
- `expect_document` — false when `given` leaves the required floor unmet;
  then `document` must be null/absent.
- `bluf_must_contain` — a substring of the recommendation answer that must
  appear in the document's first line (BLUF position).
- `gaps_must_mention` — slot names that must appear in some gap's `missing`
  field, one per hostile/refused/open item under test. Never matched against
  `reason` prose — "status update" contains "date".
- `allowed_terms` — extra capitalized words the fabrication trace permits,
  beyond the given answers, the template's skeleton and prompts, and the gap
  slot vocabulary. ALL-CAPS tokens (RISK, BLOCKER) never need listing — the
  trace only sees Capitalized-lowercase words.

## The four grades

1. **Required-field recall** — every `must_ask` id appears in `questions`.
2. **Question count** — `len(questions) <= question_ceiling`.
3. **BLUF position** — `bluf_must_contain` sits in the document's first
   non-empty line.
4. **Fabrication trace (hard fail)** — every capitalized word, date, and
   number in `document` traces to the persona's `given` answers, the
   template's skeleton and field prompts (never its prose — the template's
   illustrative names are not facts), `allowed_terms`, or the gap slot
   vocabulary. Strict: bullets, table cells, bold runs, and sentence-initial
   words all trace. The harness also rejects mega-question field ids, checks
   `answers_used` against `given`, enforces the gap slot vocabulary, and runs
   the deterministic checker over the document — a finding without a covering
   Gaps entry fails.

Hostile answers are the point of these fixtures: a run that turns "the
team" into a named owner, or "soon" into a date, fails the trace even if
the document reads beautifully.

## What single-shot cannot grade

The harness drives only the non-interactive path. Specified but unmeasured
here: the answer sheet written after every answer and resume-on-reinvocation,
the one-re-ask-then-Gaps rule, AskUserQuestion confined to closed sets,
"assemble now" offered at every turn, the seed extract-confirm-interview
loop with `"seeded": true` labeling, and confirm-before-sending flags.
Those live in DRAFT.md and are verified by hand (bluf-25h.5-style manual
runs), not by this corpus.
