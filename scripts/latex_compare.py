#!/usr/bin/env python3
"""Compare two LaTeX formulas: structural normalisation and numeric equivalence.

    python latex_compare.py --a "E = m c^{2}" --b "E=mc^2" \
        --symbols c,m,E --output compare.json

Structural comparison ignores typesetting differences (spacing, \\left/\\right,
\\dfrac vs \\frac, redundant braces). Numeric equivalence evaluates both sides at
several random assignments; it is the check to use when two formulas are written
differently but mean the same thing.
"""
import argparse
import importlib.util
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


UNCLEAN = {r"\dfrac": r"\frac", r"\tfrac": r"\frac", r"\left": "", r"\right": "",
           r"\,": "", r"\!": "", r"\;": "", r"\limits": "", r"\displaystyle": ""}


def normalize(latex):
    s = latex or ""
    for k, v in UNCLEAN.items():
        if k:
            s = s.replace(k, v)
    s = re.sub(r"\s+", "", s)
    s = s.replace(r"\cdot", r"\times")
    s = re.sub(r"\\mathrm\{([A-Za-z]+)\}", r"\1", s)
    s = re.sub(r"\\text\{([A-Za-z]+)\}", r"\1", s)
    # drop braces that wrap a single token: {x} -> x, {2} -> 2
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r"\{([A-Za-z0-9])\}", r"\1", s)
    s = s.replace("(", r"\left(").replace(")", r"\right)")
    return s


def structural_equal(a, b):
    return normalize(a) == normalize(b)


def numeric_equivalence(a, b, symbols, samples=6, tol=1e-9, seed=0):
    nc = load("numeric_check")
    try:
        ea, eb = nc.latex_to_python(a), nc.latex_to_python(b)
    except Exception as e:
        return None, "conversion failed: %s" % e
    rng = random.Random(seed)
    checked = 0
    for _ in range(samples):
        vals = {s: rng.uniform(0.5, 2.5) for s in symbols}
        ns = dict(nc.SAFE)
        ns.update(vals)
        try:
            va = eval(ea, {"__builtins__": {}}, ns)
            vb = eval(eb, {"__builtins__": {}}, ns)
        except Exception as e:
            return None, "evaluation failed: %s" % e
        if not (isinstance(va, (int, float)) and isinstance(vb, (int, float))):
            return None, "non-numeric result"
        if abs(va - vb) > tol * max(1.0, abs(va), abs(vb)):
            return False, "differs at %s: %.12g vs %.12g" % (vals, va, vb)
        checked += 1
    return True, "agreed on %d random assignments" % checked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--symbols", default="", help="comma separated free symbols")
    ap.add_argument("--output", default="compare.json")
    a = ap.parse_args()

    symbols = [s for s in (a.symbols or "").replace("，", ",").split(",") if s.strip()]
    report = {"a": a.a, "b": a.b,
              "normalized_a": normalize(a.a), "normalized_b": normalize(a.b),
              "structural_equal": structural_equal(a.a, a.b)}
    if symbols:
        ok, why = numeric_equivalence(a.a, a.b, symbols)
        report["numeric_equivalent"] = ok
        report["numeric_detail"] = why
    json.dump(report, open(a.output, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: report[k] for k in ("structural_equal", "numeric_equivalent")
                      if k in report}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
