"""Unit tests for the /bluf:explain data files. Stdlib only.

lineage.json and examples.json must cover every classified rule, and no
lineage entry may name an STE rule number the standard does not cite.
"""
import json
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "bluf" / "scripts"))
import see100_check
import sync_check

LINEAGE = json.loads((REPO / "bluf" / "data" / "lineage.json").read_text())
EXAMPLES = json.loads((REPO / "bluf" / "data" / "examples.json").read_text())
STANDARD = (REPO / "docs" / "SEE-100.md").read_text()
RULES = sync_check.classification_rules(
    (REPO / "bluf" / "docs" / "FINDINGS.md").read_text())


def cited_ste_rules(rule):
    """STE rule numbers the standard cites in one rule's prose, in order."""
    numbers = []
    for cite in re.findall(r"\*\(([^)]*)\)\*", sync_check.rule_text(STANDARD, rule)):
        if re.match(r"STE Rules?\s", cite):
            numbers += re.findall(r"\d+\.\d+", cite)
    return numbers


class TestLineage(unittest.TestCase):
    def test_covers_every_rule(self):
        self.assertEqual(set(LINEAGE), RULES)

    def test_no_invented_ste_ancestors(self):
        for rule, entry in LINEAGE.items():
            cited = cited_ste_rules(rule)
            want = ", ".join(cited) if cited else None
            self.assertEqual(entry["ste"], want, f"rule {rule}")

    def test_every_entry_has_a_note(self):
        for rule, entry in LINEAGE.items():
            self.assertTrue(entry.get("note"), f"rule {rule}")

    def test_null_ancestors_name_their_mechanism(self):
        for rule, entry in LINEAGE.items():
            if entry["ste"] is None:
                self.assertIn("no", entry["note"].lower(), f"rule {rule}")


class TestExamples(unittest.TestCase):
    def test_covers_every_rule(self):
        self.assertEqual(set(EXAMPLES), RULES)

    def test_shapes_are_known(self):
        for rule, entry in EXAMPLES.items():
            self.assertIn(entry["shape"], ("rewrite", "structure", "guidance"),
                          f"rule {rule}")

    def test_rewrite_rules_have_three_pairs(self):
        for rule, entry in EXAMPLES.items():
            if entry["shape"] == "rewrite":
                pairs = entry["pairs"]
                self.assertEqual(len(pairs), 3, f"rule {rule}")
                for pair in pairs:
                    self.assertTrue(pair["before"] and pair["after"])

    def test_structure_rules_show_a_whole_document(self):
        for rule, entry in EXAMPLES.items():
            if entry["shape"] == "structure":
                self.assertTrue(entry["examples"], f"rule {rule}")
                for example in entry["examples"]:
                    self.assertTrue(
                        {"wrong_order", "right_order"} <= set(example)
                        or {"before", "after"} <= set(example), f"rule {rule}")

    def test_guidance_rules_carry_guidance(self):
        for rule, entry in EXAMPLES.items():
            if entry["shape"] == "guidance":
                self.assertTrue(entry["guidance"], f"rule {rule}")
                self.assertLessEqual(len(entry.get("pairs", [])), 1,
                                     f"rule {rule}")

    def test_every_number_is_answerable_or_rejectable_consistently(self):
        # A number 1.1-9.9 is explained iff it is in BOTH data files;
        # a number in one file only would answer and reject at once.
        for major in range(1, 10):
            for minor in range(1, 10):
                n = f"{major}.{minor}"
                self.assertEqual(n in LINEAGE, n in EXAMPLES, n)

    def test_check_d_deterministic_befores_trip_their_rule(self):
        # Check (d) of bluf-3oz.5, static half: where the checker can see
        # the rule (det/hyb rows), every rewrite 'before' must trip it.
        findings_doc = (REPO / "bluf" / "docs" / "FINDINGS.md").read_text()
        det_rules = set(re.findall(
            r"^\| (\d\.\d+) \|[^|]*\| (?:det|hyb)", findings_doc, re.M))
        # 6.3 shares one check with 4.1; the checker always emits 4.1
        # (FINDINGS.md notes). Dual-layer rules whose curated befores
        # exercise the judgment half are out of the checker's sight.
        ALIAS = {"6.3": "4.1"}
        JUDGMENT_HALF = {"5.4", "6.4"}
        for rule, entry in EXAMPLES.items():
            if (entry["shape"] != "rewrite" or rule not in det_rules
                    or rule in JUDGMENT_HALF):
                continue
            want = ALIAS.get(rule, rule)
            for pair in entry["pairs"]:
                hit = {f["rule"] for f in
                       see100_check.check(pair["before"])["findings"]}
                self.assertIn(want, hit,
                              f"rule {rule}: before {pair['before']!r} "
                              "does not trip its own rule")

    def test_every_clean_text_passes_the_checker(self):
        """No 'after', 'right_order', or guidance text may trip any rule."""
        for rule, entry in EXAMPLES.items():
            texts = []
            if "guidance" in entry:
                texts.append(("guidance", entry["guidance"]))
            for item in entry.get("pairs", []) + entry.get("examples", []):
                texts += [(key, item[key]) for key in ("after", "right_order")
                          if key in item]
            for key, text in texts:
                findings = see100_check.check(text)["findings"]
                self.assertEqual(
                    findings, [],
                    f"rule {rule} {key}: {text!r} trips "
                    + ", ".join(f["rule"] for f in findings))


if __name__ == "__main__":
    unittest.main()
