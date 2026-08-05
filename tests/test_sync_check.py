"""Unit tests for scripts/sync_check.py. Stdlib only."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import sync_check


class TempTree(unittest.TestCase):
    """Copies the real files into a temp tree the tests can mutate."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.standard = self.tmp / "SEE-100.md"
        self.plugin_standard = self.tmp / "plugin-SEE-100.md"
        self.dictionary = self.tmp / "dictionary.json"
        shutil.copyfile(sync_check.STANDARD, self.standard)
        shutil.copyfile(sync_check.STANDARD, self.plugin_standard)
        shutil.copyfile(sync_check.DICTIONARY, self.dictionary)

    def run_check(self):
        return sync_check.check(self.standard, self.plugin_standard,
                                self.dictionary)

    def mutate_dictionary(self, fn):
        data = json.loads(self.dictionary.read_text())
        fn(data)
        self.dictionary.write_text(json.dumps(data))


class TestParsing(unittest.TestCase):
    def test_section_a_has_40_rows(self):
        text = sync_check.STANDARD.read_text()
        self.assertEqual(len(sync_check.parse_table(text, "## Section A")), 40)

    def test_section_b_has_14_rows(self):
        text = sync_check.STANDARD.read_text()
        self.assertEqual(len(sync_check.parse_table(text, "## Section B")), 14)

    def test_bold_markers_stripped(self):
        text = sync_check.STANDARD.read_text()
        rows = dict(sync_check.parse_table(text, "## Section B"))
        self.assertIn("on track", rows)
        self.assertNotIn("**on track**", rows)

    def test_version_parsed(self):
        text = sync_check.STANDARD.read_text()
        self.assertEqual(sync_check.parse_version(text), "1.0")


class TestSync(TempTree):
    def test_real_files_pass(self):
        self.assertEqual(self.run_check(), [])

    def test_removed_json_entry_fails(self):
        self.mutate_dictionary(lambda d: d["banned"].pop())
        self.assertTrue(any("missing from dictionary" in e
                            for e in self.run_check()))

    def test_extra_json_entry_fails(self):
        self.mutate_dictionary(lambda d: d["banned"].append(
            {"term": "bogus", "row": "bogus", "rule": "1.1",
             "instead": "x", "patterns": ["bogus"]}))
        self.assertTrue(any("not in Section A" in e for e in self.run_check()))

    def test_substitution_drift_fails(self):
        def drift(d):
            d["banned"][0]["instead"] = "changed"
        self.mutate_dictionary(drift)
        self.assertTrue(any("substitution drift" in e
                            for e in self.run_check()))

    def test_meaning_drift_fails(self):
        def drift(d):
            d["locks"][0]["meaning"] = "changed"
        self.mutate_dictionary(drift)
        self.assertTrue(any("meaning drift" in e for e in self.run_check()))

    def test_removed_table_row_fails(self):
        text = self.standard.read_text().replace("| utilize | use |\n", "")
        self.standard.write_text(text)
        self.plugin_standard.write_text(text)
        self.assertTrue(any("not in Section A" in e for e in self.run_check()))

    def test_version_drift_fails(self):
        self.mutate_dictionary(lambda d: d.update(see100="9.9"))
        self.assertTrue(any("version drift" in e for e in self.run_check()))

    def test_stale_plugin_copy_fails(self):
        self.plugin_standard.write_text(
            self.plugin_standard.read_text() + "\nstale\n")
        self.assertTrue(any("differs from" in e for e in self.run_check()))

    def test_dropped_split_term_fails(self):
        def drop(d):
            d["banned"] = [e for e in d["banned"] if e["term"] != "tailwinds"]
        self.mutate_dictionary(drop)
        self.assertTrue(any("should have 2 dictionary entries" in e
                            for e in self.run_check()))

    def test_garbled_term_fails(self):
        def garble(d):
            d["banned"][0]["term"] = "wrongterm"
        self.mutate_dictionary(garble)
        self.assertTrue(any("does not appear in its row" in e
                            for e in self.run_check()))

    def test_dropped_prose_ban_fails(self):
        def drop(d):
            d["prose_bans"] = [e for e in d["prose_bans"]
                               if e["term"] != "soon"]
        self.mutate_dictionary(drop)
        self.assertTrue(any("prose_bans lacks it" in e
                            for e in self.run_check()))

    def test_invented_prose_ban_fails(self):
        self.mutate_dictionary(lambda d: d["prose_bans"].append(
            {"term": "bogus", "rule": "8.2", "instead": "x",
             "patterns": ["bogus"]}))
        self.assertTrue(any("does not name it" in e for e in self.run_check()))

    def test_missing_rule_ref_fails(self):
        def strip_ref(d):
            del d["locks"][0]["rule_ref"]
        self.mutate_dictionary(strip_ref)
        self.assertTrue(any("no rule_ref.primary" in e
                            for e in self.run_check()))

    def test_unknown_primary_rule_fails(self):
        def bogus(d):
            d["banned"][0]["rule_ref"]["primary"] = "12.9"
        self.mutate_dictionary(bogus)
        self.assertTrue(any("routes to rule '12.9'" in e
                            for e in self.run_check()))

    def test_unknown_see_also_rule_fails(self):
        def bogus(d):
            d["locks"][0]["rule_ref"]["see_also"] = ["12.9"]
        self.mutate_dictionary(bogus)
        self.assertTrue(any("cross-refers to rule '12.9'" in e
                            for e in self.run_check()))

    def test_missing_rule_number_fails(self):
        def strip_rule(d):
            del d["prose_bans"][0]["rule"]
        self.mutate_dictionary(strip_rule)
        self.assertTrue(any("no rule number" in e for e in self.run_check()))


if __name__ == "__main__":
    unittest.main()
