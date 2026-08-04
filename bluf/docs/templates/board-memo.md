# Template: board-memo

Linear interview. The decision sought is the spine; everything else
supports it. Recommendation asked last, placed first.

## Fields

| id | tier | type | prompt |
|---|---|---|---|
| decision_sought | required | free | What decision do you need from the board, in one sentence? |
| deadline | required | free | By what date must the board decide, and what happens if it does not? |
| context | required | free | The two or three facts the board must know to decide. Numbers with baselines and denominators. |
| options | optional | free | Which options did you consider, and why did you reject the others? One sentence each. |
| cost | required | free | What does the recommended path cost — money, people, time — as numbers? |
| risks | optional | free | What can go wrong with the recommendation? Trigger, consequence, cost, mitigation owner. |
| tag | required | closed: fact / estimate / opinion | For each interpretive claim you gave: which tag? |
| recommendation | required | free | Your recommendation, one sentence, decisive. This opens the memo. |

## Skeleton

```
# {title} — Board Memo

{recommendation} {decision_sought framed as the ask: named body, date}

## Why

{context — tagged fact/estimate/opinion where interpretive}

## Cost

{cost}

## Options considered

{options — or omit the section}

## Risks

{RISK/BLOCKER form — or omit the section}

## Gaps

{marked-unknown convention — omit only when empty}
```
