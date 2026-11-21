#!/usr/bin/env python3
"""Self-test: run the pipeline on the bundled synthetic example.

    python selftest.py

Checks that formulas are extracted with source ids, that the symbol table is
non-empty, that every contract key appears in result.json, and that a case with
no formula representation degrades to partial instead of inventing content.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def run(args):
    p = subprocess.run([sys.executable] + args, capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit("FAILED: %s\n%s\n%s" % (" ".join(args), p.stdout, p.stderr))
    return p.stdout


def main():
    root = os.path.join(os.path.dirname(HERE), "_selftest_tmp")
    os.makedirs(root, exist_ok=True)
    tmp = os.path.join(root, "run")
    if os.path.isdir(tmp):
        shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)
    work, out = os.path.join(tmp, "work"), os.path.join(tmp, "output")
    case_dir = os.path.join(HERE, "examples", "case")
    inp = os.path.join(tmp, "input")
    os.makedirs(os.path.join(inp, "artifacts"), exist_ok=True)
    shutil.copy2(os.path.join(case_dir, "case.json"), os.path.join(inp, "case.json"))
    shutil.copy2(os.path.join(case_dir, "values.json"), os.path.join(inp, "values.json"))
    shutil.copy2(os.path.join(case_dir, "units.json"), os.path.join(inp, "units.json"))
    shutil.copy2(os.path.join(case_dir, "artifacts", "source-formulas.xml"),
                 os.path.join(inp, "artifacts", "source-formulas.xml"))

    run([os.path.join(HERE, "scripts", "run_case.py"), "--input", inp,
         "--work", work, "--output", out])

    formulas = [json.loads(l) for l in open(os.path.join(work, "formulas.jsonl"), encoding="utf-8") if l.strip()]
    assert len(formulas) >= 2, formulas
    assert all(f["id"] for f in formulas), "every formula must keep its source id"
    assert any(r"\frac" in (f["latex"] or "") for f in formulas), "fractions must survive conversion"

    import csv
    syms = list(csv.DictReader(open(os.path.join(work, "symbols.csv"), encoding="utf-8")))
    assert syms, "symbol table is empty"

    res = json.load(open(os.path.join(out, "result.json"), encoding="utf-8"))
    case = json.load(open(os.path.join(inp, "case.json"), encoding="utf-8"))
    for k in case["output_contract"]["required"]:
        assert k in res, "missing contract field %s" % k
    assert res["case_id"] == "EXAMPLE-000"
    assert res["status"] == "partial", "skeleton must not claim success before answers are filled"

    # a case with no machine-readable formula must degrade, not invent
    empty = os.path.join(tmp, "empty_input")
    os.makedirs(os.path.join(empty, "artifacts"), exist_ok=True)
    shutil.copy2(os.path.join(HERE, "examples", "case_missing", "case.json"),
                 os.path.join(empty, "case.json"))
    shutil.copy2(os.path.join(HERE, "examples", "case_missing", "artifacts", "notes.txt"),
                 os.path.join(empty, "artifacts", "notes.txt"))
    out2 = os.path.join(tmp, "output2")
    run([os.path.join(HERE, "scripts", "run_case.py"), "--input", empty,
         "--work", os.path.join(tmp, "work2"), "--output", out2])
    res2 = json.load(open(os.path.join(out2, "result.json"), encoding="utf-8"))
    assert res2["status"] == "partial", res2["status"]
    assert res2["formulas"]["status"] == "insufficient_evidence", res2["formulas"]

    run([os.path.join(HERE, "scripts", "audit.py"),
         "--work", os.path.join(tmp, "work"), "--result", os.path.join(out, "result.json"),
         "--case", os.path.join(inp, "case.json"),
         "--output", os.path.join(out, "audit.md")])
    audit = open(os.path.join(out, "audit.md"), encoding="utf-8").read()
    assert "契约字段" in audit and "逐条自检" in audit, audit[:200]

    # publisher-style XML: inherit the disp-formula id, prefer the source LaTeX
    pub_out = os.path.join(tmp, "pub.jsonl")
    run([os.path.join(HERE, "scripts", "formula_extract.py"),
         "--input", os.path.join(HERE, "examples", "publisher_sample.xml"),
         "--output", pub_out])
    pub = [json.loads(l) for l in open(pub_out, encoding="utf-8") if l.strip()]
    ids = {p["id"]: p for p in pub}
    assert "FD1" in ids and ids["FD1"]["method"] == "reconstructed", ids.keys()
    assert ids["FD2"]["method"] == "source_annotation", ids["FD2"]
    assert ids["FD2"]["latex"].replace(" ", "") == "E=mc^{2}", ids["FD2"]["latex"]
    assert ids["FD1"]["container"] == "disp-formula", ids["FD1"]

    dims = json.load(open(os.path.join(work, "dims.json"), encoding="utf-8"))
    assert dims.get("dimension_match") is True, dims
    assert dims.get("result_dimension") == "kg^1 m^2/K^1 s^2", dims.get("result_dimension")

    print(json.dumps({"formulas": len(formulas), "symbols": len(syms),
                      "contract_fields": list(res.keys())[:8],
                      "empty_case_status": res2["status"],
                      "audit_chars": len(audit),
                      "publisher_ids": sorted(ids),
                      "dimension": dims.get("result_dimension"),
                      "result": "PASS"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

