# bluf — Marketplace Specification

*bluf is a Claude Code plugin marketplace. Its one plugin, `bluf`, enforces the
[SEE-100 standard](SEE-100.md) on executive prose: bottom line up front, named
owners, real dates, no evasion.*

Status: draft. The repo stays private until `/bluf:lint` and `/bluf:rewrite` ship.

---

## Repository Layout

```
bluf/
├── .claude-plugin/
│   └── marketplace.json          # marketplace manifest
├── docs/
│   ├── SEE-100.md                # the standard (human-readable, canonical prose)
│   └── SPEC.md                   # this file
└── plugins/
    └── bluf/
        ├── .claude-plugin/
        │   └── plugin.json
        ├── data/
        │   └── dictionary.json   # banned list + meaning locks (machine-readable)
        ├── docs/
        │   └── SEE-100.md        # copy shipped with the plugin (skills read this)
        └── skills/
            ├── lint/SKILL.md
            ├── rewrite/SKILL.md
            ├── triage/SKILL.md
            ├── draft/SKILL.md
            └── explain/SKILL.md
```

Installed plugins only get the plugin directory, so the standard and the
dictionary ship inside `plugins/bluf/`. The root `docs/SEE-100.md` remains the
canonical copy for readers and the README link target.

## The Dictionary: Prose and Data in Parallel

Part 2 of SEE-100 exists twice, on purpose:

1. **Prose** — the markdown tables in `docs/SEE-100.md` (Section A banned words,
   Section B meaning locks). Canonical for humans.
2. **Data** — `plugins/bluf/data/dictionary.json`. Canonical for skills.

The two must never drift. Rules:

- Every entry in the markdown tables has exactly one entry in the JSON, and
  vice versa.
- A change lands in both files in the same commit, or it does not land.
- A sync check (script that parses the markdown tables and diffs them against
  the JSON) runs before any release. Drift fails the release.

`dictionary.json` shape (the minimal `term`/`pos`/`instead`/`rule` sketch could
not express what the checker needs, so the schema grew):

```json
{
  "see100": "1.0",
  "banned": [
    {
      "term": "leverage",
      "row": "leverage (v)",
      "rule": "1.1",
      "pos": "verb",
      "instead": "use",
      "patterns": ["leverage", "leverages", "leveraged", "leveraging"],
      "exceptions": ["leverage ratio", "leveraged buyout"]
    }
  ],
  "locks": [
    { "term": "on track", "rule": "1.3", "meaning": "The committed date and scope will hold. Nothing else." }
  ],
  "prose_bans": [
    { "term": "soon", "rule": "8.2", "condition": "as a date", "instead": "a calendar date", "patterns": ["soon"] }
  ]
}
```

Field notes:

- `row` is the verbatim banned-column cell from the Section A table; the sync
  check joins on it. Slash rows that are inflections of one term ("synergy /
  synergies") stay one entry with pattern variants; slash rows of distinct
  terms ("headwinds / tailwinds") become one entry per term sharing a `row`.
- `rule` is a citable Part 1 rule number, not a table letter: 1.1 plain bans,
  1.2 part-of-speech bans, 1.3 locks, 1.6 noun-verbing, 3.5 phrasal idioms,
  and for `prose_bans` 8.5 / 8.2 / 3.4 / 5.4.
- Parentheticals in the tables map to fields: part of speech → `pos`, scope
  qualifier ("of people") → `scope`, usage condition ("as praise") →
  `condition`, delete-instructions in the substitution column → `delete: true`
  plus `note`.
- `exceptions` suppress a match ("pivot table", "action items").
- Entries with `condition`, `scope`, or `confirm: true` emit candidates the
  model must confirm (hybrid layer, per FINDINGS.md); `confirm` marks
  part-of-speech bans on common nouns where text alone cannot tell verb from
  noun. All other entries are plain deterministic findings.
- `prose_bans` holds terms Part 1 bans in prose that the tables omit
  (intensifiers, non-dates, nominalizations, "we should").
- Vague quarter references without a day ("Q3", "EOY") are deliberately not
  dictionary entries: they are a pattern class for the deterministic checker's
  date regex, not a word list.

## Architecture: Two Layers

Every skill separates its checks into two layers and reports which layer
produced each finding.

- **Deterministic** — findings the checker script produces: banned words,
  sentence length over 25 words (20 inside explicitly marked asks lists),
  semicolons, quarter deadlines with no day. Some checks emit *candidates*
  the model must confirm (noun clusters, vague date words, percentages with
  no baseline, conditioned banned terms) — confirmed candidates are judgment
  findings. The full layer contract lives in `plugins/bluf/docs/FINDINGS.md`.
  Cited by rule number. No judgment, no false modesty.
- **Judgment** — findings that need a model: is the recommendation first
  (5.1)? Does each action item name one owner and one date (5.4)? Are claims
  tagged fact / estimate / opinion (9.2)? Is a locked word used inside its
  lock (1.3)? Cited by rule number and labeled as judgment.

## Skills

Ship order: 1–2 first (they share machinery), then 3, then 4–5.

### 1. `/bluf:lint`

Input: a document (file path or pasted text).
Output, in order:

1. One verdict line: pass, or the violation count by severity.
2. Violations: rule number, quote, location, suggested fix. Deterministic
   findings first, judgment findings labeled.

Lint never edits. It reports.

### 2. `/bluf:rewrite`

Input: a document. Output, in order:

1. The compliant rewrite, voice preserved.
2. Change log: each change with its rule number.
3. **Gaps** — what the rewrite could not fix because only the writer knows it:
   a missing owner, a missing date, a claim with no number. The skill never
   invents facts to satisfy a rule.
4. **Kept deviations** — the escape hatch. Where full compliance is a choice
   with consequences (naming who decided, stating a blunt number), the skill
   produces the compliant version and lists each deviation the writer might
   consciously keep. The tool makes evasion a visible choice. It does not
   choose.

### 3. `/bluf:triage`

For documents the user *received*. Extracts the actual state of the world:
decisions (with decider and date), owners, dates, numbers, risks. Then lists
what is evasive or missing ("no date appears in this update"). Requires no
behavior change from the sender. Zero adoption cost.

### 4. `/bluf:draft`

Templates as interviews: status update, board memo, postmortem, risk register.
The skill asks the questions the standard requires answered — state? owner?
date? denominator? — then assembles the compliant document. Compliance becomes
the path of least resistance instead of a revision tax.

### 5. `/bluf:explain`

Given a flagged sentence or a rule number: the rule, its STE lineage, and three
example rewrites. The retention layer. The goal is writers who internalize the
standard and stop needing the tool.

## Test Corpus

`plugins/bluf/tests/` holds sample documents with known violations, each with
an expected-findings file. A change to a skill is checked against the corpus
before merge. Without the corpus, every prompt tweak is a guess.

## README Requirements

In order:

1. One before/after example at the top — an ugly real-world paragraph next to
   its SEE rewrite. This sells the tool. Nothing goes above it.
2. Install instructions:
   ```
   /plugin marketplace add benjaminjackson/bluf
   /plugin install bluf@bluf
   ```
3. The skills, one line each.
4. The lineage: ASD-STE100 exists because ambiguity in a maintenance manual
   kills people. SEE-100 points the same machinery at evasion in business
   prose. Link to `docs/SEE-100.md`.
5. The ASD-STE100 attribution and the does-not-reproduce-its-dictionary note,
   carried over from the standard.

## Release Criteria (v0.1.0, flip public)

- `/bluf:lint` and `/bluf:rewrite` pass the test corpus.
- `dictionary.json` and the SEE-100 tables pass the sync check.
- README meets the requirements above.
- LICENSE file present.

Everything else — triage, draft, explain, CI hooks for team enforcement —
ships after public launch.
