#!/usr/bin/env python3
"""Run the self-built benchmark: LaTeX conversion vs an independent expression.

    python run_benchmark.py [--cases cases.jsonl] [--output report.md]

This is OUR benchmark, built from textbook formulas. It is not the official
hidden case set and its numbers must not be presented as an official score. What
it does establish, reproducibly: for each formula the skill's converter yields a
Python expression whose value matches an independently written expression, and
the symbol table recovers the symbols the formula contains.
"""
import argparse
import importlib.util
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SCRIPTS, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=os.path.join(HERE, "cases.jsonl"))
    ap.add_argument("--output", default=os.path.join(HERE, "report.md"))
    ap.add_argument("--rel-tol", type=float, default=1e-6)
    a = ap.parse_args()

    nc = load("numeric_check")
    st = load("symbol_table")

    rows, passed = [], 0
    for line in open(a.cases, encoding="utf-8-sig"):
        if not line.strip():
            continue
        case = json.loads(line)
        expr = nc.latex_to_python(case["latex"])
        ids = nc.identifiers(expr)
        ns = dict(nc.SAFE)
        ns.update(case["values"])
        try:
            got = float(eval(expr, {"__builtins__": {}}, ns))
            want = float(case["expected_value"])
            rel = abs(got - want) / abs(want) if want else abs(got)
            value_ok = rel <= a.rel_tol
        except Exception as e:
            got, want, rel, value_ok = None, case["expected_value"], None, False
            expr = expr + "  # error: %s" % e

        found = set(st.symbols_of(case["latex"]))
        expected = set(case["expected_symbols"])
        symbols_ok = expected <= found
        missing = sorted(expected - found)

        ok = value_ok and symbols_ok
        passed += ok
        rows.append({"id": case["id"], "ok": ok, "value_ok": value_ok, "symbols_ok": symbols_ok,
                     "got": got, "want": want, "rel": rel, "missing_symbols": missing,
                     "expr": expr, "note": case.get("note", "")})

    total = len(rows)
    lines = ["# 自建基准报告", "",
             "说明：本基准由本题作品自行构建，使用教科书公式，**不是**平台官方的三道隐藏案例，",
             "其通过率不能当作官方得分。它检验的是一件事：同一公式经本 Skill 转换后算出的值，",
             "是否与另一条独立写出的表达式一致。", "",
             "| 案例 | 数值一致 | 符号齐全 | 相对误差 | 缺失符号 |",
             "|-|-|-|-:|-|"]
    for r in rows:
        lines.append("| %s | %s | %s | %s | %s |" % (
            r["id"], "✓" if r["value_ok"] else "✗", "✓" if r["symbols_ok"] else "✗",
            "%.2e" % r["rel"] if r["rel"] is not None else "-",
            ", ".join(r["missing_symbols"]) or "-"))
    lines += ["", "通过 **%d/%d**。" % (passed, total), ""]

    lines += ["## 转换后的表达式", "", "| 案例 | 表达式 |", "|-|-|"]
    for r in rows:
        lines.append("| %s | `%s` |" % (r["id"], r["expr"]))
    lines.append("")

    open(a.output, "w", encoding="utf-8").write("\n".join(lines))
    json.dump({"passed": passed, "total": total, "rows": rows},
              open(os.path.join(HERE, "report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps({"passed": passed, "total": total, "output": a.output}, ensure_ascii=False))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

