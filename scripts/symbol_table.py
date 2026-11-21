#!/usr/bin/env python3
"""Build the first two columns of the variable table from extracted formulas.

Usage:
    python symbol_table.py --formulas formulas.jsonl [--text body.txt] \
        --output symbols.csv

Columns: symbol, first_formula_id, occurrences, latex_example, definition_status
The definition/unit/range columns are intentionally left for the reading step:
the script never guesses a unit, it marks the row as undefined_in_material.
"""
import argparse
import csv
import json
import re

TOKEN = re.compile(r"\\[A-Za-z]+|[{}\^_][^ ]?|[A-Za-z]+|\d+(?:\.\d+)?")
GREEK = re.compile(r"^\\[A-Za-z]+$")


BASE_SUB = re.compile(
    r"(?:\{([^{}]+)\}|([A-Za-z]|\\[A-Za-z]+))\s*_\s*(?:\{([^{}]*)\}|([A-Za-z0-9]+))")


def symbols_of(latex):
    """Return the symbols a formula introduces.

    A base with a subscript is reported as one symbol (k_{B} -> k_B); superscripts
    are powers of the same symbol and are ignored.
    """
    found = []
    consumed = []
    for m in BASE_SUB.finditer(latex):
        base = (m.group(1) or m.group(2) or "").strip("{} ")
        sub = m.group(3) if m.group(3) is not None else m.group(4)
        found.append("%s_%s" % (base.lstrip("\\"), sub))
        consumed.append((m.start(), m.end()))
    rest = []
    pos = 0
    for s, e in consumed:
        rest.append(latex[pos:s])
        pos = e
    rest.append(latex[pos:])
    stripped = " ".join(rest)

    i, n = 0, len(stripped)
    while i < n:
        c = stripped[i]
        if c == "\\":
            m = re.match(r"\\[A-Za-z]+", stripped[i:])
            if not m:
                i += 1
                continue
            name = m.group(0)
            i += len(name)
            if name not in ("\\frac", "\\text", "\\mathrm", "\\sqrt", "\\left",
                            "\\right", "\\begin", "\\end"):
                found.append(name.lstrip("\\"))
            continue
        if c.isalpha():
            m = re.match(r"[A-Za-z]+", stripped[i:])
            if m:
                word = m.group(0)
                if len(word) <= 2:
                    found.append(word)
                i += len(word)
                continue
            found.append(c)          # non-ASCII letter kept verbatim
            i += 1
            continue
        i += 1
    constants = {"pi", "infty", "ldots", "cdot", "times", "to", "le", "ge", "in",
                 "sum", "int", "prod", "partial", "nabla", "approx", "neq", "pm"}
    return [s for s in found if s.lstrip("\\") not in constants]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--formulas", required=True)
    ap.add_argument("--text", help="plain-text body used to look for definitions")
    ap.add_argument("--output", default="symbols.csv")
    a = ap.parse_args()

    body = open(a.text, encoding="utf-8", errors="replace").read() if a.text else ""
    rows = [json.loads(l) for l in open(a.formulas, encoding="utf-8") if l.strip()]

    # body.txt may carry "[p12] ..." markers, one paragraph per line
    paragraphs = []
    for line in body.splitlines():
        m = re.match(r"\[([^\]]+)\]\s*(.*)", line)
        if m:
            paragraphs.append((m.group(1), m.group(2)))
        elif line.strip():
            paragraphs.append((None, line))

    def locate(sym):
        base = sym.split("_")[0]
        for pid, text in paragraphs:
            if re.search(r"(?<![A-Za-z])%s(?![A-Za-z])" % re.escape(base), text):
                return pid
        return None

    table = {}
    for r in rows:
        latex = r.get("latex") or ""
        for s in symbols_of(latex):
            key = s.lstrip("\\")
            rec = table.setdefault(key, {"first": r.get("id"), "count": 0, "example": latex[:80]})
            rec["count"] += 1

    with open(a.output, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "first_formula_id", "occurrences", "latex_example",
                    "meaning", "unit", "range", "first_body_location", "definition_status"])
        for key, rec in sorted(table.items(), key=lambda kv: (-kv[1]["count"], kv[0])):
            loc = locate(key)
            in_body = loc is not None
            w.writerow([key, rec["first"], rec["count"], rec["example"],
                        "", "", "", loc or "", 
                        "mentioned_in_body(%s)" % loc if in_body else "undefined_in_material"])
    print(json.dumps({"symbols": len(table), "output": a.output,
                      "undefined": sum(1 for k in table if not body)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
