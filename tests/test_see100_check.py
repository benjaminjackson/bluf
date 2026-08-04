"""Unit tests for bluf/scripts/see100_check.py. Stdlib only."""
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "bluf" / "scripts"))
import see100_check


def rules(text):
    return [f["rule"] for f in see100_check.check(text)["findings"]]


def findings_for(text, rule):
    return [f for f in see100_check.check(text)["findings"]
            if f["rule"] == rule]


class TestBannedWords(unittest.TestCase):
    def test_simple_banned_word(self):
        f = findings_for("This plan has synergy.", "1.1")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]["quote"], "synergy")
        self.assertEqual(f[0]["layer"], "deterministic")
        self.assertNotIn("candidate", f[0])

    def test_case_insensitive(self):
        self.assertEqual(len(findings_for("Utilize the tool.", "1.1")), 1)

    def test_word_boundaries(self):
        self.assertEqual(rules("The cleverage of the plan."), [])
        self.assertEqual(rules("Granularity aside, synergyx is a product name."),
                         ["1.1"])  # granularity matches; synergyx does not

    def test_inflections(self):
        f = findings_for("We leveraged it. She circles back often.", "3.5")
        self.assertEqual([x["quote"] for x in f], ["circles back"])

    def test_line_and_col(self):
        f = findings_for("clean line\nhere is synergy", "1.1")
        self.assertEqual((f[0]["line"], f[0]["col"]), (2, 9))

    def test_conditioned_entry_is_candidate(self):
        f = findings_for("We lack bandwidth.", "1.1")
        self.assertTrue(f[0]["candidate"])
        self.assertEqual(f[0]["layer"], "judgment")

    def test_pos_confirm_entry_is_candidate(self):
        f = findings_for("Please action the report.", "1.6")
        self.assertTrue(f[0]["candidate"])

    def test_multiword_pattern_across_spaces(self):
        self.assertEqual(len(findings_for("It was low hanging fruit.", "1.1")), 1)


class TestExceptions(unittest.TestCase):
    def test_pivot_table(self):
        self.assertEqual(rules("Build a pivot table in Excel."), [])

    def test_leverage_ratio(self):
        self.assertEqual(rules("The leverage ratio rose."), [])

    def test_material_weakness(self):
        self.assertEqual(rules("The audit found a material weakness."), [])

    def test_action_items(self):
        self.assertEqual(rules("Review the action items."), [])

    def test_pivot_alone_still_fires(self):
        self.assertEqual(rules("We will pivot."), ["1.1"])


class TestSkipRegions(unittest.TestCase):
    def test_fenced_code(self):
        self.assertEqual(rules("```\nleverage synergy; robust\n```\n"), [])

    def test_inline_code(self):
        self.assertEqual(rules("Run `leverage --synergy` locally."), [])

    def test_url(self):
        self.assertEqual(rules("See https://example.com/leverage-synergy now."),
                         [])

    def test_blockquote(self):
        self.assertEqual(
            rules("> We should leverage synergies; circle back soon.\n"), [])

    def test_frontmatter(self):
        self.assertEqual(rules("---\ntitle: synergy leverage\n---\nClean.\n"),
                         [])

    def test_file_path(self):
        self.assertEqual(rules("Open docs/leverage-synergy.md to see it."), [])

    def test_indented_fence_in_list(self):
        text = ("- The rollback command:\n\n"
                "    ```\n    leverage synergies; circle back\n    ```\n")
        self.assertEqual(rules(text), [])


class TestSentences(unittest.TestCase):
    def test_26_word_sentence_fires(self):
        sent = "word " * 25 + "end."
        f = findings_for(sent, "4.1")
        self.assertEqual(len(f), 1)
        self.assertIn("26 words", f[0]["message"])

    def test_25_word_sentence_passes(self):
        self.assertEqual(findings_for("word " * 24 + "end.", "4.1"), [])

    def test_abbreviations_do_not_split(self):
        text = ("We hired Dr. Smith to run ops, e.g. planning, and gave the "
                "team a start date of Aug. 15 with a formal offer letter "
                "signed well before then.")
        self.assertEqual(len(findings_for(text, "4.1")), 1)

    def test_decimal_does_not_split(self):
        self.assertEqual(findings_for("Churn is 4.1% now.", "4.1"), [])

    def test_headings_excluded(self):
        heading = "# " + "word " * 30 + "\n\nShort body.\n"
        self.assertEqual(findings_for(heading, "4.1"), [])

    def test_list_item_counts(self):
        item = "- " + "word " * 26 + "\n"
        self.assertEqual(len(findings_for(item, "4.1")), 1)

    def test_link_counts_text_not_url(self):
        text = ("See [the report](https://example.com/a/very/long/path/that/"
                "would/blow/the/word/count/if/counted) for details.")
        self.assertEqual(findings_for(text, "4.1"), [])

    def test_nested_list_items_split(self):
        text = ("- Ship the config\n"
                "  - Flip the flag\n"
                "  - Watch the dashboards for one hour\n"
                "  - Page Marco on regressions\n")
        self.assertEqual(findings_for(text, "4.1"), [])

    def test_digit_after_period_splits(self):
        text = ("Headcount is 42. 12 engineers rotate on call across four "
                "squads with two leads each and one shared manager for now.")
        self.assertEqual(findings_for(text, "4.1"), [])

    def test_curly_quote_boundary(self):
        text = ("Priya said the plan holds and every vendor signed “the date "
                "will hold.” Then she confirmed the full schedule in writing "
                "for the board.")
        self.assertEqual(findings_for(text, "4.1"), [])

    def test_asks_list_20_word_limit(self):
        long_item = "- Dana: " + "word " * 20 + "\n"
        text = "## Asks\n\n" + long_item
        f = findings_for(text, "5.2")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]["layer"], "deterministic")
        self.assertEqual(findings_for(text, "4.1"), [])

    def test_asks_limit_only_in_asks_section(self):
        long_item = "- Dana: " + "word " * 20 + "\n"
        text = "## Notes\n\n" + long_item
        self.assertEqual(findings_for(text, "5.2"), [])

    def test_paragraph_over_six_sentences(self):
        para = "This is one. " * 7
        f = findings_for(para, "6.4")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]["severity"], "warning")


class TestSemicolons(unittest.TestCase):
    def test_semicolon_fires(self):
        self.assertEqual(len(findings_for("One clause; another.", "8.7")), 1)

    def test_semicolon_in_code_ignored(self):
        self.assertEqual(findings_for("Run `a; b` now.", "8.7"), [])


class TestVagueDates(unittest.TestCase):
    def test_by_eoq_deterministic(self):
        f = findings_for("We ship by EOQ.", "8.2")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]["layer"], "deterministic")
        self.assertNotIn("candidate", f[0])

    def test_by_q3(self):
        self.assertEqual(len(findings_for("Launch by Q3.", "8.2")), 1)

    def test_quarter_with_day_passes(self):
        self.assertEqual(
            findings_for("Launch in Q3, on Aug 15.", "8.2"), [])

    def test_soon_is_candidate(self):
        f = findings_for("We will announce soon.", "8.2")
        self.assertEqual(len(f), 1)
        self.assertTrue(f[0].get("candidate"))


class TestPercentages(unittest.TestCase):
    def test_bare_percent_is_candidate(self):
        f = findings_for("Revenue is up 30%.", "8.6")
        self.assertEqual(len(f), 1)
        self.assertTrue(f[0]["candidate"])

    def test_percent_with_baseline_passes(self):
        self.assertEqual(
            findings_for("Revenue is up 30% from Q2 2025.", "8.6"), [])


class TestNounClusters(unittest.TestCase):
    def test_cluster_candidate(self):
        f = findings_for(
            "Kick off the enterprise customer churn mitigation workstream "
            "today.", "2.1")
        self.assertEqual(len(f), 1)
        self.assertTrue(f[0]["candidate"])

    def test_articles_break_runs(self):
        self.assertEqual(
            findings_for("The project to reduce churn in accounts.", "2.1"),
            [])


class TestNominalizations(unittest.TestCase):
    def test_make_a_decision(self):
        f = findings_for("We will make a decision on this.", "3.4")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]["severity"], "warning")
        self.assertEqual(f[0]["suggestion"], "decide")


class TestWeShould(unittest.TestCase):
    def test_we_should_fires(self):
        f = findings_for("We should fix the outage.", "5.4")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0]["layer"], "deterministic")


class TestOutput(unittest.TestCase):
    def test_deterministic_across_runs(self):
        text = ("We should leverage synergies; circle back by EOQ.\n\n"
                "Revenue is up 30%. The enterprise customer churn mitigation "
                "workstream kickoff starts soon.\n")
        a = json.dumps(see100_check.check(text), sort_keys=True)
        b = json.dumps(see100_check.check(text), sort_keys=True)
        self.assertEqual(a, b)

    def test_empty_document(self):
        self.assertEqual(see100_check.check("")["findings"], [])

    def test_clean_document(self):
        text = ("Maria decided on Aug 15 to cut scope.\n\n"
                "Churn is 4.1%, down from 4.6% in June. Dana: reply by "
                "Thursday Aug 20.\n")
        self.assertEqual(rules(text), [])

    def test_findings_sorted_by_position(self):
        text = "synergy first.\n\nThen utilize.\n"
        f = see100_check.check(text)["findings"]
        self.assertEqual([x["line"] for x in f], sorted(x["line"] for x in f))


if __name__ == "__main__":
    unittest.main()
