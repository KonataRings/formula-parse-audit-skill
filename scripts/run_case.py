#!/usr/bin/env python3
"""One-command driver: /input -> work/* and a result.json skeleton.

Usage:
    python run_case.py --input /input --work /app/work --output /app/output

It runs the deterministic part of the pipeline (artifact inventory, formula
extraction, symbol table, contract skeleton) and prints the questions the model
still has to answer from the material. Everything written here is reproducible
from the case files alone.
"""
import argparse
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return {"cmd": " ".join(cmd), "rc": p.returncode,
            "stdout": p.stdout.strip()[:2000], "stderr": p.stderr.strip()[:2000]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="/input")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--output", default="/app/output")
    a = ap.parse_args()

    os.makedirs(a.work, exist_ok=True)
    os.makedirs(a.output, exist_ok=True)

    case_path = os.path.join(a.input, "case.json")
    case = json.load(open(case_path, encoding="utf-8-sig")) if os.path.exists(case_path) else {}
    art_dir = os.path.join(a.input, "artifacts")
    artifacts = sorted(glob.glob(os.path.join(art_dir, "**", "*"), recursive=True))
    artifacts = [p for p in artifacts if os.path.isfile(p)]

    inventory = {"case_id": case.get("case_id") or case.get("id"),
                 "has_case_json": os.path.exists(case_path),
                 "artifacts": [{"path": os.path.relpath(p, a.input),
                                "bytes": os.path.getsize(p)} for p in artifacts],
                 "output_contract_present": bool(case.get("output_contract")),
                 "notes": []}
    if not artifacts:
        inventory["notes"].append("no artifacts found: expect insufficient_evidence for content fields")
    json.dump(inventory, open(os.path.join(a.work, "inventory.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    steps = []
    formulas_path = os.path.join(a.work, "formulas.jsonl")
    xmls = [p for p in artifacts if p.lower().endswith((".xml", ".mathml", ".html"))]
    text_latex = [p for p in artifacts if p.lower().endswith((".tex", ".md"))]
    if xmls or text_latex:
        steps.append(run([sys.executable, os.path.join(HERE, "formula_extract.py"),
                          "--input", art_dir, "--output", formulas_path]))
    else:
        inventory["notes"].append("no xml/mathml artifact: formula structures are not machine-readable")
        json.dump(inventory, open(os.path.join(a.work, "inventory.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)

    symbols_path = os.path.join(a.work, "symbols.csv")
    if os.path.exists(formulas_path):
        text_files = [p for p in artifacts if p.lower().endswith((".txt", ".md"))]
        if not text_files and xmls:
            # definition sentences usually live in <p> nodes of the same XML
            import xml.etree.ElementTree as ET
            chunks = []
            for p in xmls:
                try:
                    root = ET.fromstring(open(p, encoding="utf-8").read())
                except Exception:
                    continue
                auto = 0
                for el in root.iter():
                    if isinstance(el.tag, str) and el.tag.split("}")[-1] in ("p", "title", "abstract", "label", "caption"):
                        chunk = "".join(el.itertext()).strip()
                        if chunk:
                            auto += 1
                            ident = el.attrib.get("id") or "%s-%d" % (
                                os.path.basename(p).split(".")[0], auto)
                            chunks.append("[%s] %s" % (ident, chunk))
            if chunks:
                body = os.path.join(a.work, "body.txt")
                open(body, "w", encoding="utf-8").write("\n".join(chunks))
                text_files = [body]
        cmd = [sys.executable, os.path.join(HERE, "symbol_table.py"),
               "--formulas", formulas_path, "--output", symbols_path]
        if text_files:
            cmd += ["--text", text_files[0]]
        steps.append(run(cmd))
        if text_files and os.path.basename(text_files[0]) == "body.txt":
            steps.append(run([sys.executable, os.path.join(HERE, "link_refs.py"),
                              "--formulas", formulas_path, "--body", text_files[0],
                              "--output", os.path.join(a.work, "refs.json")]))

    pdfs = [p for p in artifacts if p.lower().endswith(".pdf")]
    for pdf in pdfs:
        steps.append(run([sys.executable, os.path.join(HERE, "formula_extract.py"),
                          "--pdf", pdf,
                          "--output", os.path.join(a.work, os.path.basename(pdf) + ".txt")]))

    # numeric pass: only when the material supplied values to substitute
    values_candidates = [os.path.join(a.work, "values.json"), os.path.join(a.input, "values.json")]
    values_path = next((p for p in values_candidates if os.path.exists(p)), None)
    if values_path and os.path.exists(formulas_path):
        first = next((f for f in (json.loads(l) for l in
                                  open(formulas_path, encoding="utf-8") if l.strip())
                      if f.get("latex")), None)
        if first:
            steps.append(run([sys.executable, os.path.join(HERE, "numeric_check.py"),
                              "--latex", first["latex"], "--values", values_path,
                              "--symbol-table", symbols_path,
                              "--output", os.path.join(a.work, "check.json")]))

    # dimension pass: only when the material declares units for the symbols
    unit_candidates = [os.path.join(a.work, "units.json"), os.path.join(a.input, "units.json")]
    unit_path = next((p for p in unit_candidates if os.path.exists(p)), None)
    if unit_path and os.path.exists(formulas_path):
        first = next((f for f in (json.loads(l) for l in
                                  open(formulas_path, encoding="utf-8") if l.strip())
                      if f.get("latex")), None)
        if first:
            expect = ""
            try:
                meta = json.load(open(unit_path, encoding="utf-8-sig"))
                expect = meta.get("_expect", "")
            except Exception:
                pass
            cmd = [sys.executable, os.path.join(HERE, "dimension_check.py"),
                   "--latex", first["latex"], "--units", unit_path,
                   "--output", os.path.join(a.work, "dims.json")]
            if expect:
                cmd += ["--expect", expect]
            steps.append(run(cmd))

    status = "success" if (os.path.exists(formulas_path) and case.get("output_contract")) else "partial"
    skeleton = run([sys.executable, os.path.join(HERE, "assemble_result.py"),
                    "--case", case_path,
                    "--formulas", formulas_path if os.path.exists(formulas_path) else "",
                    "--symbols", symbols_path if os.path.exists(symbols_path) else "",
                    "--output", os.path.join(a.output, "result.json"),
                    "--status", status])

    report = {"inventory": inventory, "steps": steps, "skeleton": skeleton,
              "next": ["complete symbols.csv meaning/unit/range from the source text",
                       "write derivation steps only for derivations the material reports",
                       "run numeric_check.py on formulas that carry numbers",
                       "fill answers.json and re-run assemble_result.py"]}
    json.dump(report, open(os.path.join(a.work, "run_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps({"case_id": inventory["case_id"], "artifacts": len(artifacts),
                      "formulas": os.path.exists(formulas_path), "status": status},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()


