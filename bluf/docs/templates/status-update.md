# Template: status-update

Linear interview. Ask in this order; the recommendation is last asked,
first placed.

## Fields

| id | tier | type | prompt |
|---|---|---|---|
| period | required | free | What period does this update cover, and what is today's date for the reader? |
| state | required | closed: on track / at risk / off track | Which of the three states is this work in? |
| results | required | free | What changed this period? Results, not activity — each with its number, and each number with its baseline. |
| risks | optional | free | Any risks? For each: what triggers it, what it costs, who mitigates it, by when. |
| risk_severity | optional | closed: RISK / BLOCKER | For each risk named: could-miss (RISK) or will-miss-without-intervention (BLOCKER)? |
| asks | optional | free | What do you need from the reader? One ask at a time: the action, the named person, the date. |
| next_checkpoint | required | free | When is the next update or checkpoint, as a real date? |
| recommendation | required | free | In one sentence: what should the reader know or do? This goes first in the document. |

## Skeleton

```
# {title} — Status

{recommendation}

**State: {state}.** {period}

## Results

{results — one sentence per result, number + baseline each}

## Risks

{RISK/BLOCKER: trigger, consequence, cost, mitigation owner — or omit the section}

## Asks

{one per line: imperative, named person, date — or omit the section}

Next checkpoint: {next_checkpoint}.

## Gaps

{open and refused fields, marked-unknown convention — omit only when empty}
```
