#!/usr/bin/env python3
"""Dimensional check: evaluate the same Python expression with units attached.

    python dimension_check.py --latex "C_p=\\frac{12}{5}\\pi^4 N k_B (T/\\Theta)^3" \
        --units units.json --expect "J/K" [--output dims.json]

units.json: {"k_B": "J/K", "T": "K", "N": "1", "Theta": "K"}

The point is to catch a unit error that a value-only check cannot see: a formula
that looks right but returns joule instead of joule per kelvin is flagged even
when the number is plausible. Dimensionless inputs use "1".
"""
import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Unit:
    __slots__ = ("dims", "factor")

    def __init__(self, dims=None, factor=1.0):
        self.dims = {k: v for k, v in (dims or {}).items() if abs(v) > 1e-12}
        self.factor = float(factor)

    def _combine(self, other, sign):
        if not isinstance(other, Unit):
            other = Unit({}, float(other))
        dims = dict(self.dims)
        for k, v in other.dims.items():
            dims[k] = dims.get(k, 0) + sign * v
            if abs(dims[k]) < 1e-12:
                del dims[k]
        return Unit(dims, self.factor * (other.factor ** sign))

    def __mul__(self, other):
        return self._combine(other, 1)

    __rmul__ = __mul__

    def __truediv__(self, other):
        return self._combine(other, -1)

    def __rtruediv__(self, other):
        return Unit({}, float(other))._combine(self, -1)

    def __pow__(self, p):
        return Unit({k: v * p for k, v in self.dims.items()}, self.factor ** p)

    def __add__(self, other):
        o = other if isinstance(other, Unit) else Unit({}, float(other))
        if o.dims != self.dims:
            raise ValueError("dimension mismatch in sum: %s vs %s" % (self, o))
        return self

    __radd__ = __add__

    def __sub__(self, other):
        return self.__add__(other)

    __rsub__ = __sub__

    def __neg__(self):
        return self

    def __pos__(self):
        return self

    @property
    def dimensionless(self):
        return not self.dims

    def __str__(self):
        if not self.dims:
            return "1"
        num = " ".join("%s^%g" % (k, v) for k, v in sorted(self.dims.items()) if v > 0)
        den = " ".join("%s^%g" % (k, -v) for k, v in sorted(self.dims.items()) if v < 0)
        return num + ("/" + den if den else "")


BASE = {"kg": Unit({"kg": 1}), "m": Unit({"m": 1}), "s": Unit({"s": 1}),
        "A": Unit({"A": 1}), "K": Unit({"K": 1}), "mol": Unit({"mol": 1})}
DERIVED = {
    "N": Unit({"kg": 1, "m": 1, "s": -2}),
    "J": Unit({"kg": 1, "m": 2, "s": -2}),
    "W": Unit({"kg": 1, "m": 2, "s": -3}),
    "Pa": Unit({"kg": 1, "m": -1, "s": -2}),
    "Hz": Unit({"s": -1}),
    "C": Unit({"A": 1, "s": 1}),
    "V": Unit({"kg": 1, "m": 2, "s": -3, "A": -1}),
    "F": Unit({"kg": -1, "m": -2, "s": 4, "A": 2}),
    "ohm": Unit({"kg": 1, "m": 2, "s": -3, "A": -2}),
    "T": Unit({"kg": 1, "s": -2, "A": -1}),
    "eV": Unit({"kg": 1, "m": 2, "s": -2}, 1.602176634e-19),
    "dimensionless": Unit(),
}
UNITS = dict(BASE)
UNITS.update(DERIVED)


def _tokens(text):
    text = (text or "1").strip().replace("·", "*").replace("μ", "u")
    text = text.replace("**", "^")
    text = __import__("re").sub(r"\s+", "*", text)
    return __import__("re").findall(r"[A-Za-z_]+|\d+\.?\d*|\^|[*/()]", text)


def parse_unit(text):
    """Parse 'J/K', 'kg m^2 s^-2', 'J/(mol K)', 'm/s^2', '1'."""
    toks = _tokens(text)
    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def take():
        t = peek()
        pos[0] += 1
        return t

    def parse_term():
        t = take()
        if t is None:
            raise ValueError("unexpected end of unit %r" % text)
        if t == "(":
            v = parse_expr()
            if take() != ")":
                raise ValueError("unbalanced parentheses in %r" % text)
        elif t.replace(".", "").isdigit():
            v = Unit({}, float(t))
        elif t in UNITS:
            v = UNITS[t]
        else:
            raise ValueError("unknown unit %r" % t)
        if peek() == "^":
            take()
            e = take()
            if e is None:
                raise ValueError("dangling exponent in %r" % text)
            v = v ** float(e)
        return v

    def starts_term(t):
        return t is not None and (t == "(" or t[0].isalnum() or t[0] == "_")

    def parse_expr():
        value = parse_term()
        while True:
            t = peek()
            if t in ("*", "/"):
                take()
                rhs = parse_term()
                value = value * rhs if t == "*" else value / rhs
            elif starts_term(t):
                value = value * parse_term()
            else:
                return value

    return parse_expr()


NUMERIC = load("numeric_check")


def evaluate_with_units(latex, units):
    expr = NUMERIC.latex_to_python(latex)
    ns = {"__builtins__": {}}
    for name, utext in units.items():
        ns[name] = parse_unit(utext)
    ns.update({k: Unit() for k in NUMERIC.SAFE if k not in ("sqrt",)})
    ns["sqrt"] = lambda u: u ** 0.5 if isinstance(u, Unit) else Unit({}, float(u) ** 0.5)
    for fname in ("exp", "log", "log10", "sin", "cos", "tan", "abs"):
        def guard(x, _n=fname):
            u = x if isinstance(x, Unit) else Unit({}, float(x))
            if not u.dimensionless:
                raise ValueError("%s() needs a dimensionless argument, got %s" % (_n, u))
            return Unit()
        ns[fname] = guard
    return expr, eval(expr, ns)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--latex", required=True)
    ap.add_argument("--units", required=True, help="json: symbol -> unit string")
    ap.add_argument("--expect", help="unit the material states for the result")
    ap.add_argument("--output", default="dims.json")
    a = ap.parse_args()

    raw = json.load(open(a.units, encoding="utf-8-sig"))
    units = {k: v for k, v in raw.items() if not k.startswith("_")}
    report = {"latex": a.latex, "units": units, "status": "success", "notes": []}
    try:
        expr, result = evaluate_with_units(a.latex, units)
        report["expression"] = expr
        report["result_dimension"] = str(result)
        report["result_factor"] = result.factor
    except Exception as e:
        report["status"] = "failed"
        report["error"] = "%s: %s" % (type(e).__name__, e)
        json.dump(report, open(a.output, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps({"status": report["status"], "error": report["error"]}, ensure_ascii=False))
        return 1

    if a.expect:
        want = parse_unit(a.expect)
        report["expected_dimension"] = str(want)
        match = want.dims == result.dims
        report["dimension_match"] = match
        if not match:
            report["status"] = "partial"
            report["notes"].append("computed dimension %s differs from the stated %s"
                                   % (result, want))
        scale = result.factor / want.factor if want.factor else 1.0
        report["scale_to_expected_unit"] = scale

    json.dump(report, open(a.output, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: report[k] for k in ("status", "result_dimension")
                      if k in report}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
