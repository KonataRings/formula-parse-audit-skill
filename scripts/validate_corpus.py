#!/usr/bin/env python3
"""Coverage report for publisher XML you already have on disk.

    python validate_corpus.py --corpus path/to/xml_dir --output corpus_report.json

For every MathML formula it reports how it was obtained (publisher LaTeX via
<tex-math> or an <annotation>, a source alttext, or reconstruction), whether the
source id and the equation label survived, and whether the LaTeX looks truncated.
Use it to see what the extractor does on a given publisher before trusting it.
"""
import argparse
import importlib.util
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, help="directory containing .xml files")
    ap.add_argument("--output", default="corpus_report.json")
    ap.add_argument("--show", type=int, default=5, help="how many sample formulas to print")
    a = ap.parse_args()

    fe = load("formula_extract")
    files = [f for f in sorted(os.listdir(a.corpus)) if f.lower().endswith(".xml")]
    if not files:
        sys.exit("no .xml files in %s" % a.corpus)

    per_file, totals, methods = [], Counter(), Counter()
    for name in files:
        path = os.path.join(a.corpus, name)
        rows = fe.scan_file(path)
        text = open(path, encoding="utf-8", errors="replace").read()
        rec = {"file": name, "formulas": len(rows),
               "disp_formula": text.count("<disp-formula"),
               "inline_formula": text.count("<inline-formula"),
               "with_id": sum(1 for r in rows if r.get("id")),
               "with_label": sum(1 for r in rows if r.get("label")),
               "empty_latex": sum(1 for r in rows if not (r.get("latex") or "").strip()),
               "truncated": sum(1 for r in rows if r.get("truncated")),
               "methods": dict(Counter(r.get("method") for r in rows))}
        per_file.append(rec)
        methods.update(r.get("method") for r in rows)
        for k in ("formulas", "disp_formula", "inline_formula", "with_id",
                  "with_label", "empty_latex", "truncated"):
            totals[k] += rec[k]

    n = totals["formulas"] or 1
    summary = dict(totals)
    summary["source_latex_share"] = round(
        (methods.get("source_texmath", 0) + methods.get("source_annotation", 0)) / n, 4)
    summary["methods"] = dict(methods)

    report = {"corpus": os.path.abspath(a.corpus), "files": len(files),
              "summary": summary, "per_file": per_file}
    json.dump(report, open(a.output, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(json.dumps(summary, ensure_ascii=False))
    for rec in per_file:
        print("%-28s %5d formulas  id=%d  label=%d  empty=%d  truncated=%d  %s" % (
            rec["file"], rec["formulas"], rec["with_id"], rec["with_label"],
            rec["empty_latex"], rec["truncated"], rec["methods"]))

    sample_rows = []
    for rec in per_file[:1]:
        sample_rows = fe.scan_file(os.path.join(a.corpus, rec["file"]))[: a.show]
    for r in sample_rows:
        print("[%s|%s] %s" % (r.get("id"), r.get("method"), (r.get("latex") or "")[:120]))


if __name__ == "__main__":
    main()
