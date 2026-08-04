"""Structural gate for the triage corpus.

Enforces the hand-writing rules in bluf/tests/triage/README.md mechanically,
with the grader's own helpers — so a gold file the grader could not ground
never lands, and gold and grader cannot drift apart.
"""
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import grade

CORPUS = REPO / "bluf" / "tests" / "triage"
GOLD_KEYS = {
    "is_thread", "facts", "allowed_facts", "must_not_extract",
    "contradictions_must_include", "unresolved_must_include",
    "no_resolved_dates", "gaps_must_include", "gaps_must_not_include",
    "gaps_must_be_empty", "skipped_must_be_nonempty", "verdict_regex",
    "notes",
}


def pairs():
    for gold_path in sorted(CORPUS.glob("*.gold.json")):
        gold = json.loads(gold_path.read_text())
        doc = gold_path.with_name(
            gold_path.name.replace(".gold.json", ".md")).read_text()
        yield gold_path.name, gold, doc


class TestTriageCorpus(unittest.TestCase):
    def test_six_fixtures_each_with_gold(self):
        stems = {p.stem for p in CORPUS.glob("*.md")} - {"README"}
        golds = {p.name.replace(".gold.json", "")
                 for p in CORPUS.glob("*.gold.json")}
        self.assertEqual(stems, golds)
        self.assertEqual(len(stems), 6)

    def test_gold_keys_are_known(self):
        for name, gold, _ in pairs():
            unknown = set(gold) - GOLD_KEYS
            self.assertFalse(unknown, f"{name}: unknown keys {unknown}")

    def test_every_quote_contains_is_verbatim_and_single_line(self):
        for name, gold, doc in pairs():
            for section in ("facts", "allowed_facts", "must_not_extract"):
                for entry in gold.get(section, []):
                    q = entry.get("quote_contains", "*")
                    if q == "*":
                        continue
                    self.assertIn(q, doc, f"{name} [{section}]: {q!r}")
                    self.assertNotIn("\n", q, f"{name}: multi-line {q!r}")
            for token in gold.get("unresolved_must_include", []):
                self.assertIn(token, doc, f"{name} [unresolved]: {token!r}")
            for c in gold.get("contradictions_must_include", []):
                for q in c.get("quotes_contain", []):
                    self.assertIn(q, doc, f"{name} [contradiction]: {q!r}")

    def test_gold_fact_scalars_are_grounded(self):
        # Writing rule 2: every owner/date/decider/value/baseline a gold
        # entry requires must pass the grader's own grounding check when
        # the skill quotes exactly the quote_contains span.
        for name, gold, doc in pairs():
            for entry in gold.get("facts", []):
                q = entry.get("quote_contains", "*")
                if q == "*":
                    continue
                fact = {k: v for k, v in entry.items()
                        if k not in ("quote_contains", "must_not_have",
                                     "why")}
                fact["quote"] = q
                for key in grade.GROUNDED_FIELDS:
                    if key in fact:
                        self.assertTrue(
                            grade.field_grounded(doc, fact, key,
                                                 gold.get("is_thread")),
                            f"{name}: {key}={fact[key]!r} not grounded for "
                            f"quote {q!r}")

    def test_gap_spec_stems_fit_the_vocabulary(self):
        for name, gold, _ in pairs():
            for section in ("gaps_must_include", "gaps_must_not_include"):
                for spec in gold.get(section, []):
                    stem = str(spec.get("missing", "")).lower()
                    self.assertTrue(
                        stem == "" or any(stem in slot
                                          for slot in grade.GAP_SLOTS),
                        f"{name} [{section}]: stem {stem!r} matches no "
                        "vocabulary slot")

    def test_gold_types_are_closed(self):
        for name, gold, _ in pairs():
            for section in ("facts", "allowed_facts", "must_not_extract"):
                for entry in gold.get(section, []):
                    t = entry.get("type")
                    self.assertTrue(t == "*" or t in grade.FACT_TYPES,
                                    f"{name} [{section}]: type {t!r}")


if __name__ == "__main__":
    unittest.main()
