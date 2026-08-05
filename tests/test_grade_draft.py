"""Unit tests for the draft grading logic in scripts/grade.py.

Each test seeds a defect a correct grader must catch, or a correct payload
it must pass. Semantics: bluf/tests/draft/README.md.
"""
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import grade

PERSONA = {
    "template": "status-update",
    "given": {
        "state": "at risk",
        "results": "Latency fell from 210ms to 130ms after the Aug 5 change.",
        "asks": "The team should pick up the rollback plan soon.",
        "recommendation": "Hold the launch until the rollback plan lands.",
    },
    "must_ask": ["next_checkpoint"],
    "question_ceiling": 3,
    "expect_document": True,
    "bluf_must_contain": "Hold the launch",
    "gaps_must_mention": ["owner"],
    "allowed_terms": ["Gaps", "Results", "Asks"],
}

GOOD_PAYLOAD = {
    "template": "status-update",
    "questions": [{"field": "next_checkpoint",
                   "prompt": "When is the next checkpoint?"}],
    "answers_used": {"state": "at risk"},
    "document": ("# Status\n\nHold the launch until the rollback plan "
                 "lands.\n\n**State: at risk.** Latency fell from 210ms to "
                 "130ms after the Aug 5 change.\n\n## Gaps\n\n- Owner for "
                 "the rollback plan: not yet assigned.\n"),
    "gaps": [{"field": "asks", "missing": "owner",
              "reason": "refused: 'the team'"}],
}


class FakePersona:
    name = "fake.persona.json"
    stem = "fake.persona"


def run(payload, persona=PERSONA):
    errors = []
    grade.grade_draft_run(FakePersona(), persona, payload, errors)
    return errors


class TestDraftGrading(unittest.TestCase):
    def test_good_payload_passes(self):
        self.assertEqual(run(GOOD_PAYLOAD), [])

    def test_unasked_required_field_fails(self):
        payload = dict(GOOD_PAYLOAD, questions=[])
        self.assertTrue(any("never asked" in e for e in run(payload)))

    def test_question_ceiling(self):
        qs = [{"field": f"f{i}", "prompt": "?"} for i in range(4)]
        payload = dict(GOOD_PAYLOAD, questions=qs)
        self.assertTrue(any("ceiling" in e for e in run(payload)))

    def test_bluf_must_open_the_document(self):
        doc = GOOD_PAYLOAD["document"].replace(
            "Hold the launch until the rollback plan lands.",
            "Things are moving.")
        payload = dict(GOOD_PAYLOAD, document=doc + "\nHold the launch "
                                                    "until it lands.")
        self.assertTrue(any("first line" in e for e in run(payload)))

    def test_missing_document_fails_when_floor_met(self):
        payload = dict(GOOD_PAYLOAD, document=None)
        self.assertTrue(any("no document" in e for e in run(payload)))

    def test_document_below_floor_fails(self):
        persona = dict(PERSONA, expect_document=False)
        self.assertTrue(any("below the required floor" in e
                            for e in run(GOOD_PAYLOAD, persona)))

    def test_gap_mention_required(self):
        payload = dict(GOOD_PAYLOAD, gaps=[])
        self.assertTrue(any("never mention" in e for e in run(payload)))

    def test_laundered_owner_fails_the_trace(self):
        # "the team" was refused; a named owner from nowhere is fabrication.
        doc = GOOD_PAYLOAD["document"].replace(
            "Owner for the rollback plan: not yet assigned.",
            "The rollback plan is owned by Marco.")
        payload = dict(GOOD_PAYLOAD, document=doc)
        self.assertTrue(any("fabricated 'Marco'" in e for e in run(payload)))

    def test_invented_number_fails_the_trace(self):
        doc = GOOD_PAYLOAD["document"] + "\nThroughput rose 47%.\n"
        payload = dict(GOOD_PAYLOAD, document=doc)
        self.assertTrue(any("fabricated '47" in e for e in run(payload)))

    def test_invented_date_fails_the_trace(self):
        doc = GOOD_PAYLOAD["document"] + "\nNext checkpoint is Sep 9.\n"
        payload = dict(GOOD_PAYLOAD, document=doc)
        self.assertTrue(any("fabricated" in e and "9" in e
                            for e in run(payload)))

    def test_personas_parse_and_reference_real_templates(self):
        corpus = REPO / "bluf" / "tests" / "draft"
        personas = list(corpus.glob("*.persona.json"))
        self.assertEqual(len(personas), 3)
        for pj in personas:
            p = json.loads(pj.read_text())
            template = (REPO / "bluf" / "docs" / "templates"
                        / f"{p['template']}.md")
            self.assertTrue(template.exists(), template)
            self.assertIn("given", p)


if __name__ == "__main__":
    unittest.main()
