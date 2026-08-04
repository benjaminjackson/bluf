#!/usr/bin/env python3
"""Deterministic SEE-100 checker. Stdlib only.

Reads a document (path argument, or stdin) and emits findings JSON on stdout
per docs/FINDINGS.md. Everything here is mechanical: dictionary patterns,
sentence length, semicolons, vague quarter references, plus candidate
findings (candidate: true) for hybrid rules a model must confirm.

Identical input gives identical output.
"""
import json
import re
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
DICTIONARY = PLUGIN_ROOT / "data" / "dictionary.json"

MAX_SENTENCE_WORDS = 25
MAX_PARAGRAPH_SENTENCES = 6

# Severity is fixed per rule (FINDINGS.md); never chosen at emit time.
SEVERITY = {"2.1": "warning", "3.4": "warning", "6.4": "warning"}

ABBREVIATIONS = {
    "e.g.", "i.e.", "etc.", "vs.", "cf.", "approx.", "est.", "Inc.", "Corp.",
    "Ltd.", "LLC.", "Co.", "Mr.", "Ms.", "Mrs.", "Dr.", "Jr.", "Sr.", "St.",
    "No.", "Dept.", "Fig.", "Rev.", "Jan.", "Feb.", "Mar.", "Apr.", "Jun.",
    "Jul.", "Aug.", "Sep.", "Sept.", "Oct.", "Nov.", "Dec.",
}

# Function words that break a noun-cluster run (FINDINGS.md, rule 2.1).
CLUSTER_BREAKERS = set("""
the a an this these that those of in on at to for with by from as is are was
were be been being and or but nor so yet we our it its their they them i you
he she not no will would shall can could may might must has have had do does
did than then there who whom whose which when where while after before over
under between into per each every all any some more most less least very also
only if because therefore however up down out about across against along
around during without within
""".split())

VAGUE_QUARTER = re.compile(
    r"\b(?:by|in|until|before)\s+"
    r"(?:Q[1-4]\b|EOQ\b|EOY\b|(?:the\s+)?end\s+of\s+(?:the\s+)?"
    r"(?:quarter|year|month)\b)",
    re.IGNORECASE)
CONCRETE_DATE = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+"
    r"\d{1,2}\b|\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b")
PERCENT = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?:%|x\b)")
BASELINE_MARKER = re.compile(
    r"\b(?:from|vs|versus|baseline|compared|previous|prior|last)\b",
    re.IGNORECASE)
MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
WORD_RE = re.compile(r"\S+")

SKIP_PATTERNS = [
    re.compile(r"\A---\n.*?\n---(?:\n|\Z)", re.DOTALL),        # frontmatter
    re.compile(r"^ {0,3}(?:```|~~~).*?(?:^ {0,3}(?:```|~~~)[^\n]*$|\Z)",
               re.DOTALL | re.MULTILINE),                       # fenced code
    re.compile(r"`[^`\n]+`"),                                   # inline code
    re.compile(r"^[ \t]*>.*$", re.MULTILINE),                   # blockquotes
    re.compile(r"\S+://\S+"),                                   # URLs
    re.compile(r"(?<!\S)(?:/|\./|~/)[\w./-]+"),                 # abs/rel paths
    re.compile(r"(?<!\S)[\w-]+\.(?:md|py|json|js|ts|yml|yaml|txt)\b"),
]


def build_mask(text):
    """Boolean per character: True = inside a skip region."""
    mask = bytearray(len(text))
    for pattern in SKIP_PATTERNS:
        for m in pattern.finditer(text):
            for i in range(m.start(), m.end()):
                mask[i] = 1
    return mask


def line_starts(text):
    starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def to_line_col(starts, idx):
    import bisect
    line = bisect.bisect_right(starts, idx)
    return line, idx - starts[line - 1] + 1


def compile_pattern(pattern):
    body = re.escape(pattern).replace(r"\ ", r"\s+")
    return re.compile(r"(?<!\w)" + body + r"(?!\w)", re.IGNORECASE)


def finding(rule, layer, line, col, quote, message, suggestion=None,
            candidate=False):
    f = {"rule": rule, "layer": layer,
         "severity": SEVERITY.get(rule, "error"), "scope": "span",
         "line": line, "col": col, "quote": quote, "message": message}
    if suggestion:
        f["suggestion"] = suggestion
    if candidate:
        f["candidate"] = True
    return f


def dictionary_findings(text, mask, starts, dictionary):
    found = []
    for entry in dictionary["banned"] + dictionary["prose_bans"]:
        exception_spans = []
        for exc in entry.get("exceptions", []):
            exception_spans += [m.span()
                                for m in compile_pattern(exc).finditer(text)]
        is_candidate = bool(entry.get("condition") or entry.get("scope")
                            or entry.get("confirm"))
        for pattern in entry["patterns"]:
            for m in compile_pattern(pattern).finditer(text):
                if any(mask[i] for i in range(m.start(), m.end())):
                    continue
                if any(s <= m.start() and m.end() <= e
                       for s, e in exception_spans):
                    continue
                line, col = to_line_col(starts, m.start())
                qualifier = entry.get("condition") or entry.get("scope")
                message = f"banned term {m.group(0)!r} (rule {entry['rule']}"
                message += f", if {qualifier})" if qualifier else ")"
                found.append((m.span(), finding(
                    entry["rule"],
                    "judgment" if is_candidate else "deterministic",
                    line, col, m.group(0), message,
                    suggestion=entry.get("instead"),
                    candidate=is_candidate)))
    return found


def semicolon_findings(text, mask, starts):
    found = []
    for i, ch in enumerate(text):
        if ch == ";" and not mask[i]:
            line, col = to_line_col(starts, i)
            found.append(((i, i + 1), finding(
                "8.7", "deterministic", line, col, ";",
                "semicolon (rule 8.7): if both clauses matter, "
                "write two sentences")))
    return found


HEADING = re.compile(r"^ {0,3}#")
TABLE_ROW = re.compile(r"^ {0,3}\|")
LIST_ITEM = re.compile(r"^ {0,3}(?:[-*+]|\d{1,2}[.)])\s+")


def blocks(text, mask, starts):
    """Yield (abs_offset, block_text, is_list_item) prose blocks."""
    offset = 0
    current = None  # [start, end]
    result = []
    for raw in text.splitlines(keepends=True):
        line = raw.rstrip("\n")
        skip = (not line.strip() or HEADING.match(line)
                or TABLE_ROW.match(line)
                or (mask[offset] if offset < len(mask) else False))
        item = LIST_ITEM.match(line)
        if skip:
            if current:
                result.append(current)
                current = None
        elif item:
            if current:
                result.append(current)
            current = [offset + item.end(), offset + len(line), True]
        else:
            if current:
                current[1] = offset + len(line)
            else:
                current = [offset, offset + len(line), False]
        offset += len(raw)
    if current:
        result.append(current)
    return [(s, text[s:e], is_item) for s, e, is_item in result]


BOUNDARY = re.compile(r"[.!?][\"')\]]*(?:\s+|\Z)")


def sentences(block_text, block_start):
    """Split a block into [(abs_offset, sentence_text)]."""
    out = []
    pos = 0
    for m in BOUNDARY.finditer(block_text):
        prior = block_text[pos:m.start() + 1]
        last_word = prior.split()[-1] if prior.split() else ""
        if last_word in ABBREVIATIONS:
            continue
        if re.search(r"\d\.\Z", prior) and re.match(
                r"[.!?]*\s*\d", block_text[m.start():]):
            continue  # decimal or rule number like 4.1
        nxt = block_text[m.end():m.end() + 1]
        if nxt and not (nxt.isupper() or nxt.isdigit() or nxt in "\"'(["):
            continue
        sent = block_text[pos:m.end()].strip()
        if sent:
            out.append((block_start + pos + (len(block_text[pos:m.end()])
                                             - len(block_text[pos:m.end()].lstrip())),
                        sent))
        pos = m.end()
    tail = block_text[pos:].strip()
    if tail:
        out.append((block_start + pos + (len(block_text[pos:])
                                         - len(block_text[pos:].lstrip())), tail))
    return out


def count_words(sentence):
    cleaned = MD_LINK.sub(r"\1", sentence)
    cleaned = re.sub(r"[*_#]+", "", cleaned)
    return sum(1 for tok in cleaned.split()
               if any(c.isalnum() for c in tok))


def structure_findings(text, mask, starts):
    found = []
    for block_start, block_text, is_item in blocks(text, mask, starts):
        sents = sentences(block_text, block_start)
        for abs_off, sent in sents:
            words = count_words(sent)
            line, col = to_line_col(starts, abs_off)
            span = (abs_off, abs_off + len(sent))
            if words > MAX_SENTENCE_WORDS:
                found.append((span, finding(
                    "4.1", "deterministic", line, col, sent,
                    f"sentence has {words} words (max {MAX_SENTENCE_WORDS})")))
            # vague quarter references with no concrete day in the sentence
            if not CONCRETE_DATE.search(sent):
                for m in VAGUE_QUARTER.finditer(sent):
                    mline, mcol = to_line_col(starts, abs_off + m.start())
                    found.append(((abs_off + m.start(), abs_off + m.end()),
                                  finding("8.2", "deterministic", mline, mcol,
                                          m.group(0),
                                          f"vague date {m.group(0)!r}: no "
                                          "calendar day in the sentence",
                                          suggestion="a calendar date")))
            # percentages / multiples with no baseline marker: candidates
            if not BASELINE_MARKER.search(sent):
                for m in PERCENT.finditer(sent):
                    mline, mcol = to_line_col(starts, abs_off + m.start())
                    found.append(((abs_off + m.start(), abs_off + m.end()),
                                  finding("8.6", "judgment", mline, mcol,
                                          m.group(0),
                                          f"{m.group(0)!r} names no baseline "
                                          "or period in its sentence",
                                          candidate=True)))
            # noun-cluster candidates: 4+ words, no function word between
            run = []
            for m in WORD_RE.finditer(sent):
                token = m.group(0).strip(".,:;!?()[]\"'").rstrip("*_")
                if (token and token.replace("-", "").isalpha()
                        and token.lower() not in CLUSTER_BREAKERS):
                    run.append((m.start(), m.end(), token))
                else:
                    run = flush_cluster(run, found, sent, abs_off, starts)
            flush_cluster(run, found, sent, abs_off, starts)
        if not is_item and len(sents) > MAX_PARAGRAPH_SENTENCES:
            line, col = to_line_col(starts, block_start)
            found.append(((block_start, block_start + len(block_text)),
                          finding("6.4", "deterministic", line, col,
                                  sents[0][1],
                                  f"paragraph has {len(sents)} sentences "
                                  f"(max {MAX_PARAGRAPH_SENTENCES})")))
    return found


def flush_cluster(run, found, sent, abs_off, starts):
    if len(run) >= 4:
        start, end = run[0][0], run[-1][1]
        quote = sent[start:end]
        line, col = to_line_col(starts, abs_off + start)
        found.append(((abs_off + start, abs_off + end), finding(
            "2.1", "judgment", line, col, quote,
            f"possible noun cluster of {len(run)} words",
            candidate=True)))
    return []


def check(text, dictionary=None):
    if dictionary is None:
        dictionary = json.loads(DICTIONARY.read_text())
    mask = build_mask(text)
    starts = line_starts(text)
    found = (dictionary_findings(text, mask, starts, dictionary)
             + semicolon_findings(text, mask, starts)
             + structure_findings(text, mask, starts))
    # Sort; on same rule + overlapping span keep the first (deterministic
    # before candidate), so e.g. the 8.2 quarter regex beats the "by EOQ"
    # dictionary candidate.
    found.sort(key=lambda x: (x[0][0], x[0][1],
                              x[1].get("candidate", False), x[1]["rule"]))
    kept = []
    for span, f in found:
        clash = any(f["rule"] == g["rule"] and span[0] < gspan[1]
                    and gspan[0] < span[1] for gspan, g in kept)
        if not clash:
            kept.append((span, f))
    kept.sort(key=lambda x: (x[1]["line"], x[1]["col"], x[1]["rule"]))
    return {"version": 1, "findings": [f for _, f in kept]}


def main():
    if len(sys.argv) > 1:
        text = Path(sys.argv[1]).read_text()
    else:
        text = sys.stdin.read()
    json.dump(check(text), sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
