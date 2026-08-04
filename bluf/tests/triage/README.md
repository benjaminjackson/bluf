# Triage Corpus

Fixtures for `/bluf:triage`. The contract they grade is `bluf/docs/TRIAGE.md`.

Each `<name>.md` fixture has a hand-written `<name>.gold.json` beside it. The
suffix is `.gold.json`, not the lint corpus's `.expected.json`, because the
schema and the harness are different: the lint corpus grades findings by rule
number and span, this one grades extracted facts by field and quote.

The harness grades the skill's JSON block only. It never parses rendered prose.
Run each fixture 3 times, as with the lint corpus; disagreement between runs on
any `must_` assertion is a failure.

## The fixtures

| Fixture | What it grades |
| --- | --- |
| `thread-contradictions.md` | Cross-message contradictions, newest-wins, banned owner inference |
| `no-anchor-dates.md` | Relative dates with no anchor anywhere in the document |
| `pure-hedge.md` | Zero extractable facts: the verdict line is the whole product |
| `evasive-update.md` | Numbers without baselines, a decision never made, an ownerless risk |
| `compliant-memo.md` | A clean document: gaps must come back empty |
| `long-report.md` | Output budget: 629 words and more legitimate facts than slots |

Every fixture is synthetic. Bare first names only, no surnames, no real
companies, no real products, and the only email addresses are `@acme.example`.

## Gold file schema

```json
{
  "is_thread": false,
  "facts": [
    {"type": "commitment", "owner": "Dana", "date": "Sep 5",
     "quote_contains": "by Sep 5", "provenance": "stated"}
  ],
  "allowed_facts": [],
  "must_not_extract": [],
  "contradictions_must_include": [],
  "unresolved_must_include": [],
  "no_resolved_dates": false,
  "gaps_must_include": [],
  "gaps_must_not_include": [],
  "gaps_must_be_empty": false,
  "skipped_must_be_nonempty": false,
  "verdict_regex": null,
  "notes": "free text for the human maintainer: the traps in this fixture and why"
}
```

`why` may appear on any entry anywhere. It is a note to the next human. The
harness ignores it.

### Fact entries

`facts`, `allowed_facts` and `must_not_extract` all hold entries of the same
shape:

- `type` — `decision`, `commitment`, `number`, `risk`, or `claimed_state`, or
  `*` for any type.
- `quote_contains` — a substring that must appear in the skill fact's `quote`.
  `*` matches any quote.
- scalar fields — `owner`, `date`, `decider`, `value`, `baseline`, `speaker`,
  `message_date`, `provenance`. Present only when the gold asserts them.
- `must_not_have` — a list of field names that must be **absent** from the
  matching skill fact. This is how a banned-inference trap is expressed: the
  document states a commitment with no owner, so the skill fact must carry no
  owner.

### Matching a skill fact to a gold entry

A skill fact **matches** a gold entry when all of these hold:

1. `type` is equal, or the gold type is `*`.
2. Every scalar field present in the gold entry appears in the skill fact,
   compared case-insensitively as a **substring** of the skill's value. Gold
   `"value": "2.1"` matches a skill `"value": "2.1%"`. Gold
   `"message_date": "Jul 20"` matches `"Mon, Jul 20"`.
3. The gold `quote_contains` string appears in the skill fact's `quote`, again
   case-insensitively, unless it is `*`.
4. No field named in the gold's `must_not_have` is present in the skill fact.

Type equality in step 1 is load-bearing. A gold entry typed `claimed_state`
does not license a skill fact typed `decision` over the same sentence, which is
how the "discussion of a decision is not a decision" trap is caught.

### The three verdicts

**Recall.** Every entry in `facts` must be matched by at least one skill fact.
A missed entry is a recall failure.

**Fabrication (hard fail).** Any skill fact that matches nothing in `facts` +
`allowed_facts` is a fabrication, judged two ways:

- its `quote` does not appear verbatim in the document; or
- its stated `owner` / `date` / `decider` / `value` / `baseline` is not
  supported by the **sentence containing the quote**. Judge against the
  sentence, not the quote alone — a quote is a location mechanism and a skill
  may legitimately quote a clause of a longer sentence. It is not a licence to
  reach into a neighbouring sentence for an owner.

Anything listed in `must_not_extract` is a fabrication even if its quote is
real. That list exists for facts whose quote is genuine but whose *type* is
invented, which quote-checking alone cannot catch.

**False gap (hard fail, same weight as fabrication).** A `gaps` entry claiming
something is absent that the document states. `gaps_must_not_include` enumerates
the specific ones each fixture baits. A false gap is fabrication in the other
direction, and `compliant-memo.md` exists to catch it: inventing gaps for a
clean document is a graded failure, symmetric with inventing facts.

### The other assertions

- `contradictions_must_include` — each entry has `about_contains` and
  `quotes_contain`. `about_contains` is matched against the contradiction's
  `about` field **concatenated with its quotes**, so it passes however the run
  words the summary, as long as it found the right conflict. Every string in
  `quotes_contain` must appear somewhere in the concatenated `quotes` array.
- `unresolved_must_include` — each string must appear in the `quote` of some
  `unresolved_dates` entry.
- `no_resolved_dates` — when true, no calendar date (month name, ISO date, or
  numeric date) may appear anywhere in the output. The document carries no
  anchor, so any calendar date is fabricated. Today's date is never an anchor.
- `gaps_must_include` / `gaps_must_not_include` — each entry has an optional
  `missing` and an optional `about_contains`. `missing` is matched as a
  case-insensitive substring of the skill gap's `missing` field, so gold uses a
  stem where the natural word varies: `"decid"` matches both `decision` and
  `decider`. `about_contains` is matched against the gap's `about` field
  concatenated with its `quote`, and may be **a list**, in which case any one
  member satisfies it. An omitted field matches anything.
- `gaps_must_be_empty` — when true, any entry in `gaps` fails the run.
- `skipped_must_be_nonempty` — when true, `skipped` must name what the budget
  dropped.
- `verdict_regex` — an optional regex against the `verdict` string. Used only
  where the verdict *is* the product, i.e. `pure-hedge.md`. The verdict is a
  JSON field, so this is still grading JSON.

### Budget invariants (all fixtures)

From the output budget in `TRIAGE.md`, checked on every run rather than
declared per fixture:

- `facts` holds at most 12 entries.
- `gaps` holds at most 5, with unique `rank` values starting at 1.
- `questions` holds at most 5.
- `speaker` and `message_date` are required on every fact when `is_thread` is
  true, and absent when it is false.
- No SEE-100 rule number appears anywhere in the output.

Recall passing is not sufficient on `long-report.md`. A run that fills its
twelve slots with appendix trivia and drops the $240,000 risk has failed the
ranking even though the required six are present, because the required six are
chosen to be the consequential ones.

## First person versus the `From:` line

These look similar and only one is banned.

Banned, per `TRIAGE.md`: taking an owner from the `From:` line or the
signature. "A rollback plan will be written before the cutover", sent by Dana,
has **no owner**. Crediting Dana is fabrication. This is the trap in
`thread-contradictions.md`.

Not banned: resolving the first person. "I'll send the corrected churn
breakdown by Jul 31", written by Marco, is a commitment owned by Marco with
`provenance: "stated"`. The contract's own worked example does exactly this
(owner `Dana`, quote `"I'll move the last two services over by Sep 5"`,
provenance `stated`). The document names an owner; the pronoun just has to be
resolved to the speaker.

## Writing a new fixture

The gold file is the measuring stick, so a wrong gold file quietly corrupts
every grade taken after it. Before adding one:

1. Confirm every `quote_contains` appears **verbatim** in the fixture. Keep
   each one inside a single line so quoted-reply prefixes (`> `) cannot break
   the substring.
2. Confirm every owner, date, decider, value and baseline in `facts` is
   genuinely stated in the sentence holding the quote, not merely inferable
   from it.
3. Confirm every `gaps_must_include` entry is genuinely absent from the
   document, and every `gaps_must_not_include` entry is genuinely present.
4. Put anything true but not required in `allowed_facts`, so a good run is
   never punished for extracting more than the minimum.
5. Record every deliberate trap in `notes`.
