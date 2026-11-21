#!/usr/bin/env python3
"""Numerically check a LaTeX formula with the values the material reports.

Usage:
    python numeric_check.py --latex "<latex>" --values values.json \
        --symbol-table symbols.csv --output check.json

values.json: {"N": 6.022e23, "k_B": 1.380649e-23, "T": 300.0, "Theta": 1000.0}

The converter below is self-contained: it needs no antlr4, no sympy and no LaTeX
installation, so it also runs in a bare evaluation container. Missing values are
reported as missing; a formula the converter cannot handle is reported as such
instead of being silently scored 0.
"""
import argparse
import csv
import json
import math
import re

GREEK = {
    "alpha": "alpha", "beta": "beta", "gamma": "gamma", "delta": "delta",
    "epsilon": "epsilon", "varepsilon": "varepsilon", "zeta": "zeta", "eta": "eta",
    "theta": "theta", "vartheta": "vartheta", "iota": "iota", "kappa": "kappa",
    "lambda": "lambda", "mu": "mu", "nu": "nu", "xi": "xi", "pi": "pi", "rho": "rho",
    "sigma": "sigma", "tau": "tau", "upsilon": "upsilon", "phi": "phi",
    "varphi": "varphi", "chi": "chi", "psi": "psi", "omega": "omega",
    "Gamma": "Gamma", "Delta": "Delta", "Theta": "Theta", "Lambda": "Lambda",
    "Xi": "Xi", "Pi": "Pi", "Sigma": "Sigma", "Phi": "Phi", "Psi": "Psi",
    "Omega": "Omega", "hbar": "hbar",
}


def bracket_balance(latex):
    bad = []
    for open_, close in (("{", "}"), ("(", ")"), ("[", "]")):
        if latex.count(open_) != latex.count(close):
            bad.append({"pair": open_ + close,
                        "open": latex.count(open_), "close": latex.count(close)})
    return bad


def _match_brace(s, i):
    """Index just past the group starting at s[i] == '{'."""
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return j + 1
    raise ValueError("unbalanced braces")


def _rewrite_commands(s, name, template):
    """Rewrite \\name{arg1}{arg2} ... using innermost-first matching."""
    out = s
    while True:
        i = out.find("\\" + name + "{")
        if i < 0:
            return out
        j = _match_brace(out, i + len(name) + 1)
        try:
            k = _match_brace(out, j)
            args = (out[i + len(name) + 2:j - 1], out[j + 1:k - 1])
            out = out[:i] + template.format(*args) + out[k:]
        except (ValueError, IndexError):
            return out


TOKEN = re.compile(r"\d+\.\d*(?:[eE][-+]?\d+)?|\d+(?:[eE][-+]?\d+)?|[A-Za-z_][A-Za-z0-9_]*"
                   r"|\*\*|[-+*/(),]|\S")
FUNCS = {"sqrt", "exp", "log", "log10", "sin", "cos", "tan", "asin", "acos",
         "atan", "sinh", "cosh", "tanh", "abs", "min", "max", "fabs"}


SAFE = {k: getattr(math, k, None) for k in
        ("sqrt", "exp", "log", "log10", "sin", "cos", "tan", "asin", "acos",
         "atan", "sinh", "cosh", "tanh", "fabs", "floor")}
SAFE.update({"pi": math.pi, "e": math.e, "abs": abs, "min": min, "max": max})

KNOWN_NAMES = set(GREEK.values()) | FUNCS | set(SAFE)


def split_identifier(tok):
    """`Nk_B` in hand-written LaTeX means N * k_B; spelled-out names stay whole."""
    base, _, sub = tok.partition("_")
    if base in KNOWN_NAMES or len(base) <= 1 or not base.isalpha():
        return [tok]
    letters = list(base)
    if sub:
        letters[-1] = letters[-1] + "_" + sub
    return letters


def insert_products(s):
    """Turn `n R T` and `2\\pi m` into explicit products, keeping f(x) intact."""
    out, prev = [], None
    for m in TOKEN.finditer(s):
        tok = m.group(0)
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", tok):
            parts = split_identifier(tok)
            if len(parts) > 1:
                for k, part in enumerate(parts):
                    if prev is not None and (k > 0 or prev[0].isalnum() or prev[0] in "_)]"):
                        out.append("*")
                    out.append(part)
                    prev = part
                continue
        if prev is not None:
            left_ok = prev[0].isalnum() or prev[0] in "_)]"
            right_ok = tok[0].isalnum() or tok[0] in "(["
            if left_ok and right_ok and not (prev in FUNCS and tok == "("):
                out.append("*")
        out.append(tok)
        prev = tok
    return "".join(out)


FUNCTION_NAMES = {"exp": "exp", "log": "log", "ln": "log", "sin": "sin",
                  "cos": "cos", "tan": "tan", "max": "max", "min": "min",
                  "abs": "abs", "det": "det"}


def latex_to_python(latex):
    s = latex
    if s.count("=") == 1:            # C_p = <expr> -> evaluate <expr>
        s = s.split("=", 1)[1]
    s = s.replace("\\left", "").replace("\\right", "")
    s = s.replace("\\,", "").replace("\\!", "").replace("\\;", "")
    s = s.replace("\\cdot", "*").replace("\\times", "*")
    s = s.replace("\\pi", "pi")
    for name in sorted(GREEK, key=len, reverse=True):
        if name != "pi":
            s = s.replace("\\" + name, GREEK[name])
    for latex_name, py_name in FUNCTION_NAMES.items():
        s = s.replace("\\" + latex_name, " " + py_name)
    s = s.replace("\\mathrm", "").replace("\\text", "")
    s = re.sub(r"\\operatorname\{([^{}]*)\}", r"\1", s)
    s = _rewrite_commands(s, "frac", "(({0})/({1}))")
    s = _rewrite_commands(s, "dfrac", "(({0})/({1}))")
    while "\\sqrt{" in s:
        i = s.find("\\sqrt{")
        j = _match_brace(s, i + 5)
        s = s[:i] + "sqrt(" + s[i + 6:j - 1] + ")" + s[j:]
    # subscripts fold into identifiers, superscripts become powers
    s = re.sub(r"\}\s*_\s*\{([^{}]*)\}", r"_\1}", s)          # {k}_{B} -> {k_B}
    s = re.sub(r"_\s*\{([^{}]*)\}", r"_\1", s)
    s = re.sub(r"\}\s*\^\s*\{([^{}]*)\}", r"**(\1)}", s)
    s = re.sub(r"\^\s*\{([^{}]*)\}", r"**(\1)", s)
    s = re.sub(r"\^\s*(-?\d+(?:\.\d+)?)", r"**(\1)", s)
    s = s.replace("{", "(").replace("}", ")")
    s = insert_products(s)
    return s.strip()


def identifiers(expr):
    return sorted({m for m in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr)
                   if m not in SAFE})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--latex", required=True)
    ap.add_argument("--values", help="json file with numeric assignments")
    ap.add_argument("--symbol-table", help="csv written by symbol_table.py")
    ap.add_argument("--output", default="check.json")
    ap.add_argument("--expected-range", help="material's stated range, e.g. '1e-30,1e-20'")
    a = ap.parse_args()

    report = {"latex": a.latex, "checks": {}, "status": "success", "notes": []}
    report["checks"]["bracket_balance"] = bracket_balance(a.latex) or "ok"

    defined = set()
    if a.symbol_table:
        try:
            with open(a.symbol_table, encoding="utf-8-sig") as f:
                defined = {row["symbol"] for row in csv.DictReader(f)}
        except FileNotFoundError:
            report["notes"].append("symbol table not found; undefined-symbol check skipped")

    values = {}
    if a.values:
        values = json.load(open(a.values, encoding="utf-8-sig"))

    try:
        expr = latex_to_python(a.latex)
    except Exception as e:
        report["status"] = "partial"
        report["checks"]["converted"] = "conversion_failed: %s" % e
        json.dump(report, open(a.output, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps({"status": report["status"], "output": a.output}, ensure_ascii=False))
        return

    report["checks"]["converted"] = expr
    ids = identifiers(expr)
    report["checks"]["free_symbols"] = ids
    if defined:
        report["checks"]["undefined_symbols"] = sorted(
            s for s in ids if s not in defined and s.split("_")[0] not in defined) or "none"
    missing = [s for s in ids if s not in values]
    report["checks"]["missing_values"] = missing or "none"

    if missing:
        report["status"] = "partial"
        report["checks"]["value"] = "not_computed"
        report["notes"].append("no value reported for: %s" % missing)
    else:
        namespace = dict(SAFE)
        namespace.update(values)
        try:
            val = eval(expr, {"__builtins__": {}}, namespace)  # restricted namespace
            report["checks"]["value"] = float(val)
            report["checks"]["intermediates"] = {
                "expression": expr,
                "substituted": {k: values[k] for k in ids},
            }
            if a.expected_range:
                lo, hi = [float(x) for x in a.expected_range.replace("，", ",").split(",")]
                inside = lo <= float(val) <= hi if lo <= hi else hi <= float(val) <= lo
                report["checks"]["expected_range"] = {"low": lo, "high": hi,
                                                      "value": float(val), "inside": inside}
                if not inside:
                    report["notes"].append(
                        "computed value %.6g falls outside the range stated in the material "
                        "%.6g..%.6g: check symbol, unit or order of magnitude" % (float(val), lo, hi))
                    if report["status"] == "success":
                        report["status"] = "partial"
        except Exception as e:
            report["status"] = "partial"
            report["checks"]["value"] = "evaluation_failed: %s" % e
            report["notes"].append("formula could not be evaluated with the supplied values")

    try:  # optional cross-check when sympy is usable
        import sympy as sp
        ns = {k: sp.Symbol(k) for k in ids}
        ns.update({k: sp.Float(v) for k, v in values.items()})
        ns.update({"sqrt": sp.sqrt, "exp": sp.exp, "log": sp.log, "pi": sp.pi,
                   "sin": sp.sin, "cos": sp.cos, "tan": sp.tan})
        report["checks"]["sympy_crosscheck"] = str(sp.simplify(eval(expr, {"__builtins__": {}}, ns)))[:200]
    except Exception:
        report["checks"]["sympy_crosscheck"] = "skipped"

    json.dump(report, open(a.output, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"status": report["status"], "value": report["checks"].get("value"),
                      "output": a.output}, ensure_ascii=False))


if __name__ == "__main__":
    main()
