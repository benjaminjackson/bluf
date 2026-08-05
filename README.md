# bluf

**Before:**

> Quick update: the migration is progressing well. We're seeing significant improvement in checkout latency and we should be able to leverage the new caching layer across other services soon.

**After:**

> The migration is on track for the Oct 2 cutover. Checkout latency fell 38%, from 210ms to 130ms, after the Aug 12 cache change. Marco moves the two remaining services to the new caching layer by Sep 5.

The first paragraph commits to nothing. The second commits to a state, a
number with its baseline, an owner, and three dates. bluf is a Claude Code
plugin that turns the first kind of paragraph into the second, by enforcing
[SEE-100](docs/SEE-100.md) — an adaptation of ASD-STE100 Simplified
Technical English for executive prose.

## Install

```
/plugin marketplace add benjaminjackson/bluf
/plugin install bluf@bluf
```

## Skills

- `/bluf:lint` — check a document against SEE-100. Reports each violation
  with its rule number; never edits.
- `/bluf:rewrite` — rewrite a document into compliance, voice preserved. It
  never invents facts: what only you know (an owner, a date, a number) goes
  in a Gaps list instead.
- `/bluf:triage` — extract the real state of the world from documents you
  *receive*: decisions, owners, dates, numbers, and what's evasively missing.
  Asks nothing of the sender.
- `/bluf:draft` — templates as interviews: the skill asks what the standard
  requires — state, owners, dates, numbers — then assembles the compliant
  document. Status update, board memo, postmortem, risk register.
- `/bluf:selftest` — diagnostic. Verifies an installed copy can read its own
  data files.
- `/bluf:explain` — for any rule, banned term, or flagged sentence: the rule
  verbatim, its verified STE lineage, and curated example rewrites.

## Why STE?

ASD-STE100 exists because ambiguity in a maintenance manual kills people.
Its rules — controlled vocabulary, sentence limits, active voice, rigid
structure — make each sentence mean exactly one thing. Executive prose
rarely fails from that kind of ambiguity. It fails from evasion: hedged
claims, buried recommendations, passive voice that hides owners, adjectives
where numbers belong. [SEE-100](docs/SEE-100.md) points the same machinery
at that target. STE removes ambiguity about actions on objects; SEE removes
ambiguity about decisions, owners, numbers, and dates.

## Attribution

SEE-100 follows the structure and rule numbering of ASD-STE100 Simplified
Technical English, Issue 8 (April 2021), a registered specification of the
AeroSpace and Defence Industries Association of Europe (ASD). It does not
reproduce the ASD-STE100 dictionary or its rule text. This project is not
affiliated with, sponsored by, or endorsed by ASD. Obtain ASD-STE100 itself
from [asd-ste100.org](https://www.asd-ste100.org/).

Code is MIT-licensed; the SEE-100 document carries its own terms. See
[LICENSE](LICENSE), [LICENSE-DOCS](LICENSE-DOCS), and [NOTICE](NOTICE).
