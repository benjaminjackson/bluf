# Template: risk-register

A loop, not a linear interview. Nine risks must not mean 36 sequential
questions.

## Flow

1. **Batch-collect titles first.** One free-text prompt: "List every risk
   as a short title, one per line — or paste your existing notes and I'll
   parse them." Free-text bulk entry is parsed into titles; anything in
   the paste that already answers a Rule 7.2 slot (trigger, consequence,
   cost, owner) is pre-filled into the sheet and shown for confirmation,
   never silently upgraded.
2. **Per-risk form, batched by slot.** For risks still missing slots, ask
   per risk in one compact prompt: "For 'vendor API slips': what triggers
   it, what is the consequence and cost, who mitigates it?" One prompt
   per risk, not one per slot.
3. **Severity is closed.** RISK vs BLOCKER via AskUserQuestion, batched.
4. Refusals and unknowns per protocol: one re-ask, then Gaps.

## Fields (per risk)

| id | tier | type | prompt |
|---|---|---|---|
| title | required | free | (from the batch) |
| trigger | required | free | What has to happen for this risk to fire? |
| consequence | required | free | What happens then — with the cost as a number where one exists? |
| owner | required | free | Who mitigates it? One name. |
| mitigation_date | required | free | By when — a real date? |
| severity | required | closed: RISK / BLOCKER | Could-miss or will-miss-without-intervention? |

## Skeleton

```
# Risk Register — {scope}

{one line: N risks, M of them BLOCKERs, next review date}

| Severity | Risk | Trigger | Consequence / cost | Mitigation owner | Date |
|---|---|---|---|---|---|
{one row per risk}

## Gaps

{risks with open slots, marked-unknown convention — omit only when empty}
```
