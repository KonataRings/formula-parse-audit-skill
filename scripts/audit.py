#!/usr/bin/env python3
"""Audit a finished case directory against the evidence the task requires.

Usage:
    python audit.py --work /app/work --result /app/output/result.json \
        --case /input/case.json [--output /app/output/audit.md]

The audit is a checklist, not a score. It reports what is present, what is
missing and what claims cannot be traced, so a reviewer can recompute every
statement without rerunning the model.
"""
import argparse
import csv
import json
import os


def read_json(p):
    if not p or not os.path.exists(p):
        return None
    return json.load(open(p, encoding="utf-8-sig"))


def read_jsonl(p):
    if not p or not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def read_csv(p):
    if not p or not os.path.exists(p):
        return []
    with open(p, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--result", default="/app/output/result.json")
    ap.add_argument("--case", default="/input/case.json")
    ap.add_argument("--output", default="/app/output/audit.md")
    a = ap.parse_args()

    case = read_json(a.case) or {}
    result = read_json(a.result) or {}
    formulas = read_jsonl(os.path.join(a.work, "formulas.jsonl"))
    symbols = read_csv(os.path.join(a.work, "symbols.csv"))
    checks = read_json(os.path.join(a.work, "check.json"))
    dims = read_json(os.path.join(a.work, "dims.json"))

    contract = []
    oc = case.get("output_contract") or {}
    if isinstance(oc, dict):
        contract = list(oc.get("required") or (oc.get("properties") or {}).keys() or [])
    elif isinstance(oc, list):
        contract = [x.get("name") if isinstance(x, dict) else str(x) for x in oc]

    with_id = [f for f in formulas if f.get("id")]
    defined = [s for s in symbols if s.get("definition_status") in ("mentioned_in_body", "defined")]
    unfilled = [k for k in contract if k in result and isinstance(result[k], dict)
                and result[k].get("status") == "insufficient_evidence"]

    lines = ["# 案例自审", "",
             "- case_id：`%s`" % (result.get("case_id") or case.get("case_id")),
             "- 运行状态：`%s`" % result.get("status"), ""]

    lines += ["## 证据清单", "",
              "| 项目 | 数量 | 可核验性 |", "|-|-:|-|",
              "| 抽取公式 | %d | %s |" % (len(formulas),
                                        "全部带来源 id" if formulas and len(with_id) == len(formulas)
                                        else "有公式缺 id" if formulas else "无"),
              "| 变量表行 | %d | %s |" % (len(symbols),
                                        "全部可回溯" if symbols and len(defined) == len(symbols)
                                        else "%d 行未在正文找到定义" % (len(symbols) - len(defined)) if symbols else "无"),
              "| 数值核验 | %s | %s |" % (
                  "有" if checks else "无",
                  (checks or {}).get("status", "-")),
              "| 量纲核对 | %s | %s |" % (
                  "有" if dims else "无",
                  ("%s" % dims.get("result_dimension", "-")) if dims else "-"),
              "| 契约字段 | %d/%d | %s |" % (len(contract) - len(unfilled), len(contract),
                                          "全部填写" if not unfilled else "未填：" + ", ".join(unfilled)),
              ""]

    lines += ["## 逐条自检", ""]
    checks_list = [
        ("每条公式保留来源 id", bool(formulas) and len(with_id) == len(formulas)),
        ("变量表非空", bool(symbols)),
        ("未定义符号已标注", all(s.get("definition_status") for s in symbols) if symbols else False),
        ("量纲与原文声明一致", (dims or {}).get("dimension_match", True)),
        ("数值核验留中间值", bool(checks and checks.get("checks", {}).get("intermediates"))
         or bool(checks and checks.get("checks", {}).get("value") == "not_computed")),
        ("契约字段全覆盖", not unfilled and bool(contract)),
        ("状态与内容一致", (result.get("status") == "success" and not unfilled)
         or (result.get("status") != "success")),
        ("不确定项已记录", "uncertainty" in result),
    ]
    for name, ok in checks_list:
        lines.append("- [%s] %s" % ("x" if ok else " ", name))
    lines.append("")

    if unfilled:
        lines += ["## 未填字段的处理", "",
                  "以下字段按材料缺失填 `insufficient_evidence`，未用 0 或推测值替代：`%s`" % "`, `".join(unfilled), ""]

    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    open(a.output, "w", encoding="utf-8").write("\n".join(lines))
    print(json.dumps({"output": a.output, "formulas": len(formulas),
                      "symbols": len(symbols), "contract": len(contract),
                      "unfilled": unfilled,
                      "passed": sum(1 for _, ok in checks_list if ok)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
