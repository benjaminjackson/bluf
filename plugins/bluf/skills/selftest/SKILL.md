---
name: selftest
description: Diagnostic probe. Proves an installed copy of the bluf plugin can read its own shipped data files. Use when the user runs /bluf:selftest or asks to verify the bluf plugin installation.
---

# bluf selftest

Prove this installed copy of the plugin reads its own data. Do exactly this:

1. Read `${CLAUDE_PLUGIN_ROOT}/data/dictionary.json`.
2. Read `${CLAUDE_PLUGIN_ROOT}/docs/SEE-100.md`.
3. Count the data rows of the two markdown tables in SEE-100.md Part 2
   (Section A banned words, Section B meaning locks). Do not count the header
   or separator rows.
4. Report, in this order:
   - The absolute path the plugin root resolved to.
   - Banned rows: the count of distinct `row` values in `banned`, the total
     entry count, and the Section A table row count. The distinct-row count
     must equal the table row count.
   - Locks: the length of `locks` and the Section B table row count. They
     must be equal.
   - Prose bans: the length of `prose_bans`.
   - The dictionary `see100` value and the `Version:` line from SEE-100.md
     (they must match).
5. End with one verdict line: `SELFTEST PASS` if the dictionary counts match
   the table counts and the versions match, otherwise `SELFTEST FAIL` plus
   what was wrong.

Do not read any file outside `${CLAUDE_PLUGIN_ROOT}`. If a file is missing,
that is a FAIL — report the path you tried.
