"""Release-gate assertions for README.md (bluf-7zl.5 gate, scripted)."""
import json
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "bluf" / "scripts"))
import see100_check

README = (REPO / "README.md").read_text()


class TestReadme(unittest.TestCase):
    def test_before_after_match_fixtures_verbatim(self):
        for stem in ("readme-before", "readme-after"):
            text = (REPO / "bluf" / "tests" / f"{stem}.md").read_text().strip()
            self.assertIn(text, README.replace("> ", ""),
                          f"README block drifted from fixture {stem}.md")

    def test_after_text_is_clean(self):
        after = (REPO / "bluf" / "tests" / "readme-after.md").read_text()
        self.assertEqual(see100_check.check(after)["findings"], [])

    def test_skill_list_matches_shipped_directories(self):
        shipped = {p.name for p in (REPO / "bluf" / "skills").iterdir()
                   if (p / "SKILL.md").exists()}
        # Skills documented above the "Planned" heading
        documented = set(re.findall(r"`/bluf:(\w+)`",
                                    README.split("### Planned")[0]))
        self.assertEqual(documented, shipped)

    def test_planned_skills_are_not_shipped(self):
        shipped = {p.name for p in (REPO / "bluf" / "skills").iterdir()
                   if (p / "SKILL.md").exists()}
        planned = set(re.findall(r"`/bluf:(\w+)`",
                                 README.split("### Planned")[1]
                                 .split("## Why STE?")[0]))
        self.assertFalse(planned & shipped,
                         "a Planned skill is actually shipped — move it up")

    def test_install_command_matches_manifests(self):
        market = json.loads(
            (REPO / ".claude-plugin" / "marketplace.json").read_text())
        plugin = json.loads(
            (REPO / "bluf" / ".claude-plugin" / "plugin.json").read_text())
        self.assertIn("/plugin install bluf@bluf", README)
        self.assertEqual(market["name"], "bluf")
        self.assertEqual(plugin["name"], "bluf")
        self.assertTrue(any(e["name"] == "bluf" and e["source"] == "./bluf"
                            for e in market["plugins"]))


if __name__ == "__main__":
    unittest.main()
