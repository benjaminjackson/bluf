---
name: rewrite
description: Rewrite a document into SEE-100-compliant executive prose, preserving the writer's voice and facts. Use when the user runs /bluf:rewrite or asks to fix, tighten, or make a memo, status update, or business document compliant with SEE-100.
---

# /bluf:rewrite

Rewrite the given document (file path or pasted text) so it complies with
SEE-100, without inventing a single fact.

## Procedure

1. Run the deterministic checker on the input via Bash:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/see100_check.py" <document-path>
   ```
   For pasted text, write it to a temp file first, unchanged.
2. Read `${CLAUDE_PLUGIN_ROOT}/docs/FINDINGS.md` and, when you need rule
   text, `${CLAUDE_PLUGIN_ROOT}/docs/SEE-100.md`.
3. Rewrite. Fix every deterministic finding, every candidate you confirm,
   and every judgment-layer violation you identify. Preserve the writer's
   voice: their word choices survive wherever the standard allows them.
   Restructure for BLUF (5.1/6.1) when the recommendation is buried.
4. Run the checker on your rewrite. If it reports deterministic findings,
   fix them and run it again before presenting.

## Hard rules

- **Never invent facts.** No new names, dates, numbers, dollar amounts, or
  decisions. A fabricated "Maria decided on Aug 15" is this skill's worst
  failure. Where a rule demands a fact only the writer knows, the rewrite
  stays vague there and the gap goes in the Gaps section.
- **Never edit inside blockquotes** or quotations of someone else's words.
  Quoted evasion belongs to its author.
- **Keep facts in their original written form.** Reuse the document's exact
  spellings of numbers, dates, names, and amounts ("Aug 7" stays "Aug 7",
  never "August 7"). Reformatting a fact reads as fabricating one.
- Rule 9.1: when a banned word has no one-word substitute, restate the
  actual thing — never thesaurus-swap.

## Output, in order

1. **Rewrite** — the full compliant document, in one fenced block.
2. **Changes** — each change with its rule number.
3. **Gaps** — what the rewrite could not fix because only the writer knows
   it: a missing owner, a missing date, a claim with no number. Cite the
   rule each gap violates. If there are none, say "none".
4. **Kept deviations** — where full compliance is a choice with consequences
   (naming who decided, stating a blunt number), list each deviation the
   writer might consciously keep. The tool makes evasion a visible choice;
   it does not choose. If there are none, say "none".

If the request contains "emit rewrite JSON", append one fenced `json` block:
`{"rewrite": "<full text>", "changes": [{"rule", "from", "to"}], "gaps":
[{"rule", "what"}], "kept_deviations": [{"rule", "what"}]}`. No prose inside
the block.

## Failure behavior

Same as `/bluf:lint`: if Bash is unavailable, say so up front and label the
whole rewrite as unchecked; if the dictionary, standard, or checker cannot
be read, stop and report the exact path that failed — never work from
memory of the standard.
