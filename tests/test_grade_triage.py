"""Unit tests for the triage grading logic in scripts/grade.py.

Each test seeds a defect a correct grader must catch, or a correct payload
it must pass — the harness is graded before it grades anything.
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import grade

DOC = """From: Dana
Date: Jul 20
Subject: migration

The cutover is Oct 2. Checkout latency fell 38%, from 210ms to 130ms.
Someone still needs to own the rollback plan. I'll confirm by Friday.
"""

GOLD = {
    "facts": [
        {"type": "number", "value": "38%", "baseline": "210ms",
         "quote_contains": "fell 38%"},
        {"type": "commitment", "date": "Friday",
         "quote_contains": "confirm by Friday",
         "must_not_have": {"owner": "Dana"}},
    ],
    "allowed_facts": [],
    "gaps_must_include": [{"missing": "owner", "about_contains": "rollback"}],
    "false_gap_traps": [{"missing": "date", "about_contains": "cutover"}],
    "unresolved_must_include": ["Friday"],
}

GOOD_FACTS = [
    {"type": "number", "value": "38%", "baseline": "from 210ms to 130ms",
     "quote": "Checkout latency fell 38%, from 210ms to 130ms",
     "provenance": "stated"},
    {"type": "commitment", "date": "Friday",
     "quote": "I'll confirm by Friday", "provenance": "stated"},
]

GOOD_PAYLOAD = {
    "facts": GOOD_FACTS,
    "gaps": [{"rank": 1, "missing": "owner", "about": "the rollback plan",
              "quote": "Someone still needs to own the rollback plan"}],
    "unresolved_dates": [{"quote": "by Friday",
                          "reason": "no year anchor for the send date"}],
}


class FakeMd:
    name = "fake.md"

    def read_text(self):
        return DOC


def run(payload, gold=GOLD):
    errors = []
    grade.grade_triage_run(FakeMd(), gold, payload, errors)
    return errors


class TestTriageGrading(unittest.TestCase):
    def test_good_payload_passes(self):
        self.assertEqual(run(GOOD_PAYLOAD), [])

    def test_missed_gold_fact_fails_recall(self):
        payload = dict(GOOD_PAYLOAD, facts=[GOOD_FACTS[0]])
        self.assertTrue(any("gold fact missed" in e for e in run(payload)))

    def test_fabricated_quote_is_hard_fail(self):
        bad = dict(GOOD_FACTS[0], quote="latency dropped 38 percent")
        payload = dict(GOOD_PAYLOAD, facts=[bad, GOOD_FACTS[1]])
        self.assertTrue(any("fabricated" in e for e in run(payload)))

    def test_ungrounded_owner_is_hard_fail(self):
        bad = dict(GOOD_FACTS[1], owner="Marco")
        payload = dict(GOOD_PAYLOAD, facts=[GOOD_FACTS[0], bad])
        self.assertTrue(any("owner='Marco'" in e or "owner=Marco" in e
                            for e in run(payload)))

    def test_sender_as_owner_trips_banned_inference(self):
        # Dana IS in the document (the From: line) so grounding passes,
        # but the gold trap forbids crediting the sender as owner.
        bad = dict(GOOD_FACTS[1], owner="Dana")
        payload = dict(GOOD_PAYLOAD, facts=[GOOD_FACTS[0], bad])
        self.assertTrue(any("banned inference" in e for e in run(payload)))

    def test_false_gap_is_fabrication(self):
        gaps = GOOD_PAYLOAD["gaps"] + [
            {"rank": 2, "missing": "date", "about": "the cutover"}]
        payload = dict(GOOD_PAYLOAD, gaps=gaps)
        self.assertTrue(any("false gap" in e for e in run(payload)))

    def test_missing_gold_gap_fails(self):
        payload = dict(GOOD_PAYLOAD, gaps=[])
        self.assertTrue(any("gold gap missed" in e for e in run(payload)))

    def test_invented_gap_on_compliant_doc_fails(self):
        gold = {"facts": [], "gaps_must_be_empty": True}
        payload = {"facts": [], "gaps": [{"rank": 1, "missing": "owner",
                                          "about": "anything"}]}
        self.assertTrue(any("invented" in e for e in run(payload, gold)))

    def test_unsurfaced_relative_date_fails(self):
        payload = dict(GOOD_PAYLOAD, unresolved_dates=[])
        self.assertTrue(any("not surfaced" in e for e in run(payload)))

    def test_budget_cap_fails_on_13_facts(self):
        filler = [dict(GOOD_FACTS[0]) for _ in range(13)]
        payload = dict(GOOD_PAYLOAD, facts=filler)
        self.assertTrue(any("budget" in e for e in run(payload)))

    def test_contradiction_recall(self):
        gold = {"facts": [], "contradictions_must_include": [
            {"about_contains": "date", "quotes_contain": ["Aug 15"]}]}
        payload = {"facts": [], "contradictions": []}
        self.assertTrue(any("contradiction missed" in e
                            for e in run(payload, gold)))
        payload = {"facts": [], "contradictions": [
            {"about": "migration date", "quotes": ["done by Aug 15", "later"],
             "speakers": ["Dana", "Dana"]}]}
        self.assertEqual(run(payload, gold), [])


if __name__ == "__main__":
    unittest.main()
