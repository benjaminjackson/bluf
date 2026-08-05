# Findings Schema and Rule Classification

This document is the contract between the deterministic checker
(`scripts/see100_check.py`), the skills (`/bluf:lint`, `/bluf:rewrite`), and
the grading harness. The script emits JSON. The skills render prose from that
JSON and add judgment findings to it. The harness grades JSON and never parses
prose.

Machine data never round-trips through the model. When a skill is asked for
findings JSON it emits only its judgment-layer findings; any consumer that
needs the deterministic layer runs the checker itself and combines the two.
A model asked to copy JSON through its own output will eventually retype it
wrong — the grading harness proved this, so the contract forbids it.

## Findings JSON

The checker writes one JSON object to stdout:

```json
{
  "version": 1,
  "findings": [
    {
      "rule": "1.1",
      "layer": "deterministic",
      "severity": "error",
      "scope": "span",
      "line": 12,
      "col": 8,
      "quote": "leverage",
      "message": "banned word 'leverage' (banned as: verb)",
      "suggestion": "use"
    }
  ]
}
```

Field rules:

- `rule` — a citable SEE-100 rule number ("1.1", "8.2"). Never a section
  letter.
- `layer` — `deterministic` or `judgment`. Deterministic findings come only
  from the script. A skill may not re-derive, add to, reword, or drop them.
- `severity` — `error` or `warning`, assigned per rule by the table below,
  never chosen at emit time. The verdict line counts by severity.
- `scope` — `span` or `document`. Document-scope rules (5.1, 5.5, 6.1, 6.2,
  1.5, 1.7, 7.3, 9.3, 9.4) describe the whole document and carry no
  `line`/`col`/`quote`; the `message` carries the explanation.
- `line`/`col` — 1-indexed, on the original unmodified document. Only the
  script emits them: deterministic findings and script-emitted candidates
  carry line/col. Model-added judgment findings never carry line numbers —
  models miscount lines. They locate by `quote` instead.
- `quote` — the exact span from the document. Required for every span
  finding. For judgment findings it is the location mechanism: it must appear
  verbatim in the document.
- `candidate` — `true` on hybrid-rule findings the script emits for the model
  to confirm (see Hybrid rules). Candidates are not findings; unconfirmed
  candidates are dropped, confirmed ones become judgment-layer findings.
- `acknowledged` — `true` on a judgment finding the document's Gaps section
  covers (see Gaps-aware mode). Absent otherwise. Deterministic findings
  never carry it.
- `suggestion` — the fix, when one exists. From the dictionary's `instead`
  column for word findings.

## Hybrid rules

The stdlib has no part-of-speech tagger and the plugin ships no dependencies,
so rules whose trigger needs classification run in two steps: the script emits
`candidate: true` findings from a cheap over-inclusive pattern, and the model
confirms or discards each one. Confirmed findings are labeled `judgment`.

Hybrid by this mechanism:

- **2.1 noun clusters** — candidates are runs of 4+ words containing no
  article, preposition, conjunction, or verb. The model discards official
  names introduced per 2.2.
- **Conditioned dictionary entries** — any `banned` or `prose_bans` entry with
  a `condition`, `scope`, or `confirm` field ("robust (as praise)", "bandwidth
  (of people)", "significant on a quantity", "soon as a date") matches as a
  candidate; the model checks the condition. `confirm: true` marks
  part-of-speech bans on common nouns (action, dialogue, whiteboard, leverage)
  where a bare text match cannot tell verb from noun. Unconditioned entries
  are plain deterministic errors.
- **8.6 baselines** — candidates are percentage/multiple tokens ("up 30%",
  "3x") with no baseline marker (from, vs, versus, baseline, compared)
  in the same sentence.
- **5.2 ask length** — deciding what is an "ask" is judgment. Exception: in an
  explicitly marked action-item or asks list (a heading containing "action
  item", "asks", or "requests"), every list item is an ask and the 20-word
  limit fires deterministically.

## Gaps-aware mode

"Passes lint clean" is an incentive to invent an owner. The honest document
— the one that says the owner is not yet assigned — breaks rule 5.4, so the
compliant-looking document and the truthful one are different documents.
Gaps-aware mode is how the truthful one wins.

**The marked-unknown convention**, shared by every skill: a document
acknowledges an unknown in a `## Gaps` section, or in a `Gaps:` list when it
is too short for headings. Each item names the missing slot in plain words,
and the thing the slot belongs to:

- Owner for the rollback plan: not yet assigned.
- Date for the migration: to be set by Fri.

ALL-CAPS placeholders (OWNER, DATE, N) may stand in the body only when the
same unknown is listed in Gaps. A placeholder with no Gaps item is an
unmarked hole, and lint reads it as one.

**Acknowledgment.** Lint reports every finding, always — a declared gap is
still a gap. A finding whose subject a Gaps item names is *acknowledged*: it
counts separately in the verdict and it does not fail the document. Coverage
is a judgment call, never a string match. The Gaps item must name the same
missing thing as the finding, not merely sit in the same document.

**PASS.** A document passes when every error-severity finding is
acknowledged. A pass carrying acknowledged findings is a legal verdict, and
says so: `PASS, 3 acknowledged (read as: status update)`. Warnings never
fail a document, acknowledged or not.

**Where the flag lives.** In the findings JSON, an acknowledged judgment
finding carries `"acknowledged": true`. Deterministic findings never carry
it. The JSON block stays judgment-only, so a deterministic finding
round-trips nowhere and has nowhere to put the flag: its acknowledgment
appears in the rendered prose and in the verdict arithmetic, and nowhere
else. A consumer that wants to know which deterministic findings the Gaps
section covers reads the prose. The checker itself does not change —
acknowledgment is a judgment-layer classification laid over the checker's
output, never an output of the checker.

Two worked examples, both against this action item:

    - OWNER: write the rollback plan by Aug 11.

Rule 5.4 fires: the item names no owner.

- Gaps says "Owner for the rollback plan: not yet assigned." — **covered**.
  The item names the same slot (owner) on the same thing (the rollback
  plan). Lint reports the finding and marks it acknowledged.
- Gaps says "Date for the load test: not yet set." — **not covered**. That
  item is honest about a different unknown, and the owner is still missing
  with nothing said about it. Lint reports the 5.4 finding unacknowledged,
  and the document fails.

## Sentence segmentation and word counting

Rule 4.1 is the most-cited rule in every run; the splitter is specified
exactly so two implementations cannot disagree.

Skip regions — excluded from every check, by script and skills alike; never
flag or edit inside them:

1. Fenced code blocks and inline code.
2. URLs and file paths (a token containing `://`, or starting with `/`, `./`,
   `~/`, or matching `\S+\.(md|py|json|js|ts|yml|yaml|txt)\b`).
3. YAML frontmatter at document start.
4. Blockquote lines (`>` prefix) — someone else's words are quoted, not
   written, and are never findings against this document's author.

Sentence boundaries:

- A sentence ends at `.`, `!`, or `?` followed by whitespace and then an
  uppercase letter, digit, `"`, or end of text.
- Not a boundary: a period inside a decimal (`4.1%`), a version or rule
  number (`8.2`), an abbreviation from this list (case-sensitive, trailing
  period): `e.g. i.e. etc. vs. cf. approx. est. Inc. Corp. Ltd. LLC. Co.
  Mr. Ms. Mrs. Dr. Jr. Sr. St. No. Dept. Fig. Rev. Jan. Feb. Mar. Apr. Jun.
  Jul. Aug. Sep. Sept. Oct. Nov. Dec.`
- Headings (`#` lines) and table rows (`|` lines) are not sentences and are
  excluded from sentence checks entirely.
- A list item (`-`, `*`, `+`, or `1.` prefix) is one sentence-equivalent: it
  is subject to length limits even without terminal punctuation. Multiple
  sentences inside one item segment normally.

Word counting:

- A word is a whitespace-delimited token after markdown markers (`*`, `_`,
  `#`, list prefixes) are stripped.
- Hyphenated compounds are one word (`best-in-class` = 1).
- A number with its unit sticks together: `12%`, `$1.5M`, `4.1x` = 1 word
  each. `Aug 15` = 2 words.
- A markdown link `[text](url)` counts the text words only; the URL counts 0.
  A bare URL counts as 1 word.
- Em-dash–joined clauses are separate words; the dash itself counts 0.

## Rule classification

Every SEE-100 rule, its layer, severity, and scope. `det` = deterministic,
`jdg` = judgment, `hyb` = hybrid (script candidates, model confirms, labeled
judgment). Rules marked both det and jdg: the dictionary-listed terms fire
deterministically; novel instances are judgment.

| Rule | What fires | Layer | Severity | Scope |
|---|---|---|---|---|
| 1.1 | banned-list word (unconditioned entry) | det | error | span |
| 1.1 | banned-list word (conditioned entry) | hyb | error | span |
| 1.2 | part-of-speech ban ("the ask") | det+jdg | error | span |
| 1.3 | meaning-lock word outside its lock | jdg | error | span |
| 1.4 | jargon with a plain-word equivalent | jdg | warning | span |
| 1.5 | multiple names for one thing | jdg | warning | document |
| 1.6 | noun used as verb | det+jdg | error | span |
| 1.7 | term of art never defined | jdg | warning | document |
| 2.1 | noun cluster over 3 words | hyb | warning | span |
| 2.2 | long official name never short-formed | jdg | warning | span |
| 2.3 | dropped articles (slide-speak) | jdg | warning | span |
| 3.1 | passive voice hiding an actor | jdg | error | span |
| 3.2 | non-simple tense | jdg | warning | span |
| 3.3 | hedging helping verbs | jdg | error | span |
| 3.4 | nominalization | det+jdg | warning | span |
| 3.5 | phrasal-verb idiom | det | error | span |
| 4.1 | sentence over 25 words | det | error | span |
| 4.2 | more than one idea/ask per sentence | jdg | warning | span |
| 4.3 | fragment posing as a sentence | jdg | warning | span |
| 4.4 | 4+ parallel items not in a list | jdg | warning | span |
| 4.5 | missing connector between related sentences | jdg | warning | span |
| 5.1 | recommendation not in first sentence | jdg | error | document |
| 5.2 | ask over 20 words | hyb | error | span |
| 5.3 | ask not imperative / no named recipient | jdg | error | span |
| 5.4 | "we should" as an owner | det | error | span |
| 5.4 | action item without one owner and one date | jdg | error | span |
| 5.5 | ask hidden inside context | jdg | warning | document |
| 6.1 | conclusion not first | jdg | error | document |
| 6.2 | status not one of the three states | jdg | error | document |
| 6.3 | sentence over 25 words (status docs) | det | error | span |
| 6.4 | paragraph over 6 sentences | det | warning | span |
| 6.4 | more than one topic per paragraph | jdg | warning | span |
| 6.5 | activity reported instead of results | jdg | warning | span |
| 7.1 | risk without RISK/BLOCKER label | jdg | error | span |
| 7.2 | risk missing trigger/consequence/cost/owner | jdg | error | span |
| 7.3 | risks after the plan or in an appendix | jdg | warning | document |
| 8.1 | size/speed/change claim with no number or label | jdg | error | span |
| 8.2 | quarter/EOQ/EOY deadline (after by/in/until/before) with no day in the sentence | det | error | span |
| 8.2 | vague date word ("soon", "next sprint") | hyb | error | span |
| 8.3 | false precision / range without confidence | jdg | warning | span |
| 8.4 | missing denominator | jdg | error | span |
| 8.5 | intensifier on a quantity | hyb | error | span |
| 8.6 | percentage without baseline and period | hyb | error | span |
| 8.7 | semicolon | det | error | span |
| 9.1 | thesaurus-swap instead of restatement | jdg | warning | span |
| 9.2 | interpretive claim not tagged fact/estimate/opinion | jdg | error | span |
| 9.3 | inconsistent labels/formats for same construction | jdg | warning | document |
| 9.4 | sentence that needs context to survive quotation | jdg | warning | document |

Notes:

- The checker emits over-25-word sentences as rule 4.1. In its rendered prose
  a skill may mention 6.3 alongside 4.1 for status reports, but the finding —
  and the JSON — always keeps rule 4.1 verbatim; the two rules share one
  check, run once.
- 6.4's sentence-count half (countable) is deterministic; its one-topic half
  is judgment. Two rows, one rule.
- Document-scope rules fire at most once per document.
- 6.2 fires only when the document is a status update. The verdict line names
  the document type the skill assumed, so a wrong assumption is visible and
  correctable.
- 9.1 and 9.4 are primarily practices for `/bluf:rewrite`; lint emits them
  sparingly.
