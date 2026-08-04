"""Unit tests for the triage grading logic in scripts/grade.py.

Each test seeds a defect a correct grader must catch, or a correct payload
it must pass — the harness is graded before it grades anything. Matching
semantics under test are specified in bluf/tests/triage/README.md; the
B*/S* names track the Phase 4 review findings they regress.
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

THREAD_DOC = """From: Marco
Date: Fri, Jul 18
Subject: churn

I'll send the breakdown by Jul 31.
"""

THREAD_GOLD = {
    "is_thread": True,
    "facts": [
        {"type": "commitment", "owner": "Marco", "date": "Jul 31",
         "speaker": "Marco", "message_date": "Jul 18",
         "quote_contains": "breakdown by Jul 31", "provenance": "stated"},
    ],
}


def make_md(doc):
    return type("FakeMd", (), {"name": "fake.md",
                               "read_text": lambda self: doc})()


def run(payload, gold=GOLD, doc=DOC):
    errors = []
    grade.grade_triage_run(make_md(doc), gold, payload, errors)
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
        bad = dict(GOOD_FACTS[1], owner="Dana")
        payload = dict(GOOD_PAYLOAD, facts=[GOOD_FACTS[0], bad])
        errors = run(payload)
        self.assertTrue(any("gold fact missed" in e for e in errors))
        self.assertTrue(any("unsupported" in e for e in errors))

    def test_b1_allowed_match_does_not_skip_grounding(self):
        gold = {"facts": [], "allowed_facts": [
            {"type": "commitment", "quote_contains": "confirm by Friday"}]}
        bad = {"type": "commitment", "owner": "Sam",
               "quote": "I'll confirm by Friday", "provenance": "stated"}
        payload = {"verdict": "v", "facts": [bad], "gaps": [],
                   "questions": []}
        self.assertTrue(any("owner='Sam'" in e and "unsupported" in e
                            for e in run(payload, gold)))

    def test_b2_wildcard_does_not_license_invented_fields(self):
        gold = {"facts": [], "allowed_facts": [
            {"type": "*", "quote_contains": "*"}]}
        bad = {"type": "decision", "decider": "Marco", "date": "Dec 25",
               "quote": "The cutover is Oct 2", "provenance": "stated"}
        payload = {"verdict": "v", "facts": [bad], "gaps": [],
                   "questions": []}
        errors = run(payload, gold)
        self.assertTrue(any("decider='Marco'" in e for e in errors))
        self.assertTrue(any("date='Dec 25'" in e for e in errors))

    def test_b3_contradiction_needs_actual_quotes(self):
        doc = ("Dana wrote: done by Aug 15. Later Dana wrote: realistically "
               "early September.")
        gold = {"facts": [], "contradictions_must_include": [
            {"about_contains": "date", "quotes_contain": ["Aug 15"]}]}
        base = {"verdict": "v", "facts": [], "gaps": [], "questions": []}
        # Narrating the conflict in `about` while quoting nothing must fail.
        narrated = dict(base, contradictions=[
            {"about": "date slip: Aug 15 vs early September", "quotes": []}])
        self.assertTrue(any("contradiction missed" in e
                            for e in run(narrated, gold, doc)))
        quoted = dict(base, contradictions=[
            {"about": "the date", "quotes": ["done by Aug 15",
                                            "early September"]}])
        self.assertEqual(run(quoted, gold, doc), [])

    def test_b3_contradiction_quotes_must_be_verbatim(self):
        gold = {"facts": []}
        payload = {"verdict": "v", "facts": [], "gaps": [], "questions": [],
                   "contradictions": [{"about": "x",
                                       "quotes": ["never said this"]}]}
        self.assertTrue(any("not verbatim" in e for e in run(payload, gold)))

    def test_b4_invented_fact_type_fails(self):
        bad = {"type": "action_item",
               "quote": "A rollback plan will be written before the cutover",
               "provenance": "stated"}
        payload = dict(GOOD_PAYLOAD, facts=GOOD_FACTS + [bad])
        self.assertTrue(any("invented fact type" in e for e in run(payload)))

    def test_b5_gap_slot_vocabulary_is_closed(self):
        gaps = GOOD_PAYLOAD["gaps"] + [
            {"rank": 2, "missing": "deadline", "about": "the cutover"}]
        payload = dict(GOOD_PAYLOAD, gaps=gaps)
        self.assertTrue(any("outside the vocabulary" in e
                            for e in run(payload)))

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

    def test_s1_false_gap_trap_ignores_the_quote(self):
        # The gap is about the rollback plan; its quote happens to contain
        # the word "cutover". The strict trap (about-only) must not fire.
        gaps = [{"rank": 1, "missing": "owner", "about": "the rollback plan",
                 "quote": "A rollback plan will be written before the "
                          "cutover"}]
        payload = dict(GOOD_PAYLOAD, gaps=gaps)
        self.assertEqual(run(payload), [])

    def test_s2_neighbouring_sentence_does_not_ground(self):
        # "Oct 2" sits in the other sentence on the same line as the quote.
        bad = {"type": "number", "value": "Oct 2",
               "quote": "Checkout latency fell 38%", "provenance": "stated"}
        payload = dict(GOOD_PAYLOAD, facts=GOOD_FACTS + [bad])
        self.assertTrue(any("value='Oct 2'" in e and "unsupported" in e
                            for e in run(payload)))

    def test_s3_first_person_resolution_grounds(self):
        fact = {"type": "commitment", "owner": "Marco", "date": "Jul 31",
                "speaker": "Marco", "message_date": "Jul 18",
                "quote": "I'll send the breakdown by Jul 31.",
                "provenance": "stated"}
        payload = {"verdict": "v", "facts": [fact], "gaps": [],
                   "questions": []}
        self.assertEqual(run(payload, THREAD_GOLD, THREAD_DOC), [])

    def test_s3_first_person_needs_the_real_speaker(self):
        fact = {"type": "commitment", "owner": "Sam", "date": "Jul 31",
                "speaker": "Sam", "message_date": "Jul 18",
                "quote": "I'll send the breakdown by Jul 31.",
                "provenance": "stated"}
        payload = {"verdict": "v", "facts": [fact], "gaps": [],
                   "questions": []}
        errors = run(payload, THREAD_GOLD, THREAD_DOC)
        self.assertTrue(any("owner='Sam'" in e for e in errors))

    def test_s4_missing_rank_fails_without_crashing(self):
        gaps = [{"rank": 1, "missing": "owner", "about": "the rollback plan"},
                {"missing": "date", "about": "x"}]
        payload = dict(GOOD_PAYLOAD, gaps=gaps)
        self.assertTrue(any("budget" in e for e in run(payload)))

    def test_s5_gap_missing_matches_case_insensitively(self):
        self.assertTrue(grade.gap_matches(
            {"missing": "owner", "about": "the rollback plan"},
            {"missing": "Owner", "about_contains": "rollback"}))

    def test_s6_gap_quote_must_be_verbatim(self):
        gaps = [{"rank": 1, "missing": "owner", "about": "the rollback plan",
                 "quote": "a quote that is not in the document"}]
        payload = dict(GOOD_PAYLOAD, gaps=gaps)
        self.assertTrue(any("not verbatim" in e for e in run(payload)))

    def test_s7_null_field_is_a_contract_failure(self):
        bad = dict(GOOD_FACTS[1], owner=None)
        payload = dict(GOOD_PAYLOAD, facts=[GOOD_FACTS[0], bad])
        self.assertTrue(any("null field" in e for e in run(payload)))

    def test_s8_calendar_date_regex(self):
        caught = ["Sep 4", "Sept 4", "Sep. 4", "September 4", "4 Sep",
                  "4 September", "15th of September", "2026-09-04",
                  "2026-09", "09/04"]
        for s in caught:
            self.assertTrue(grade.CALENDAR_DATE.search(s), s)
        missed = ["decided 3", "declined 2", "marked 4", "separate 2",
                  "augmented 3", "junior 2", "next month", "Friday"]
        for s in missed:
            self.assertFalse(grade.CALENDAR_DATE.search(s), s)

    def test_s9_inferred_requires_inference(self):
        bad = {"type": "claimed_state", "quote": "The cutover is Oct 2",
               "provenance": "inferred"}
        payload = dict(GOOD_PAYLOAD, facts=GOOD_FACTS + [bad])
        self.assertTrue(any("inference" in e for e in run(payload)))

    def test_missing_verdict_fails(self):
        payload = {k: v for k, v in GOOD_PAYLOAD.items() if k != "verdict"}
        self.assertTrue(any("verdict" in e for e in run(payload)))

    def test_missing_gold_gap_fails(self):
        payload = dict(GOOD_PAYLOAD, gaps=[], questions=[])
        self.assertTrue(any("gold gap missed" in e for e in run(payload)))

    def test_invented_gap_on_compliant_doc_fails(self):
        gold = {"facts": [], "gaps_must_be_empty": True}
        payload = {"verdict": "v", "facts": [],
                   "gaps": [{"rank": 1, "missing": "owner",
                             "about": "anything"}], "questions": []}
        self.assertTrue(any("invented" in e for e in run(payload, gold)))

    def test_unsurfaced_relative_date_fails(self):
        payload = dict(GOOD_PAYLOAD, unresolved_dates=[])
        self.assertTrue(any("not surfaced" in e for e in run(payload)))

    def test_no_resolved_dates_catches_calendar_date(self):
        gold = {"facts": [], "no_resolved_dates": True}
        payload = {"verdict": "The pilot opens on Sep 4.", "facts": [],
                   "gaps": [], "questions": []}
        self.assertTrue(any("calendar date" in e for e in run(payload, gold)))
        clean = {"verdict": "Every date is relative; none can resolve.",
                 "facts": [], "gaps": [], "questions": []}
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
        payload = dict(GOOD_PAYLOAD,
                       verdict="Per SEE100 the plan has no owner.")
        self.assertTrue(any("rule number" in e for e in run(payload)))

    def test_thread_attribution_required(self):
        fact = {"type": "commitment", "owner": "Marco", "date": "Jul 31",
                "quote": "I'll send the breakdown by Jul 31.",
                "provenance": "stated"}
        payload = {"verdict": "v", "facts": [fact], "gaps": [],
                   "questions": []}
        self.assertTrue(any("speaker/message_date" in e
                            for e in run(payload, THREAD_GOLD, THREAD_DOC)))

    def test_skipped_required_when_budget_bites(self):
        gold = {"facts": [], "skipped_must_be_nonempty": True}
        payload = {"verdict": "v", "facts": [], "gaps": [], "questions": []}
        self.assertTrue(any("skipped" in e for e in run(payload, gold)))

    def test_verdict_regex(self):
        gold = {"facts": [], "verdict_regex": r"(?i)\bno\b"}
        payload = {"verdict": "Everything needed is stated.", "facts": [],
                   "gaps": [], "questions": []}
        self.assertTrue(any("verdict fails" in e for e in run(payload, gold)))


if __name__ == "__main__":
    unittest.main()
