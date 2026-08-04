# Quarterly Operations Review — Platform Group

Dateline: Sep 30

## Summary

The quarter closed with the migration finished, hiring behind plan, and one open vendor question. Three items need a decision in October. The rest of this report is background for the people who want it.

## Delivery

The service migration finished on Sep 22, eight days ahead of the Sep 30 target. Marco led the cutover and the on-call rotation held through it without an extra page.

Two services stayed on the old cluster by design: the billing exporter and the internal admin console. Neither is on the critical path. Sam moves both by Nov 14.

Deploy frequency rose from 11 per week to 26 per week across the quarter. The change failure rate held at 4%, unchanged from the quarter before. Mean time to restore fell from 71 minutes to 38 minutes.

Priya decided on Sep 8 to freeze schema changes until the migration closed. The freeze lifted on Sep 22 as planned, and the backlog of held migrations cleared in two days.

Routine notes from delivery: the weekly release train ran on schedule every week, the staging environment was rebuilt once after a disk issue, and the runbook index moved into the platform wiki.

## Hiring

We planned six hires and made three: two backend engineers and one site reliability engineer. Two offers were declined at the salary stage and one search is still open.

Time to offer averaged 41 days against a 30-day target. Recruiting screens were not the bottleneck; the panel debrief step was, and it slipped by a week in four of the nine loops.

Dana owns the revised hiring plan and presents it on Oct 9.

Onboarding for the three new people finished on time. Buddy assignments, laptop provisioning, and access requests all ran through the standard checklist without exception.

## Infrastructure

Compute spend was $184,000 for the quarter, up from $161,000 the quarter before. Most of the increase is the dual-running cost during the migration, and that cost ends in October.

Storage spend was flat. Network egress rose slightly and is not material.

The contract with the log vendor renews on Dec 1. We discussed switching to in-house storage and did not settle it.

RISK: Priya owns this one — if the log vendor renewal is not decided by Nov 1, the contract auto-renews for twelve months at $240,000.

## Customer impact

Support tickets fell from 340 per month to 295 per month over the quarter. First-response time was steady.

Two enterprise accounts escalated during the cutover window. Both closed without a credit. Alex writes the postmortem for those escalations by Oct 17.

Customer satisfaction is trending in the right direction and the qualitative feedback has been encouraging.

## Open items for October

1. The log vendor renewal.
2. The revised hiring plan.
3. Whether the billing exporter move waits for the Q4 freeze.

## Appendix A — minor figures

- On-call pages: 214 this quarter, 231 the quarter before.
- Documentation pages updated: 96.
- Average pull request review time: 6.2 hours, down from 7.1 hours.
- Test suite runtime: 18 minutes, up from 14 minutes.
- Third-party API error rate: 0.3%, unchanged.
- Internal tooling tickets closed: 87.

## Appendix B — process notes

The quarterly review template changed slightly this cycle. The delivery and infrastructure sections now lead, and the narrative summary is shorter. Feedback on the format goes to Sam.

Meeting hygiene held up. The weekly platform sync kept to 30 minutes in eleven of thirteen weeks. The architecture review met twice and produced written notes both times.

The team retro raised two themes: too many interrupts during the cutover window, and unclear ownership of the shared staging environment. Both are on the agenda for the October offsite.
