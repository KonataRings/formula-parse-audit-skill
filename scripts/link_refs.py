#!/usr/bin/env python3
"""Link in-text equation references to the formulas that carry the labels.

    python link_refs.py --formulas formulas.jsonl --body body.txt --output refs.json

Publishers number displayed equations in a <label> ("(3)") and refer to them in
the prose ("as shown in (3)"). This script turns those mentions into explicit
edges, so a derivation step can point at the formula it depends on instead of a
page number.
"""
import argparse
import json
import os
import re

REF = re.compile(r"(?:Eq\.?|Equation|式)?\s*\(?(\d{1,3}[a-z]?)\)")


def normalize_label(text):
    if not text:
        return None
    m = re.search(r"\(?([0-9]{1,3}[a-z]?)\)?", text.strip())
    return m.group(1) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--formulas", required=True)
    ap.add_argument("--body", required=True)
    ap.add_argument("--output", default="refs.json")
    a = ap.parse_args()

    formulas = [json.loads(l) for l in open(a.formulas, encoding="utf-8") if l.strip()]
    by_label = {}
    for f in formulas:
        key = normalize_label(f.get("label"))
        if key:
            by_label[key] = f["id"]

    edges, unresolved = [], []
    paragraphs = 0
    if os.path.exists(a.body):
        for line in open(a.body, encoding="utf-8"):
            m = re.match(r"\[([^\]]+)\]\s*(.*)", line.strip())
            pid, text = (m.group(1), m.group(2)) if m else (None, line.strip())
            if not text:
                continue
            paragraphs += 1
            for ref in set(REF.findall(text)):
                if ref in by_label:
                    edges.append({"paragraph": pid, "label": "(%s)" % ref,
                                  "formula_id": by_label[ref],
                                  "evidence": text[:120]})
                elif ref.isdigit() and len(ref) <= 2:
                    unresolved.append({"paragraph": pid, "label": "(%s)" % ref,
                                       "reason": "no formula carries this label"})

    report = {"paragraphs": paragraphs, "labeled_formulas": by_label,
              "edges": edges, "unresolved": unresolved}
    json.dump(report, open(a.output, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"paragraphs": paragraphs, "labeled_formulas": len(by_label),
                      "edges": len(edges), "unresolved": len(unresolved),
                      "output": a.output}, ensure_ascii=False))


if __name__ == "__main__":
    main()
