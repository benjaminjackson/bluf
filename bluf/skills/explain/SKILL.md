---
name: explain
description: Explain any SEE-100 rule, banned term, or flagged sentence — the rule verbatim, its verified STE lineage, and curated example rewrites. Use when the user runs /bluf:explain, asks what a rule number means, why a word is banned, or "what's wrong with this sentence" after a lint.
---

# /bluf:explain

Given a rule number, a term, a section, or a sentence: the rule quoted
verbatim, its STE lineage, and curated examples. This is the retention
layer — the goal is writers who internalize the standard and stop
needing the tool.

## Data, and what may be said

1. `${CLAUDE_PLUGIN_ROOT}/docs/SEE-100.md` — rule text is **quoted
   verbatim** from here, never paraphrased into authority.
2. `${CLAUDE_PLUGIN_ROOT}/data/lineage.json` — the ONLY source for STE
   citations. **Never name an STE rule number absent from this file.**
   `ste: null` is said as "no direct STE ancestor" plus the file's note.
   A fabricated citation into a registered third-party specification is
   the one unforgivable output of this skill.
3. `${CLAUDE_PLUGIN_ROOT}/data/examples.json` — examples come from here,
   per the rule's `shape`: `rewrite` rules show before/after pairs;
   `structure` rules (5.1, 6.1, 7.3…) show document order, not sentence
   rewrites; `guidance` rules get the guidance text — three rewrites of
   "read it back" is nonsense.
4. `${CLAUDE_PLUGIN_ROOT}/data/dictionary.json` — term routing via
   `rule_ref`: primary rule first, then "also touches" cross-references.

## Entry points, all reaching the same answer

- **A rule number** ("8.6", "explain 5.4") — direct.
- **A bare term or quoted phrase** ("material", "circle back") — through
  the dictionary's `rule_ref.primary`; name the cross-references so a
  dual-homed term ("material" is 8.5 as an intensifier, 1.3 as a lock)
  gets one designated answer plus its siblings, not a shrug.
- **A section** ("Section A", "section 8", "Part 2") — that section's
  rule list with one-line summaries, not a refusal.
- **A sentence** — the raw-sentence path below.

Unknown numbers, three distinct cases:

- Out of range ("10.1", "8.9"): reject plainly — "SEE-100 has no rule
  10.1."
- Valid in STE but not SEE ("3.6", "6.6"): "SEE has no rule 3.6; the STE
  rule of that number maps to SEE X per the appendix" — find X in
  lineage.json by searching `ste` values.
- Section-level input: the rule list, as above.

## Raw-sentence path

Run the SAME procedure lint runs — shared instruction, not a paraphrase:

1. Checker via Bash on the sentence written to a temp file:
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/see100_check.py" <tempfile>`
2. Confirm or discard candidates; add judgment findings per the rules in
   `${CLAUDE_PLUGIN_ROOT}/docs/FINDINGS.md`. Explain and lint must never
   disagree on one sentence in public.
3. Report ALL violated rules, deterministic first. Explain the
   highest-severity one in full (rule verbatim, lineage, examples); list
   the rest as "also violates: 8.5, 4.1".

**Compliant sentence**: the fixed no-violation output — "This sentence is
compliant. Nearest applicable rule: X, which it satisfies because …".
Never hunt for something wrong; a writer told their clean sentence is
broken stops trusting the standard permanently.

## Output, in order

1. **The rule, verbatim** — quoted from SEE-100.md, cited by number.
2. **Lineage** — the STE citation from lineage.json, or "no direct STE
   ancestor" with the note.
3. **Examples** — per the rule's shape, from examples.json.
4. For sentences: the also-violates list.

If the request contains "emit explain JSON", append one fenced `json`
block, last in the response, no prose inside:

```json
{
  "version": 1,
  "rule": "8.6",
  "rule_text": "…the verbatim rule text…",
  "ste": "…the lineage.json ste value, or null…",
  "shape": "rewrite",
  "also_violates": []
}
```

`rule_text` is copied character-for-character from SEE-100.md (the bold
rule line's text after the dash). `ste` is copied from lineage.json —
these two fields are machine-checked against the source files.

Special cases in the JSON:

- Out-of-range number: `{"version": 1, "rule": null, "rejected": "10.1"}`.
- STE-only number: `{"version": 1, "rule": null, "ste_only": "3.6",
  "maps_to": "3.3"}` — `maps_to` found by searching lineage.json `ste`
  values.
- Compliant sentence: the nearest rule's fields plus `"compliant": true`
  and an empty `also_violates`.
- Sentence with violations: the explained (highest-severity) rule's
  fields plus `also_violates` listing every other violated rule number.

## Failure behavior

If SEE-100.md, lineage.json, examples.json, or dictionary.json cannot be
read: stop and report the exact path that failed. Never explain from
memory — a plausible paraphrase of a rule is a second standard.
