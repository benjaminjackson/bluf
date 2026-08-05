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
- Triage (--skill triage): fixtures in bluf/tests/triage/ with hand-written
  .gold.json files. Recall against gold facts; fabrication (ungrounded
  fields, invented types, false gaps) is a hard fail. Matching semantics:
  bluf/tests/triage/README.md.

The harness consumes JSON only. It never parses rendered prose outside the
fenced json block the skills emit on request.

Usage:
  python3 scripts/grade.py                      # script layer only
  python3 scripts/grade.py --skill lint         # + lint judgment grading
  python3 scripts/grade.py --skill rewrite      # + rewrite grading
  python3 scripts/grade.py --skill triage       # + triage extraction grading
  python3 scripts/grade.py --skill all --runs 3 --only lock-misuse
"""
import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLUGIN = REPO / "bluf"
CORPUS = PLUGIN / "tests"
TRIAGE_CORPUS = CORPUS / "triage"
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


def run_skill(command, dump_name, timeout=600):
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
    # Deterministic name from (phase, fixture, run index) — no glob counting,
    # which raced under concurrent workers.
    (DUMP_DIR / f"{dump_name}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False))
    return payload


def triage_fixtures(only=None):
    if not TRIAGE_CORPUS.is_dir():
        return
    for md in sorted(TRIAGE_CORPUS.glob("*.md")):
        if md.name == "README.md":
            continue
        if only and md.stem not in only:
            continue
        yield md, json.loads(md.with_suffix(".gold.json").read_text())


COMMANDS = {
    "lint": "/bluf:lint {md} — emit findings JSON",
    "rewrite": "/bluf:rewrite {md} — emit rewrite JSON",
    "triage": "/bluf:triage {md} — emit triage JSON",
}


def run_one(phase, md, i):
    command = COMMANDS[phase].format(md=md)
    return run_skill(command, f"{phase}-{md.stem}-{i}")


def collect(jobs, workers):
    """Run every (phase, fixture, run-index) job on a bounded pool.

    Returns {(phase, stem, i): payload-or-exception}. A failed run becomes
    its exception so the grader counts it without killing sibling jobs.
    """
    results = {}
    if not jobs:
        return results
    total = len(jobs)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(run_one, phase, md, i): (phase, md, i)
                for phase, md, i in jobs}
        for n, fut in enumerate(as_completed(futs), 1):
            phase, md, i = futs[fut]
            try:
                results[(phase, md.stem, i)] = fut.result()
            except (RuntimeError, subprocess.TimeoutExpired,
                    json.JSONDecodeError) as e:
                results[(phase, md.stem, i)] = e
            print(f"  done {phase} {md.name} run {i + 1} [{n}/{total}]")
    return results


def spans_overlap(doc, quote_a, quote_b):
    a, b = doc.find(quote_a), doc.find(quote_b)
    if a < 0 or b < 0:
        return quote_a in quote_b or quote_b in quote_a
    return a < b + len(quote_b) and b < a + len(quote_a)


def matches(doc, finding, rule_spec):
    if rule_spec["rule"] not in ("*", finding["rule"]):
        return False
    # Gaps-aware classification. Judgment findings only: deterministic
    # findings never carry the flag, so "acknowledged": true never matches
    # one (bluf/tests/README.md, FINDINGS.md "Gaps-aware mode").
    if "acknowledged" in rule_spec:
        if bool(finding.get("acknowledged")) != rule_spec["acknowledged"]:
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


def grade_lint(runs, only, results):
    errors = []
    for md, expected in fixtures(only):
        before = len(errors)
        verdicts = []
        for i in range(runs):
            payload = results[("lint", md.stem, i)]
            if isinstance(payload, Exception):
                fail(errors, f"{md.name} run {i + 1}: {payload}")
                continue
            verdicts.append(grade_lint_run(md, expected, payload, errors))
        if len({json.dumps(v) for v in verdicts}) > 1:
            fail(errors, f"{md.name}: runs disagree on "
                         "must_find/must_not_find — variance is a failure")
        if len(errors) == before:
            print(f"  ok   {md.name}: {runs} run(s) agree")
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


def grade_rewrite(runs, only, results):
    errors = []
    for md, expected in fixtures(only):
        if "rewrite" not in expected:
            continue
        before = len(errors)
        for i in range(runs):
            payload = results[("rewrite", md.stem, i)]
            if isinstance(payload, Exception):
                fail(errors, f"{md.name} run {i + 1}: {payload}")
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
        if len(errors) == before:
            print(f"  ok   {md.name}: {runs} rewrite run(s) clean")
    return errors


# Matching semantics are specified in bluf/tests/triage/README.md; this is
# their implementation. Change them there first.
FACT_TYPES = {"decision", "commitment", "number", "risk", "claimed_state"}
GAP_SLOTS = ("owner", "date", "decider", "decision", "value", "baseline",
             "denominator")
GOLD_SCALARS = ("owner", "date", "decider", "value", "baseline",
                "provenance", "speaker", "message_date")
GROUNDED_FIELDS = ("owner", "date", "decider", "value", "baseline")
FIRST_PERSON = re.compile(r"\b(I|I'll|I'd|I'm|my)\b")
MONTH = (r"(jan(uary)?|feb(ruary)?|mar(ch)?|apr(il)?|may|jun(e)?|jul(y)?"
         r"|aug(ust)?|sep(t|tember)?|oct(ober)?|nov(ember)?|dec(ember)?)")
CALENDAR_DATE = re.compile(
    r"(?i)\b" + MONTH + r"\b\.?\s*\d"
    r"|\b\d{1,2}(st|nd|rd|th)?\s+(of\s+)?" + MONTH + r"\b"
    r"|\b\d{4}-\d{2}(-\d{2})?\b"
    r"|\b\d{1,2}/\d{1,2}\b")
RULE_NUMBER = re.compile(r"(?i)\bsee[- ]?100\b|\brule\s*\d")


def contains_any(wanted, blob):
    """about_contains semantics: a string, a list of alternatives, or
    absent (matches anything)."""
    if isinstance(wanted, str):
        wanted = [wanted] if wanted else []
    return not wanted or any(w.lower() in blob for w in wanted)


def gold_fact_matches(skill_fact, gold_fact):
    if gold_fact.get("type") not in ("*", skill_fact.get("type")):
        return False
    for key in GOLD_SCALARS:
        if key in gold_fact and (str(gold_fact[key]).lower()
                                 not in str(skill_fact.get(key, "")).lower()):
            return False
    want = gold_fact.get("quote_contains", "*")
    if want != "*" and want.lower() not in skill_fact.get(
            "quote", "").lower():
        return False
    for key in gold_fact.get("must_not_have", []):
        if key in skill_fact:
            return False
    return True


def quote_sentences(doc, quote):
    """Every sentence containing an occurrence of the quote, over ALL
    occurrences. Sentences are split crudely inside the containing line.
    ponytail: a sentence spanning a hard line break counts as two; fixture
    prose keeps each sentence on one line."""
    found = []
    at = doc.find(quote)
    while at >= 0:
        start = doc.rfind("\n", 0, at) + 1
        end = doc.find("\n", at + len(quote))
        line = doc[start: end if end >= 0 else len(doc)]
        qs, qe = at - start, at - start + len(quote)
        # A boundary is punctuation followed by whitespace and a capital —
        # a period inside a decimal (2.9%) never splits.
        cuts = ([0] + [m.end() for m in re.finditer(
            r"[.!?]+(?=\s+[\"'(]?[A-Z])", line)] + [len(line)])
        for a, b in zip(cuts, cuts[1:]):
            if a < qe and b > qs:
                found.append(line[a:b])
        at = doc.find(quote, at + 1)
    return found


def message_speaker(doc, quote):
    """The From: name of the thread message holding the quote, matched by
    quote-nesting depth. ponytail: depth heuristic for pasted email threads;
    exotic quoting styles fall back to None (no first-person credit)."""
    at = doc.find(quote)
    if at < 0:
        return None

    def depth(line):
        return re.match(r"[\s>]*", line).group().count(">")

    lines = doc[:at].split("\n")
    current = (lines[-1] if lines else "") + doc[at:].split("\n", 1)[0]
    want = depth(current)
    for line in reversed(lines[:-1]):
        m = re.match(r"[\s>]*From:\s*([A-Za-z]+)", line)
        if m and depth(line) == want:
            return m.group(1)
    return None


def field_grounded(doc, fact, key, is_thread):
    """Fabrication test for one scalar field. stated: the value must sit in
    a sentence holding the quote (any occurrence), or resolve an explicit
    first person to the message's own speaker. inferred: the value must at
    least exist in the document, and the inference must be shown."""
    value = str(fact[key]).lower()
    if fact.get("provenance") == "inferred":
        return value in doc.lower()
    sentences = quote_sentences(doc, fact.get("quote", ""))
    if any(value in s.lower() for s in sentences):
        return True
    if (is_thread and key in ("owner", "decider")
            and str(fact[key]) == str(fact.get("speaker", ""))
            and fact.get("speaker") == message_speaker(doc,
                                                      fact.get("quote", ""))
            and any(FIRST_PERSON.search(s) for s in sentences)):
        return True
    return False


def gap_matches(gap, spec, strict=False):
    """strict=True (gaps_must_not_include): about field only — a trap must
    key on the claim, not on a long quote that happens to contain the
    phrase. Lenient (gaps_must_include): about + quote."""
    if (str(spec.get("missing", "")).lower()
            not in str(gap.get("missing", "")).lower()):
        return False
    blob = str(gap.get("about", "")).lower()
    if not strict:
        blob += " " + str(gap.get("quote", "")).lower()
    return contains_any(spec.get("about_contains", ""), blob)


def grade_triage_run(md, gold, payload, errors):
    doc = md.read_text()
    facts = payload.get("facts", [])
    gaps = payload.get("gaps", [])
    questions = payload.get("questions", [])
    is_thread = bool(gold.get("is_thread"))
    verdict = []

    # Only gold-anchored checks join the cross-run variance verdict.
    # Payload-derived keys (a fact's own quote) legitimately differ
    # between runs; tracking them made all-pass runs "disagree".
    UNSTABLE = {"grounded-quote", "grounded-field", "thread-attribution",
                "fact-shape", "gap-shape"}

    def check(kind, spec, ok):
        if kind not in UNSTABLE:
            verdict.append((kind, json.dumps(spec, sort_keys=True),
                            bool(ok)))
        return ok

    # Contract shape, every run.
    if not check("verdict-line", "verdict nonempty",
                 str(payload.get("verdict", "") or "").strip()):
        fail(errors, f"{md.name}: missing verdict (the lead line)")
    if not check("budget-facts", "facts<=12", len(facts) <= 12):
        fail(errors, f"{md.name}: {len(facts)} facts — budget is 12")
    ranks = [g.get("rank") for g in gaps]
    if not check("budget-gaps", "gaps<=5,int ranks unique from 1",
                 len(gaps) <= 5 and all(isinstance(r, int) for r in ranks)
                 and sorted(ranks) == list(range(1, len(gaps) + 1))):
        fail(errors, f"{md.name}: gaps break the budget (max 5, integer "
                     "ranks unique from 1)")
    if not check("budget-questions", "questions<=5", len(questions) <= 5):
        fail(errors, f"{md.name}: {len(questions)} questions — budget is 5")
    if not check("no-rule-numbers", "output carries no rule number",
                 not RULE_NUMBER.search(json.dumps(payload))):
        fail(errors, f"{md.name}: SEE-100 rule number in triage output")

    # Per-fact contract checks and fabrication grounding. Grounding runs on
    # EVERY fact — matching a gold entry is no licence to invent the fields
    # the entry does not pin.
    clean = []
    for f in facts:
        nulls = sorted(k for k, v in f.items() if v is None)
        if nulls:
            check("fact-shape", nulls, False)
            fail(errors, f"{md.name}: null field(s) {nulls} — the contract "
                         "says omit absent fields")
        f = {k: v for k, v in f.items() if v is not None}
        clean.append(f)
        if not check("fact-shape", f.get("type"),
                     f.get("type") in FACT_TYPES):
            fail(errors, f"{md.name}: invented fact type "
                         f"{f.get('type')!r} — the five types are closed")
        thread_ok = (all(k in f for k in ("speaker", "message_date"))
                     if is_thread
                     else not any(k in f for k in ("speaker",
                                                   "message_date")))
        if not check("thread-attribution", f.get("quote", ""), thread_ok):
            fail(errors, f"{md.name}: speaker/message_date wrong for "
                         f"is_thread={is_thread} on {f.get('quote', '')!r}")
        if f.get("provenance") == "inferred" and not f.get("inference"):
            check("fact-shape", "inference", False)
            fail(errors, f"{md.name}: provenance 'inferred' without the "
                         "inference shown")
        quote = f.get("quote", "")
        if not check("grounded-quote", quote, bool(quote) and quote in doc):
            fail(errors, f"{md.name}: fabricated/mangled quote {quote!r}")
            continue
        for key in GROUNDED_FIELDS:
            if key in f and not field_grounded(doc, f, key, is_thread):
                fail(errors, f"{md.name}: fact asserts {key}={f[key]!r} "
                             "unsupported by the sentence holding its quote")
    facts = clean

    # A fact whose type is invented over a real quote.
    for spec in gold.get("must_not_extract", []):
        bad = [f for f in facts if gold_fact_matches(f, spec)]
        if not check("must-not-extract", spec, not bad):
            fail(errors, f"{md.name}: extracted what must not exist: "
                         f"{spec.get('type')} over "
                         f"{spec.get('quote_contains')!r}")

    # Recall against the hand-written gold facts.
    for spec in gold.get("facts", []):
        if not check("recall", spec,
                     any(gold_fact_matches(f, spec) for f in facts)):
            fail(errors, f"{md.name}: gold fact missed {spec}")

    # Gap shape: closed slot vocabulary, verbatim quotes.
    for g in gaps:
        slot = str(g.get("missing", "")).lower()
        if not check("gap-shape", slot,
                     any(s in slot for s in GAP_SLOTS)):
            fail(errors, f"{md.name}: gap slot {g.get('missing')!r} outside "
                         "the vocabulary (owner/date/decider/decision/"
                         "value/baseline/denominator)")
        q = g.get("quote")
        if q and not check("gap-shape", q, q in doc):
            fail(errors, f"{md.name}: gap quote not verbatim: {q!r}")

    if gold.get("gaps_must_be_empty"):
        if not check("no-gaps", "gaps==[]", not gaps):
            fail(errors, f"{md.name}: invented {len(gaps)} gap(s) on a "
                         "compliant document")
    for spec in gold.get("gaps_must_include", []):
        if not check("gap-recall", spec,
                     any(gap_matches(g, spec) for g in gaps)):
            fail(errors, f"{md.name}: gold gap missed {spec}")
    # A false gap — claiming absent what the document states — is
    # fabrication in the other direction. Strict matching: about only.
    for spec in gold.get("gaps_must_not_include", []):
        if not check("false-gap", spec,
                     not any(gap_matches(g, spec, strict=True)
                             for g in gaps)):
            fail(errors, f"{md.name}: false gap — claims missing "
                         f"{spec.get('missing')!r} which the document states")

    contradictions = payload.get("contradictions", [])
    for c in contradictions:
        for q in c.get("quotes", []):
            if not check("gap-shape", q, str(q) in doc):
                fail(errors, f"{md.name}: contradiction quote not "
                             f"verbatim: {q!r}")
    for spec in gold.get("contradictions_must_include", []):
        def contra_hit(c):
            quotes_blob = " ".join(map(str, c.get("quotes", []))).lower()
            about_blob = str(c.get("about", "")).lower() + " " + quotes_blob
            return (contains_any(spec.get("about_contains", ""), about_blob)
                    and all(q.lower() in quotes_blob
                            for q in spec.get("quotes_contain", [])))
        if not check("contradiction", spec,
                     any(map(contra_hit, contradictions))):
            fail(errors, f"{md.name}: contradiction missed {spec}")

    unresolved_entries = payload.get("unresolved_dates", [])
    for u in unresolved_entries:
        q = str(u.get("quote", ""))
        if q and not check("gap-shape", q, q in doc):
            fail(errors, f"{md.name}: unresolved-date quote not verbatim: "
                         f"{q!r}")
    unresolved = " ".join(str(u.get("quote", "")) for u in unresolved_entries)
    for token in gold.get("unresolved_must_include", []):
        if not check("unresolved", token,
                     token.lower() in unresolved.lower()):
            fail(errors, f"{md.name}: unresolved date {token!r} not surfaced")
    if gold.get("no_resolved_dates"):
        hit = CALENDAR_DATE.search(json.dumps(payload))
        if not check("no-resolved-dates", "no calendar date", not hit):
            fail(errors, f"{md.name}: calendar date {hit.group()!r} in "
                         "output — the document has no anchor")

    if gold.get("skipped_must_be_nonempty"):
        if not check("skipped", "skipped nonempty",
                     bool(payload.get("skipped"))):
            fail(errors, f"{md.name}: budget must name what it dropped in "
                         "'skipped'")
    if gold.get("verdict_regex"):
        if not check("verdict", gold["verdict_regex"],
                     bool(re.search(gold["verdict_regex"],
                                    str(payload.get("verdict", ""))))):
            fail(errors, f"{md.name}: verdict fails "
                         f"{gold['verdict_regex']!r}")
    return verdict


def grade_triage(runs, only, results):
    errors = []
    for md, gold in triage_fixtures(only):
        before = len(errors)
        verdicts = []
        for i in range(runs):
            payload = results[("triage", md.stem, i)]
            if isinstance(payload, Exception):
                fail(errors, f"{md.name} run {i + 1}: {payload}")
                continue
            verdicts.append(grade_triage_run(md, gold, payload, errors))
        if len({json.dumps(v) for v in verdicts}) > 1:
            fail(errors, f"{md.name}: runs disagree — variance is a failure")
        if len(errors) == before:
            print(f"  ok   {md.name}: {runs} triage run(s) agree")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill",
                        choices=["lint", "rewrite", "triage", "all"])
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--only", nargs="*", help="fixture stems to grade")
    parser.add_argument("--workers", type=int, default=4,
                        help="parallel claude sessions (1 = sequential)")
    args = parser.parse_args()

    print("script layer:")
    errors = grade_script(args.only)

    jobs = []
    if args.skill in ("lint", "all"):
        jobs += [("lint", md, i)
                 for md, _ in fixtures(args.only) for i in range(args.runs)]
    if args.skill in ("rewrite", "all"):
        jobs += [("rewrite", md, i)
                 for md, expected in fixtures(args.only)
                 if "rewrite" in expected for i in range(args.runs)]
    if args.skill in ("triage", "all"):
        jobs += [("triage", md, i)
                 for md, _ in triage_fixtures(args.only)
                 for i in range(args.runs)]
    if jobs:
        print(f"running {len(jobs)} live job(s) on {args.workers} worker(s):")
    results = collect(jobs, args.workers)

    if args.skill in ("lint", "all"):
        print("lint judgment layer:")
        errors += grade_lint(args.runs, args.only, results)
    if args.skill in ("rewrite", "all"):
        print("rewrite:")
        errors += grade_rewrite(args.runs, args.only, results)
    if args.skill in ("triage", "all"):
        print("triage:")
        errors += grade_triage(args.runs, args.only, results)

    print(f"\n{'FAIL' if errors else 'PASS'}: {len(errors)} failure(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
