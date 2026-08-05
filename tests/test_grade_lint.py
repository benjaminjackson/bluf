"""Unit tests for the lint grading logic in scripts/grade.py.

Covers the gaps-aware `acknowledged` pin on must_find / must_not_find
entries — the harness is graded before it grades anything. Matching
semantics are specified in bluf/tests/README.md and FINDINGS.md
("Gaps-aware mode").
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import grade

DOC = "- OWNER: write the rollback plan by Aug 11.\n"

ACKED = {"rule": "5.4", "layer": "judgment", "acknowledged": True,
         "quote": "OWNER: write the rollback plan by Aug 11."}
PLAIN = {"rule": "5.4", "layer": "judgment",
         "quote": "OWNER: write the rollback plan by Aug 11."}


class TestAcknowledgedMatching(unittest.TestCase):
    def test_spec_without_acknowledged_ignores_the_flag(self):
        spec = {"rule": "5.4"}
        self.assertTrue(grade.matches(DOC, ACKED, spec))
        self.assertTrue(grade.matches(DOC, PLAIN, spec))

    def test_true_pin_needs_the_flag(self):
        spec = {"rule": "5.4", "acknowledged": True}
        self.assertTrue(grade.matches(DOC, ACKED, spec))
        self.assertFalse(grade.matches(DOC, PLAIN, spec))

    def test_false_pin_rejects_the_flag(self):
        spec = {"rule": "5.4", "acknowledged": False}
        self.assertFalse(grade.matches(DOC, ACKED, spec))
        self.assertTrue(grade.matches(DOC, PLAIN, spec))

    def test_wildcard_rule_still_honours_the_pin(self):
        spec = {"rule": "*", "acknowledged": True}
        self.assertTrue(grade.matches(DOC, ACKED, spec))
        self.assertFalse(grade.matches(DOC, PLAIN, spec))

    def test_pin_combines_with_quote_overlap(self):
        spec = {"rule": "5.4", "acknowledged": True,
                "quote": "write the rollback plan"}
        self.assertTrue(grade.matches(DOC, ACKED, spec))
        spec["quote"] = "run the load test"
        self.assertFalse(grade.matches(DOC, ACKED, spec))

    def test_deterministic_findings_never_match_any_pin(self):
        det = {"rule": "5.4", "layer": "deterministic", "quote": "OWNER:"}
        self.assertFalse(grade.matches(DOC, det,
                                       {"rule": "5.4", "acknowledged": True}))
        # A false pin means "an UNACKNOWLEDGED JUDGMENT finding" — a det
        # finding must not satisfy it either.
        self.assertFalse(grade.matches(DOC, det,
                                       {"rule": "5.4",
                                        "acknowledged": False}))


class TestGapsFixturePair(unittest.TestCase):
    """The honest and dishonest fixtures must differ only by the Gaps
    section, so the acknowledged classification is the single variable."""

    def test_bodies_are_identical(self):
        corpus = REPO / "bluf" / "tests"
        honest = (corpus / "gaps-honest.md").read_text()
        dishonest = (corpus / "gaps-dishonest.md").read_text()
        mismatched = (corpus / "gaps-mismatched.md").read_text()
        self.assertIn("## Gaps", honest)
        self.assertNotIn("## Gaps", dishonest)
        self.assertIn("## Gaps", mismatched)
        body = dishonest.strip()
        self.assertEqual(honest.split("## Gaps")[0].strip(), body)
        self.assertEqual(mismatched.split("## Gaps")[0].strip(), body)
        # The mismatched Gaps section covers the date item only — the
        # owner item stays uncovered, which is the coverage discriminator.
        self.assertIn("Date for the load test", mismatched)
        self.assertNotIn("Owner for the rollback plan", mismatched)


if __name__ == "__main__":
    unittest.main()
