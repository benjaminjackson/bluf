---
name: draft
description: Build a compliant document by interview — status update, board memo, postmortem, or risk register. The skill asks what SEE-100 requires answered (state, owners, dates, numbers), then assembles the document. Use when the user runs /bluf:draft, asks to write or draft a status update, memo, postmortem, or risk register, or says "turn my notes into a status update".
---

# /bluf:draft

Interview the user with the questions SEE-100 requires answered, then
assemble the compliant document. The interview is the product; the
document is its receipt.

## Procedure

1. Read `${CLAUDE_PLUGIN_ROOT}/docs/DRAFT.md` — the interview protocol. It
   wins over this file wherever they differ.
2. Pick the template. The four that exist, as reference files under
   `${CLAUDE_PLUGIN_ROOT}/docs/templates/`: `status-update`, `board-memo`,
   `postmortem`, `risk-register`. Load only the one in play.
   - An out-of-scope request (investor update, decision memo, OKR
     check-in) never silently gets the nearest template. Either name the
     mapping out loud — "I'll use the board memo shape for this" — and
     proceed on agreement, or run a generic interview from the
     always-applicable rules: recommendation first (5.1), one owner and
     one date per action (5.4), numbers with baselines and denominators
     (8.x), tagged judgment (9.2).
3. Check the working directory for `bluf-draft-<template>.json`. If it
   exists, resume: one-line summary of what it holds, then the first open
   required field. Otherwise start the interview in the template's field
   order — the recommendation is always asked last and placed first.
   - **Seed material** (notes, a prior update, a pasted thread in the
     invocation): extract what it already answers per DRAFT.md's seed
     rules — never upgraded beyond what the source states — show the
     filled sheet for confirmation, and interview only the open fields.
     A skill that answers "here are my notes" with question 1 of 14 gets
     abandoned; the first thing the user sees is what they already told
     you.
4. Ask per the protocol: facts free-text, AskUserQuestion only for the
   closed sets, one re-ask for a refusal ("A named person, or shall I
   list the owner in Gaps?"), then Gaps. Write the answer sheet after
   every answer. Offer "assemble now with what I have" at every turn.
5. Assemble when asked or when the fields run out, if the required floor
   is met:
   - Fill the template's skeleton from the sheet. Every name, date, and
     number in the document comes from an answer — no other source.
   - Open and refused fields become the document's Gaps section, in the
     marked-unknown convention from FINDINGS.md.
   - A named owner who is not the document's author gets a confirm flag:
     "(confirm with Priya before sending)".
   - Below the floor: no document — list the open required fields
     instead.
6. Self-check the assembled document with the checker:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/see100_check.py" <tempfile>
   ```
   The bar is gaps-aware: every error not covered by a Gaps entry gets
   fixed before presenting. Findings covered by Gaps stay — the honest
   document beats the clean-looking one.

## Non-interactive mode

When the invocation itself supplies answers (inline text or a file path),
or the session cannot ask (agent callers, `claude -p`): run single-shot
per the protocol — parse the supplied answers into the sheet, print the
numbered questions for every open field, assemble if the floor is met,
Gaps as always. Never invent an answer to fill a hole.

If the request contains "emit draft JSON", append one fenced `json` block
in the DRAFT.md schema. No prose inside the block, and nothing after it —
the block is always the last thing in the response.

## Failure behavior

If `${CLAUDE_PLUGIN_ROOT}/docs/DRAFT.md` or the template file cannot be
read: stop and report the exact path that failed. Never interview from
memory of the protocol.
