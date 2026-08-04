#!/usr/bin/env python3
"""Fail if the SEE-100 prose and dictionary.json drift apart.

Checks, in order:
  1. Section A table rows == distinct `row` values in dictionary `banned`,
     and every entry's `instead` matches its row's substitution column.
  2. Section B table rows == dictionary `locks` (term and meaning, exact).
  3. The `Version:` line in SEE-100.md == the dictionary's `see100` value.
  4. docs/SEE-100.md and bluf/docs/SEE-100.md are byte-identical.
  5. Every dictionary entry carries a rule number and a non-empty pattern list
     (locks need no patterns; their term is the pattern).

Exit 0 on sync, 1 on drift. Stdlib only.
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STANDARD = REPO / "docs" / "SEE-100.md"
PLUGIN_STANDARD = REPO / "bluf" / "docs" / "SEE-100.md"
DICTIONARY = REPO / "bluf" / "data" / "dictionary.json"


# Slash rows that are inflections of one term (one JSON entry with pattern
# variants). Every other " / " row splits into one entry per term.
SINGLE_ENTRY_ROWS = {"synergy / synergies", "alignment / aligned"}


def parse_table(text, heading):
    """Return [(cell1, cell2)] for the first markdown table after `heading`."""
    if heading not in text:
        raise SystemExit(f"SYNC CHECK FAILED: heading {heading!r} not found "
                         "in SEE-100.md")
    lines = text[text.index(heading):].splitlines()
    rows = []
    in_table = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|"):
            in_table = True
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) >= 2 and not set(cells[0]) <= set("-: "):
                rows.append((cells[0].replace("**", ""), cells[1].replace("**", "")))
        elif in_table:
            break
    return rows[1:]  # drop the header row


def parse_version(text):
    m = re.search(r"^Version:\s*(\S+)", text, re.MULTILINE)
    return m.group(1) if m else None


def rule_text(text, number):
    """Return the prose of one Part 1 rule (its paragraph and bullets)."""
    m = re.search(rf"\*\*Rule {re.escape(number)}\*\*(.*?)(?=\n\*\*Rule|\n#)",
                  text, re.DOTALL)
    return m.group(1) if m else ""


def quoted_terms(text):
    """Quoted terms in rule prose, lowercased, trailing punctuation dropped."""
    return {t.rstrip(",.").lower() for t in re.findall(r'"([^"]+)"', text)}


def expected_prose_bans(text):
    """The prose-ban term set each Part 1 rule names, keyed by rule number."""
    bullets = re.findall(r'^- "([^"]+)"', rule_text(text, "3.4"), re.MULTILINE)
    return {
        "8.5": quoted_terms(rule_text(text, "8.5")),
        "8.2": quoted_terms(rule_text(text, "8.2")),
        "3.4": {b.rstrip(",.").lower() for b in bullets},
        "5.4": {"we should"},
    }


def check(standard_path=STANDARD, plugin_standard_path=PLUGIN_STANDARD,
          dictionary_path=DICTIONARY):
    """Return a list of drift messages. Empty list means in sync."""
    errors = []
    text = standard_path.read_text()
    dictionary = json.loads(dictionary_path.read_text())

    # 1. Section A rows vs banned entries
    section_a = dict(parse_table(text, "## Section A"))
    banned = dictionary.get("banned", [])
    json_rows = {e["row"] for e in banned}
    for row in sorted(section_a.keys() - json_rows):
        errors.append(f"Section A row missing from dictionary: {row!r}")
    for row in sorted(json_rows - section_a.keys()):
        errors.append(f"dictionary row not in Section A table: {row!r}")
    for entry in banned:
        expected = section_a.get(entry["row"])
        if expected is not None and entry.get("instead") != expected:
            errors.append(
                f"substitution drift for {entry['row']!r}: "
                f"table says {expected!r}, dictionary says {entry.get('instead')!r}")
        if entry.get("term", "").lower() not in entry["row"].lower():
            errors.append(
                f"term {entry.get('term')!r} does not appear in its row "
                f"{entry['row']!r}")

    # Split rows: one entry per slashed term, unless the row is inflections
    # of a single term
    for row in section_a:
        want = 1 if row in SINGLE_ENTRY_ROWS else row.count(" / ") + 1
        got = sum(1 for e in banned if e["row"] == row)
        if row in json_rows and got != want:
            errors.append(
                f"row {row!r} should have {want} dictionary entries, has {got}")

    # 2. Section B rows vs locks
    section_b = dict(parse_table(text, "## Section B"))
    locks = {e["term"]: e.get("meaning") for e in dictionary.get("locks", [])}
    for term in sorted(section_b.keys() - locks.keys()):
        errors.append(f"Section B lock missing from dictionary: {term!r}")
    for term in sorted(locks.keys() - section_b.keys()):
        errors.append(f"dictionary lock not in Section B table: {term!r}")
    for term, meaning in section_b.items():
        if term in locks and locks[term] != meaning:
            errors.append(
                f"meaning drift for {term!r}: "
                f"table says {meaning!r}, dictionary says {locks[term]!r}")

    # 3. Version pin
    version = parse_version(text)
    if version is None:
        errors.append("no 'Version:' line in SEE-100.md")
    elif version != dictionary.get("see100"):
        errors.append(
            f"version drift: SEE-100.md says {version!r}, "
            f"dictionary see100 says {dictionary.get('see100')!r}")

    # 3b. Prose bans vs the Part 1 rules that name them
    expected = expected_prose_bans(text)
    actual = {}
    for entry in dictionary.get("prose_bans", []):
        actual.setdefault(entry.get("rule"), set()).add(entry["term"].lower())
    for rule, terms in expected.items():
        got = actual.get(rule, set())
        for term in sorted(terms - got):
            errors.append(f"Rule {rule} names {term!r} but prose_bans lacks it")
        for term in sorted(got - terms):
            errors.append(f"prose_bans has {term!r} under rule {rule} "
                          "but the rule prose does not name it")
    for rule in sorted(actual.keys() - expected.keys()):
        errors.append(f"prose_bans cites rule {rule}, which this check "
                      "does not know — add it to expected_prose_bans")

    # 4. Plugin copy byte-identical
    if standard_path.read_bytes() != plugin_standard_path.read_bytes():
        errors.append(
            f"{plugin_standard_path} differs from {standard_path} "
            "(run scripts/sync-standard)")

    # 5. Entry hygiene: rule number and patterns everywhere
    for section in ("banned", "prose_bans"):
        for entry in dictionary.get(section, []):
            name = f"{section} entry {entry.get('term')!r}"
            if not entry.get("rule"):
                errors.append(f"{name} has no rule number")
            if not entry.get("patterns"):
                errors.append(f"{name} has no patterns")
    for entry in dictionary.get("locks", []):
        if not entry.get("rule"):
            errors.append(f"locks entry {entry.get('term')!r} has no rule number")

    return errors


def main():
    errors = check()
    if errors:
        print("SYNC CHECK FAILED — prose and dictionary have drifted:")
        for error in errors:
            print(f"  - {error}")
        return 1
    dictionary = json.loads(DICTIONARY.read_text())
    rows = len({e["row"] for e in dictionary["banned"]})
    print(f"sync check passed: {rows} banned rows "
          f"({len(dictionary['banned'])} entries), "
          f"{len(dictionary['locks'])} locks, "
          f"{len(dictionary['prose_bans'])} prose bans, "
          f"see100 {dictionary['see100']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
