"""Unit tests for the triage grading logic in scripts/grade.py.

Each test seeds a defect a correct grader must catch, or a correct payload
it must pass — the harness is graded before it grades anything. Matching
semantics under test are specified in bluf/tests/triage/README.md.
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
A rollback plan will be written before the cutover. I'll confirm by Friday.
"""

GOLD = {
    "is_thread": False,
    "facts": [
        {"type": "number", "value": "38%", "baseline": "210ms",
         "quote_contains": "fell 38%"},
        {"type": "commitment", "date": "Friday",
         "quote_contains": "confirm by Friday",
         "must_not_have": ["owner"]},
    ],
    "allowed_facts": [
        {"type": "claimed_state", "quote_contains": "cutover is Oct 2"},
    ],
    "must_not_extract": [
        {"type": "decision", "quote_contains": "cutover"},
    ],
    "gaps_must_include": [{"missing": "owner", "about_contains": "rollback"}],
    "gaps_must_not_include": [
        {"missing": "date", "about_contains": "cutover"}],
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
    "verdict": "One number with its baseline; the rollback plan has no owner.",
    "facts": GOOD_FACTS,
    "gaps": [{"rank": 1, "missing": "owner", "about": "the rollback plan",
              "quote": "A rollback plan will be written before the cutover"}],
    "questions": ["Who owns the rollback plan?"],
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

    def test_sender_as_owner_is_caught_twice(self):
        # Dana IS in the document (the From: line) but not in the sentence
        # holding the quote. The fact stops matching gold (must_not_have),
        # so recall fails AND the grounding check flags the owner.
        bad = dict(GOOD_FACTS[1], owner="Dana")
        payload = dict(GOOD_PAYLOAD, facts=[GOOD_FACTS[0], bad])
        errors = run(payload)
        self.assertTrue(any("gold fact missed" in e for e in errors))
        self.assertTrue(any("unsupported by its own sentence" in e
                            for e in errors))

    def test_invented_type_over_real_quote_fails(self):
        bad = {"type": "decision", "quote": "The cutover is Oct 2",
               "provenance": "stated"}
        payload = dict(GOOD_PAYLOAD, facts=GOOD_FACTS + [bad])
        self.assertTrue(any("must not exist" in e for e in run(payload)))

    def test_false_gap_is_fabrication(self):
        gaps = GOOD_PAYLOAD["gaps"] + [
            {"rank": 2, "missing": "date", "about": "the cutover"}]
        payload = dict(GOOD_PAYLOAD, gaps=gaps)
        self.assertTrue(any("false gap" in e for e in run(payload)))

    def test_missing_gold_gap_fails(self):
        payload = dict(GOOD_PAYLOAD, gaps=[], questions=[])
        self.assertTrue(any("gold gap missed" in e for e in run(payload)))

    def test_invented_gap_on_compliant_doc_fails(self):
        gold = {"facts": [], "gaps_must_be_empty": True}
        payload = {"facts": [], "gaps": [{"rank": 1, "missing": "owner",
                                          "about": "anything"}]}
        self.assertTrue(any("invented" in e for e in run(payload, gold)))

    def test_unsurfaced_relative_date_fails(self):
        payload = dict(GOOD_PAYLOAD, unresolved_dates=[])
        self.assertTrue(any("not surfaced" in e for e in run(payload)))

    def test_no_resolved_dates_catches_calendar_date(self):
        gold = {"facts": [], "no_resolved_dates": True}
        payload = {"facts": [], "gaps": [], "questions": [],
                   "verdict": "The pilot opens on Sep 4."}
        self.assertTrue(any("calendar date" in e for e in run(payload, gold)))
        clean = {"facts": [], "gaps": [], "questions": [],
                 "verdict": "Every date is relative; none can resolve."}
        self.assertEqual(run(clean, gold), [])

    def test_budget_caps(self):
        payload = dict(GOOD_PAYLOAD, facts=[GOOD_FACTS[0]] * 13)
        self.assertTrue(any("budget is 12" in e for e in run(payload)))
        gaps = [{"rank": 1, "missing": "owner", "about": "the rollback plan"},
                {"rank": 1, "missing": "date", "about": "x"}]
        payload = dict(GOOD_PAYLOAD, gaps=gaps)
        self.assertTrue(any("unique" in e for e in run(payload)))

    def test_rule_number_in_output_fails(self):
        payload = dict(GOOD_PAYLOAD,
                       verdict="Rule 5.4: the rollback plan has no owner.")
        self.assertTrue(any("rule number" in e for e in run(payload)))

    def test_thread_attribution_required(self):
        gold = {"is_thread": True, "facts": []}
        payload = {"facts": [{"type": "number", "value": "38%",
                              "quote": "Checkout latency fell 38%"}],
                   "gaps": [], "questions": []}
        self.assertTrue(any("speaker/message_date" in e
                            for e in run(payload, gold)))

    def test_skipped_required_when_budget_bites(self):
        gold = {"facts": [], "skipped_must_be_nonempty": True}
        payload = {"facts": [], "gaps": [], "questions": []}
        self.assertTrue(any("skipped" in e for e in run(payload, gold)))

    def test_verdict_regex(self):
        gold = {"facts": [], "verdict_regex": r"(?i)\bno\b"}
        payload = {"facts": [], "gaps": [], "questions": [],
                   "verdict": "Everything needed is stated."}
        self.assertTrue(any("verdict fails" in e for e in run(payload, gold)))

    def test_contradiction_recall(self):
        gold = {"facts": [], "contradictions_must_include": [
            {"about_contains": "date", "quotes_contain": ["Aug 15"]}]}
        payload = {"facts": [], "gaps": [], "questions": [],
                   "contradictions": []}
        self.assertTrue(any("contradiction missed" in e
                            for e in run(payload, gold)))
        payload = dict(payload, contradictions=[
            {"about": "migration date", "quotes": ["done by Aug 15", "later"],
             "speakers": ["Dana", "Dana"]}])
        self.assertEqual(run(payload, gold), [])


if __name__ == "__main__":
    unittest.main()
