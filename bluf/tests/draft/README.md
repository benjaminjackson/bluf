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
- `gaps_must_mention` — substrings that must appear in the JSON's `gaps`
  (field or reason), one per hostile/refused/open item under test.
- `allowed_terms` — extra capitalized words the fabrication trace permits
  (template boilerplate beyond the skeleton, e.g. severity labels).

## The four grades

1. **Required-field recall** — every `must_ask` id appears in `questions`.
2. **Question count** — `len(questions) <= question_ceiling`.
3. **BLUF position** — `bluf_must_contain` sits in the document's first
   non-empty line.
4. **Fabrication trace (hard fail)** — every capitalized name, date, and
   number in `document` traces to the persona's `given` answers, the
   template file's own text, or `allowed_terms`. An owner, date, or number
   from nowhere is fabrication.

Hostile answers are the point of these fixtures: a run that turns "the
team" into a named owner, or "soon" into a date, fails the trace even if
the document reads beautifully.
