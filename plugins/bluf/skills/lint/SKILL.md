---
name: lint
description: Check a document against the SEE-100 standard for executive prose. Reports violations with rule numbers; never edits. Use when the user runs /bluf:lint, asks to lint or check a memo, status update, or business document against SEE-100, or asks "is this compliant".
---

# /bluf:lint

Check the given document (file path or pasted text) against SEE-100 and
report findings. Lint never edits — it reports.

## Procedure

1. Run the deterministic checker via Bash:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/see100_check.py" <document-path>
   ```
   For pasted text, write it to a temp file first, unchanged.
2. Read `${CLAUDE_PLUGIN_ROOT}/docs/FINDINGS.md` for the rule classification
   and `${CLAUDE_PLUGIN_ROOT}/docs/SEE-100.md` when you need rule text.
3. Split the checker's output:
   - Findings without `candidate` are **deterministic**. Reproduce them
     verbatim — never re-derive, add to, reword, drop, or re-count them.
   - Findings with `candidate: true` are hybrid candidates. Confirm or
     discard each one against its condition (part of speech, "as praise",
     "of people", "as a date", is it really a noun cluster, does the
     sentence really lack a baseline). Confirmed candidates become
     judgment findings; discarded ones vanish silently.
4. Add judgment-layer findings for the rules the script cannot check — the
   `jdg` rows in FINDINGS.md. Every judgment finding carries a `quote` (the
   exact span, verbatim from the document — never a line number) or, for
   document-scope rules, a message only. First decide the document type
   (status update, memo, postmortem, email, other); document-scope rules like
   6.2 fire only for the types they apply to.
5. Walk the document-scope rules as an explicit checklist — 1.5, 1.7, 5.1,
   5.5, 6.1, 6.2, 7.3, 9.3, 9.4 — and decide fire / no-fire for each. For a
   status update whose conclusion is buried, cite 6.1; cite 5.1 only when a
   concrete recommendation or ask exists and sits below the evidence. Do not
   skip this walk: a missed document-scope rule is the most common lint
   failure.
6. Assemble severities from FINDINGS.md. Severity is fixed per rule — never
   choose it yourself.

## Output, in order

1. **Verdict line**: `PASS` or `N errors, M warnings`, plus the document type
   you assumed (e.g. "read as: status update"). Nothing goes above it.
2. **Deterministic findings** — for each: rule number, quote, line:col,
   message, suggested fix.
3. **Judgment findings**, labeled `[judgment]` — for each: rule number,
   quote (or "whole document"), message, suggested fix.

If the request contains "emit findings JSON", append one fenced `json` block
containing **only your judgment-layer findings** (confirmed candidates plus
model-added findings) in the FINDINGS.md schema. Do not include the checker's
deterministic findings — machine data never round-trips through you; whoever
asked for the JSON runs the checker directly and combines the two layers. No
prose inside the block.

## Failure behavior

- If Bash is unavailable: the verdict line must say "degraded: checker not
  run", and every finding you emit is labeled `[judgment]` — none may claim
  to be deterministic.
- If `${CLAUDE_PLUGIN_ROOT}/data/dictionary.json`,
  `${CLAUDE_PLUGIN_ROOT}/docs/SEE-100.md`, or the checker script cannot be
  read: stop and report the exact path that failed. Never fall back to your
  memory of the dictionary or the standard.
