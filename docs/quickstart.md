# 三分钟上手

面向第一次使用本 Skill 的人或 Agent。全部命令假定当前目录是本包的根目录。

## 1. 一条命令跑完全流程

```bash
python scripts/run_case.py --input /input --work /app/work --output /app/output
```

它会依次完成：清点材料 → 抽取公式（保留 `id`、`label`、取得方式）→ 建变量表（含段落级定位）→ 连编号引用 → 材料有 `values.json` 时做数值代算 → 有 `units.json` 时做量纲核对 → 按 `output_contract` 生成 `result.json` 骨架 → 自审 `audit.md`，最后在标准输出打印一段摘要：

```json
{"case_id": "...", "formulas": 2, "formulas_with_id": 2, "symbols": 7,
 "symbols_with_location": 2, "numeric_value": 3.2277e-27,
 "dimension_match": true, "reference_edges": 0, "status": "partial"}
```

## 2. 补内容

按 `work/summary.json` 的提示补齐：

- `work/symbols.csv` 的 `meaning`、`unit`、`range` 三列，只依据原文，缺就写 `not_reported`。
- `work/answers.json` 的 `derivation`：只为材料真实出现的推导写步骤，带 `from`、`assumptions` 与 `source_id`。

然后重新装配：

```bash
python scripts/assemble_result.py --case /input/case.json --answers work/answers.json \
  --formulas work/formulas.jsonl --symbols work/symbols.csv --output /app/output/result.json
```

## 3. 交前自检

```bash
python scripts/audit.py --work /app/work --result /app/output/result.json \
  --case /input/case.json --output /app/output/audit.md
python selftest.py
python benchmark/run_benchmark.py
```

`audit.md` 是逐条清单；`selftest.py` 验证包本身可用；`run_benchmark.py` 给出数值核对与结构还原两组通过率（自建基准，不是官方案例）。

## 材料缺失时

如果 `run_case.py` 的报告里 `formulas` 为 0，说明材料没有公式表示。此时正确做法是按 `SKILL.md` 的判定表报 `insufficient_evidence` 并列出缺失对象，不要从其他文献反推公式，也不要把未知写成 0。
