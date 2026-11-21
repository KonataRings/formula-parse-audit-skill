# 最小调用示例（示例，不是正式案例结果）

本目录演示一次完整调用：输入 → 命令 → 示意输出。所有输出均为**示例**，用于说明接口与字段，不代表平台正式案例的结果。

## 输入

- `case/case.json`：案例描述，`output_contract.required` 声明四个字段
- `case/artifacts/source-formulas.xml`：含两条带 `id` 的 MathML 公式（合成材料）
- `case/values.json`：代入用的数值
- `case/answers.json`：示例中由阅读环节填写的内容

## 调用

```bash
python scripts/run_case.py --input examples/case --work work --output output
python scripts/assemble_result.py --case examples/case/case.json \
    --answers examples/case/answers.json \
    --formulas work/formulas.jsonl --symbols work/symbols.csv \
    --output output/result.json
python scripts/audit.py --work work --result output/result.json \
    --case examples/case/case.json --output output/audit.md
```

## 示意输出

- `expected_output/result.json`：`"example": true`，`example_notice` 写明其为示例
- `expected_output/audit.md`：标题含"示例输出，非正式案例结果"

关键字段：

| 字段 | 示例值 |
|-|-|
| `case_id` | `EXAMPLE-000` |
| `status` | `success` |
| `formulas[0].id` | `eq1`（来自 MathML 的 `id`） |
| `symbol_table` | 7 行，含 `k_B`、`Theta` 等 |
| `numeric_check.value` | `3.2277063390481063e-27` |

该数值由 `scripts/numeric_check.py` 计算，不是手写。

## 缺失材料分支

`../case_missing/` 演示题面所述的 C02 情形：没有公式表示、没有可复算数据。正确输出是 `insufficient_evidence` 并列出缺失对象，而不是反推公式或把未知写 0。
