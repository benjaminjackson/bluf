#!/usr/bin/env python3
"""Grade the bluf skills against the corpus. Stdlib only.

Layers are graded differently (see bluf/tests/README.md):

- Script layer (always): see100_check.py output must equal each fixture's
  expected `script` array exactly.
- Judgment layer (--skill lint): run /bluf:lint via the claude CLI N times
  per fixture (default 3). The JSON block's deterministic findings must
  reproduce the script output verbatim; judgment findings are graded by
  must_find / must_not_find / allowed with span-overlap matching.
  Disagreement between runs is a failure.
- Rewrite (--skill rewrite): fixtures with a `rewrite` key. The rewrite must
  produce zero non-candidate checker findings, name every required gap rule,
  and pass a closed-world fact check: numbers, dollar amounts, and proper
  nouns in the output must already exist in the input.

The harness consumes JSON only. It never parses rendered prose outside the
fenced json block the skills emit on request.

Usage:
  python3 scripts/grade.py                      # script layer only
  python3 scripts/grade.py --skill lint         # + lint judgment grading
  python3 scripts/grade.py --skill rewrite      # + rewrite grading
  python3 scripts/grade.py --skill all --runs 3 --only lock-misuse
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLUGIN = REPO / "bluf"
CORPUS = PLUGIN / "tests"
DUMP_DIR = Path("/tmp/bluf-grade-runs")
sys.path.insert(0, str(PLUGIN / "scripts"))
import see100_check  # noqa: E402

JSON_BLOCK = re.compile(r"```json\s*\n(.*?)```", re.DOTALL)


def fixtures(only=None):
    for md in sorted(CORPUS.glob("*.md")):
        if md.name == "README.md":
            continue
        if only and md.stem not in only:
            continue
        yield md, json.loads(md.with_suffix(".expected.json").read_text())


def fail(errors, message):
    errors.append(message)
    print(f"  FAIL {message}")


def grade_script(only=None):
    errors = []
    for md, expected in fixtures(only):
        actual = see100_check.check(md.read_text())["findings"]
        if actual != expected["script"]:
            fail(errors, f"{md.name}: checker output != expected script "
                         "findings (regenerate deliberately or fix checker)")
        else:
            print(f"  ok   {md.name}: {len(actual)} script findings")
    return errors


def run_skill(command, timeout=600):
    result = subprocess.run(
        ["claude", "-p", "--plugin-dir", str(PLUGIN), command],
        capture_output=True, text=True, timeout=timeout, cwd=str(REPO))
    if result.returncode != 0:
        raise RuntimeError(f"claude exited {result.returncode}: "
                           f"{result.stderr[:500]}")
    # Take the LAST ```json opener and everything up to the LAST fence, so a
    # rewrite whose own text contains code fences cannot truncate the block.
    start = result.stdout.rfind("```json")
    if start < 0:
        raise RuntimeError(f"no fenced json block in output:\n"
                           f"{result.stdout[-500:]}")
    body = result.stdout[start + len("```json"):]
    end = body.rfind("```")
    payload = json.loads(body[:end if end >= 0 else None])
    DUMP_DIR.mkdir(exist_ok=True)
    slug = re.sub(r"\W+", "-", command)[:80]
    existing = len(list(DUMP_DIR.glob(f"{slug}*")))
    (DUMP_DIR / f"{slug}-{existing}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False))
    return payload


def spans_overlap(doc, quote_a, quote_b):
    a, b = doc.find(quote_a), doc.find(quote_b)
    if a < 0 or b < 0:
        return quote_a in quote_b or quote_b in quote_a
    return a < b + len(quote_b) and b < a + len(quote_a)


def matches(doc, finding, rule_spec):
    if rule_spec["rule"] not in ("*", finding["rule"]):
        return False
    if "quote" in rule_spec:
        if not finding.get("quote"):
            return False
        return spans_overlap(doc, finding["quote"], rule_spec["quote"])
    return True


def grade_lint_run(md, expected, payload, errors):
    doc = md.read_text()
    script = see100_check.check(doc)["findings"]
    got = payload if isinstance(payload, list) else payload.get("findings", [])
    # The skill's JSON carries only its judgment layer; the deterministic
    # layer comes straight from the checker — machine data never round-trips
    # through the model. A det-layer finding in the payload is a contract
    # violation.
    det_got = [f for f in got if f.get("layer") == "deterministic"]
    if det_got:
        fail(errors, f"{md.name}: payload contains {len(det_got)} "
                     "deterministic findings; the JSON block is "
                     "judgment-only")
    det = [f for f in script if not f.get("candidate")]
    judgment = [f for f in got if f.get("layer") == "judgment"]
    verdict = []
    for spec in expected["judgment"]["must_find"]:
        hit = any(matches(doc, f, spec) for f in judgment + det)
        verdict.append(("find", json.dumps(spec, sort_keys=True), hit))
        if not hit:
            fail(errors, f"{md.name}: must_find missed {spec}")
    for spec in expected["judgment"]["must_not_find"]:
        hits = [f for f in judgment if matches(doc, f, spec)]
        verdict.append(("not_find", json.dumps(spec, sort_keys=True),
                        not hits))
        for f in hits:
            fail(errors, f"{md.name}: must_not_find violated: "
                         f"{f['rule']} {f.get('quote', '')!r}")
    return verdict


def grade_lint(runs, only=None):
    errors = []
    for md, expected in fixtures(only):
        verdicts = []
        for i in range(runs):
            print(f"  run  {md.name} [{i + 1}/{runs}]")
            try:
                payload = run_skill(
                    f"/bluf:lint {md} — emit findings JSON")
            except (RuntimeError, subprocess.TimeoutExpired,
                    json.JSONDecodeError) as e:
                fail(errors, f"{md.name} run {i + 1}: {e}")
                continue
            verdicts.append(grade_lint_run(md, expected, payload, errors))
        if len({json.dumps(v) for v in verdicts}) > 1:
            fail(errors, f"{md.name}: runs disagree on "
                         "must_find/must_not_find — variance is a failure")
    return errors


FACT_TOKEN = re.compile(
    r"\$[\d,.]+[kKmMbB]?|\b\d+(?:[.,]\d+)*%?\b|\b[A-Z][a-z]+\b")


def new_facts(input_text, output_text):
    """Facts in the output that the input never stated.

    Numbers and dollar amounts must appear in the input as exact tokens.
    A capitalized word counts as a new proper noun only when its lowercase
    form is absent from the input AND it appears somewhere mid-sentence in
    the output. Sentence-initial-only capitalized words are imperatives and
    labels ("Name the owner", "Ask:"), not fabrications.
    ponytail: a fabricated name used only sentence-initially slips through;
    numbers and dates — the facts that matter most — stay strict.
    """
    input_tokens = set(FACT_TOKEN.findall(input_text))
    input_lower = input_text.lower()
    found = []
    for token in set(FACT_TOKEN.findall(output_text)):
        if token[0].isalpha():
            if token.lower() in input_lower:
                continue
            mid_sentence = re.search(
                r"[a-z0-9,] +" + re.escape(token) + r"\b", output_text)
            if mid_sentence:
                found.append(token)
        elif token not in input_tokens:
            found.append(token)
    return sorted(found)


def grade_rewrite(runs, only=None):
    errors = []
    for md, expected in fixtures(only):
        if "rewrite" not in expected:
            continue
        for i in range(runs):
            print(f"  run  {md.name} rewrite [{i + 1}/{runs}]")
            try:
                payload = run_skill(
                    f"/bluf:rewrite {md} — emit rewrite JSON")
            except (RuntimeError, subprocess.TimeoutExpired,
                    json.JSONDecodeError) as e:
                fail(errors, f"{md.name} run {i + 1}: {e}")
                continue
            rewrite = payload.get("rewrite", "")
            residual = [f for f in see100_check.check(rewrite)["findings"]
                        if not f.get("candidate")]
            for f in residual:
                fail(errors, f"{md.name}: rewrite still violates "
                             f"{f['rule']}: {f['quote']!r}")
            gap_rules = {g.get("rule") for g in payload.get("gaps", [])}
            for rule in expected["rewrite"]["gaps_must_include"]:
                if rule not in gap_rules:
                    fail(errors, f"{md.name}: Gaps missing rule {rule}")
            invented = new_facts(md.read_text(), rewrite)
            for token in invented:
                fail(errors, f"{md.name}: invented fact {token!r} "
                             "(closed-world violation)")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill", choices=["lint", "rewrite", "all"])
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--only", nargs="*", help="fixture stems to grade")
    args = parser.parse_args()

    print("script layer:")
    errors = grade_script(args.only)
    if args.skill in ("lint", "all"):
        print("lint judgment layer:")
        errors += grade_lint(args.runs, args.only)
    if args.skill in ("rewrite", "all"):
        print("rewrite:")
        errors += grade_rewrite(args.runs, args.only)

    print(f"\n{'FAIL' if errors else 'PASS'}: {len(errors)} failure(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
