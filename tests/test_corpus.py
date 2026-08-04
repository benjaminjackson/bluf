"""Corpus contract tests: checker output pinned to expected files."""
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CORPUS = REPO / "bluf" / "tests"
sys.path.insert(0, str(REPO / "bluf" / "scripts"))
import see100_check

FIXTURES = sorted(CORPUS.glob("*.md"))
FIXTURES = [f for f in FIXTURES if f.name != "README.md"]

FINDING_KEYS = {"rule", "layer", "severity", "scope", "line", "col", "quote",
                "message", "suggestion", "candidate"}


class TestCorpus(unittest.TestCase):
    def test_every_fixture_has_expected_file(self):
        for md in FIXTURES:
            self.assertTrue(md.with_suffix(".expected.json").exists(),
                            f"{md.name} has no expected file")

    def test_script_findings_match_expected_exactly(self):
        for md in FIXTURES:
            expected = json.loads(md.with_suffix(".expected.json").read_text())
            actual = see100_check.check(md.read_text())["findings"]
            self.assertEqual(actual, expected["script"],
                             f"checker drifted from {md.name} expectations")

    def test_expected_files_validate_against_schema(self):
        for md in FIXTURES:
            expected = json.loads(md.with_suffix(".expected.json").read_text())
            for f in expected["script"]:
                self.assertLessEqual(set(f), FINDING_KEYS, md.name)
                self.assertIn(f["layer"], ("deterministic", "judgment"))
                self.assertIn(f["severity"], ("error", "warning"))
                self.assertIn(f["scope"], ("span", "document"))
                self.assertTrue(f["quote"], md.name)
            judgment = expected["judgment"]
            for key in ("must_find", "must_not_find", "allowed"):
                self.assertIn(key, judgment, md.name)
                for entry in judgment[key]:
                    self.assertIn("rule", entry, md.name)
            for entry in judgment["must_find"]:
                if "quote" in entry:
                    self.assertIn(entry["quote"], md.read_text(),
                                  f"{md.name}: must_find quote not in fixture")

    def test_quotes_appear_in_fixture(self):
        for md in FIXTURES:
            text = md.read_text()
            expected = json.loads(md.with_suffix(".expected.json").read_text())
            for f in expected["script"]:
                self.assertIn(f["quote"], text, md.name)


if __name__ == "__main__":
    unittest.main()
