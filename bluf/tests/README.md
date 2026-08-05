# Test Corpus

Each `<name>.md` fixture has a `<name>.expected.json` file:

- `script` — the exact findings array `scripts/see100_check.py` must emit for
  the fixture, including `candidate: true` entries. Graded by set equality on
  every field. Regenerate only when the checker intentionally changes, and
  eyeball the diff: this file is the checker's contract.
- `judgment` — grading for `/bluf:lint`'s judgment layer. The skill's JSON
  block carries only judgment findings; the harness runs the checker itself
  for the deterministic layer and grades the two together (a deterministic
  finding inside the skill's JSON fails the run):
  - `must_find` — each entry names a `rule` and optionally a `quote`; a skill
    finding matches by rule plus span overlap with the quote, never by
    wording. All must be present in every run. An entry may also pin
    `acknowledged` (`true` or `false`) — the gaps-aware classification the
    matching finding must carry. This narrows the match: judgment findings
    only, because deterministic findings never carry the flag (FINDINGS.md,
    "Gaps-aware mode").
  - `must_not_find` — matches here fail the run. `"rule": "*"` means any
    finding fails; `acknowledged` narrows it the same way, so
    `{"rule": "*", "acknowledged": true}` fails the run on any acknowledged
    finding at all.
  - `allowed` — documentation for humans: the harness allows anything
    `must_not_find` does not match, so this list is never read by code.
- `rewrite` — for rewrite fixtures: `gaps_must_include` lists rule numbers
  that must appear in the Gaps section. The harness also checks every number,
  date, proper noun, and dollar amount in the rewrite against the input
  (closed world): a new fact is a hard fail.

The harness runs each fixture through the skill 3 times; disagreement between
runs on `must_find`/`must_not_find` is a failure.

## Sub-corpora

- `triage/` — extraction fixtures with hand-written gold files; format and matching semantics in `triage/README.md`.
- `draft/` — interview personas; format and the four grades in `draft/README.md`.
