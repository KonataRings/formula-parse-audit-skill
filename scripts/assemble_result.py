#!/usr/bin/env python3
"""Assemble /app/output/result.json against the case's own output_contract.

Usage:
    python assemble_result.py --case /input/case.json --answers work/answers.json \
        --formulas work/formulas.jsonl --symbols work/symbols.csv \
        --output /app/output/result.json [--status partial]

Every key declared in output_contract is present in the result. Keys without an
answer are filled with an explicit status object, never with 0 or a guess.
"""
import argparse
import csv
import json
import os


def contract_keys(case):
    """Accept the several shapes output_contract appears in."""
    keys = []
    oc = case.get("output_contract") or {}
    if isinstance(oc, dict):
        if "fields" in oc and isinstance(oc["fields"], (list, dict)):
            f = oc["fields"]
            keys = list(f.keys()) if isinstance(f, dict) else [
                x.get("name") if isinstance(x, dict) else str(x) for x in f]
        elif "required" in oc:
            keys = list(oc["required"])
        elif "properties" in oc:
            keys = list(oc["properties"].keys())
        else:
            keys = [k for k in oc if not str(k).startswith("_")]
    elif isinstance(oc, list):
        keys = [x.get("name") if isinstance(x, dict) else str(x) for x in oc]
    return [k for k in keys if k]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--answers", help="json object with the values the agent derived")
    ap.add_argument("--formulas")
    ap.add_argument("--symbols")
    ap.add_argument("--output", required=True)
    ap.add_argument("--status", default="success")
    a = ap.parse_args()

    case = json.load(open(a.case, encoding="utf-8-sig"))
    answers = json.load(open(a.answers, encoding="utf-8-sig")) if a.answers and os.path.exists(a.answers) else {}
    keys = contract_keys(case)

    result = {"case_id": case.get("case_id") or case.get("id"),
              "status": a.status,
              "sources": [],
              "uncertainty": [],
              "changes": []}

    formulas = []
    if a.formulas and os.path.exists(a.formulas):
        formulas = [json.loads(l) for l in open(a.formulas, encoding="utf-8-sig") if l.strip()]
        result["sources"] = [{"id": f.get("id"), "kind": f.get("kind"),
                              "source": f.get("source")} for f in formulas]

    symbols = []
    if a.symbols and os.path.exists(a.symbols):
        with open(a.symbols, encoding="utf-8-sig") as f:
            symbols = list(csv.DictReader(f))

    filled, missing = 0, []
    for k in keys:
        if k in answers and answers[k] not in (None, "", []):
            result[k] = answers[k]
            filled += 1
        else:
            result[k] = {"status": "insufficient_evidence",
                         "reason": "material did not report the objects this field needs"}
            missing.append(k)

    if symbols:
        und = [s["symbol"] for s in symbols if s.get("definition_status") == "undefined_in_material"]
        if und:
            result["uncertainty"].append({"kind": "undefined_symbols", "symbols": und[:20]})
    if missing:
        result["uncertainty"].append({"kind": "unfilled_contract_fields", "fields": missing})
        if a.status == "success":
            result["status"] = "partial"

    result["changes"] = [{"step": "formula_extraction", "formulas": len(formulas)},
                         {"step": "symbol_table", "symbols": len(symbols)},
                         {"step": "contract_fill", "filled": filled, "missing": len(missing)}]

    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    json.dump(result, open(a.output, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"output": a.output, "status": result["status"],
                      "contract_fields": len(keys), "filled": filled,
                      "missing": missing}, ensure_ascii=False))


if __name__ == "__main__":
    main()


