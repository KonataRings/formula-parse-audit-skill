---
name: formula-parse-audit
description: 解析科研材料中的公式（MathML、出版商 XML、PDF 片段或 LaTeX 文本），输出保结构 LaTeX、可回溯原文的变量表、分步推导说明与数值代算核验；当材料缺少公式表示或可复算数据时，明确给出 partial 或 insufficient_evidence 状态，不反推、不补零。
---

# 公式解析与数学推理

## 适用条件

当输入材料包含数学公式，且任务要求把公式转成结构化表达、解释变量、拆解推导或做数值核验时使用本 Skill。典型触发条件：

- 材料给出 MathML、出版商 XML 或 PDF，需要还原公式结构，而不是复述正文。
- 需要把公式中的符号与原文定义、单位、取值范围对应起来。
- 需要判断某一步推导在什么假设下成立，或在给定数值下能否复算。
- 材料可能缺少公式表示或可复算数据，需要区分"未报告"与"算错"。

不适用：纯文字摘要、无公式的图表读数和图像生成任务。

## 输入

运行时输入位于 `/input`：

- `/input/case.json`：案例描述，含 `case_id`、`output_contract` 及材料指针。
- `/input/task.md`：本题面。
- `/input/artifacts/`：实际材料，可能包含 `publisher-source.xml`、`source-formulas.xml`、PDF 或纯文本。

先读 `case.json` 的 `output_contract`，再决定要产出哪些字段；字段名以它为准，本 Skill 不预设。

## 处理流程

1. **识别材料边界。** 列出 `/input/artifacts` 实际存在的文件，逐个判断类型：含 `mfrac`/`msub` 的 XML 是公式表示，纯 `<p>` 的 XML 或 TXT 是正文，PDF 需要文本层。记录哪些材料存在、哪些缺失，缺失项直接进入结果的状态字段。
2. **抽取公式并保结构。** 用 `scripts/formula_extract.py` 把 MathML 子集转成 LaTeX，保留分式、上下标、括号层级和来源 `id`。输出 `work/formulas.jsonl`，每行为 `{id, latex, kind, depth, method, container, label, truncated, source}`。转换后逐条对照原节点复核一次：分式是否仍是分式、上下标是否落到正确基底、希腊字母与单位是否错位。

   已知的四个易错点，脚本按下列顺序处理：

   - **原文 LaTeX 优先**：JATS 的 `<tex-math>`（常包着一整份排版用 LaTeX 文档，需剥掉导言区）、MathML 的 `<annotation encoding="application/x-tex">`、`math/@alttext` 三条路径依次尝试，命中即采用，`method` 记为 `source_texmath`、`source_annotation` 或 `source_alttext`；原文 LaTeX 原样保留，不重排。都不存在时才重建，记 `reconstructed`。
   - **不可见算符**：U+2061（函数作用）与 U+2062（隐式乘）必须丢弃，不能写进 LaTeX，否则 `sin(x)` 会变成非法命令。
   - **命令与字母相邻**：`\pi` 紧接 `m` 时插入空格，避免被读成 `\pim`。
   - **公式编号**：JATS 把编号放在 `disp-formula` 的 `<label>` 里，脚本沿祖先查找并写入 `label` 字段。
3. **建立变量表。** 用 `scripts/symbol_table.py` 从 LaTeX 提取符号，合并正文中的定义句，输出 `work/symbols.csv`。每一行必须能回答：符号是什么、含义、单位、取值范围、首次定义出现在哪个 `id` 或页码。原文没有给出的字段写 `not_reported`，不按常识补写。正文按段落打 `[pID]` 标记，脚本会把符号第一次出现的段号写进 `first_body_location`。
4. **拆解推导。** 只对材料中真实出现的推导写步骤；每步记录所用前序步骤的 `id`、假设、近似和边界条件。跨公式引用要指名 `id`。材料只给结论而未给推导时，写 `derivation_not_provided`，不要自行生成"看起来合理"的中间步骤。正文里 "Eq. (3)" 这类编号引用由 `scripts/link_refs.py` 自动连到带 `<label>` 的公式，输出 `work/refs.json`；连不上的引用进 `unresolved`，不猜。
5. **数值核验。** 用 `scripts/numeric_check.py` 对可计算公式做代算：解析 LaTeX、代入材料给出的数值、输出中间值与最终值。无法解析或缺少数值时，报告失败原因与本应满足的条件，不用 0 占位。
   若材料还声明了符号单位，用 `scripts/dimension_check.py` 做量纲核对：同一表达式换上单位求值，结果量纲与原文声明不一致即报 `partial`，可发现"数值看似合理但单位错"的情形。
6. **落盘。** 用 `scripts/assemble_result.py` 生成 `/app/output/result.json`：包含 `output_contract` 的全部字段、`case_id`、来源定位、运行状态、不确定项和变更记录。可编辑产物放 `/app/output`，需要预览的另存 PDF 或 PNG。
7. **自审。** 用 `scripts/audit.py` 生成 `audit.md`：逐条列出公式是否带来源 id、变量表是否可回溯、数值核验是否留中间值、契约字段是否全覆盖、状态与内容是否一致。自审只说明证据是否齐备，不代替结论。

## 材料缺口的判断顺序

拿到案例后按以下顺序判定，不要跳过：

| 观察 | 判定 | 处理 |
|-|-|-|
| 有 `mfrac`/`msub` 的 XML | 公式可机器复现 | 完整抽取并逐条复核 |
| 只有 `<p>` 文本或 PDF 文本层 | 公式需人工判读 | 抽取后标 `structure_inferred`，结论降为 `partial` |
| 原快照没有公式表示、也没有可复算数据 | 无法判断 | `insufficient_evidence`，列出缺失对象，禁止反推 |
| 有公式但缺数值 | 可复现结构、不可代算 | 结构字段填值，`numeric_check` 写 `not_computed` 及缺失量 |

C02 这类"保留真实缺失分支"的案例，正确做法是报告缺什么，而不是把缺失量补成 0 或从其他文献反推公式。

## 四个判定目标的落地方式

| 目标 | 本 Skill 的具体做法 | 失败时的表现 |
|-|-|-|
| 认得准 | 若 MathML 带 `annotation encoding="application/x-tex"`，直接采用原文 LaTeX，不做重建；否则按节点重建，并记录 `method` 为 `source_annotation` 或 `reconstructed` | 括号不平衡时标 `truncated: true` 并降级 |
| 讲得清 | 变量表区分 `mentioned_in_body` 与 `undefined_in_material`，单位与范围缺失写 `not_reported` | 未定义符号汇总进 `uncertainty` |
| 推得顺 | 只记录材料中真实出现的推导，每步带依赖公式 `id`、假设与边界条件 | 材料未给推导时写 `derivation_not_provided` |
| 算得回 | 把 LaTeX 转成 Python 表达式代入材料数值，输出中间值与最终值；可给出原文声明的数量级区间做范围核对 | 越界时状态降为 `partial` 并提示核对符号、单位或数量级 |

## 异常处置

| 情况 | 识别方式 | 处置 |
|-|-|-|
| 公式被截断 | 转换后花括号不平衡，或节点缺少闭合标签 | 标 `truncated`，只用可见部分，结论降 `partial` |
| 符号歧义 | 同一符号在不同公式中含义冲突，或变量表同名不同义 | 拆成两行并各注 `id`，在 `uncertainty` 说明 |
| 单位缺失 | 变量表 `unit` 为空 | 写 `not_reported`，不套用国际单位制默认值 |
| 代入无解 | 表达式转换失败或缺少数值 | 输出 `not_computed` 及缺失清单，不用 0 占位 |
| 数量级异常 | 计算结果落在原文声明区间之外 | 保留计算值，标注越界并要求复核 |
| 无公式表示 | 材料只有正文或扫描件无文本层 | `insufficient_evidence`，禁止反推 |
| 权限或依赖缺失 | 读文件失败、可选库不可用 | 记录异常与影响范围，给出人工接管点 |

| 状态 | 使用条件 | 写法 |
|-|-|-|
| `success` | 契约字段全部填出，关键结论可回到材料定位 | 正常填写 |
| `partial` | 部分字段完成，其余有明确原因 | 已完成字段填值，其余注明缺什么 |
| `insufficient_evidence` | 材料缺少公式表示、数值或推导，无法判断 | 说明缺哪个对象，禁止反推补全 |
| `failed` | 工具或解析失败 | 记录异常、影响范围与人工接管点 |

状态与分数无关，如实标注不扣分；把未知写成事实或填 0 会被判为不忠实。

## 输出约定

`result.json` 顶层至少包含：

- `case_id`
- `output_contract` 中声明的每个字段
- `sources`：每条结论对应的 `id`、页码或 XPath
- `uncertainty`：不确定项及其原因
- `changes`：相对输入的处理记录，例如"删除空行""公式 id 重排"

字段值优先用结构化对象而不是长字符串；数值保留足够有效位，单位与原文一致。

## 失败处理

- XML 不合法：退回正则提取 `id` 与文本，状态降为 `partial` 并写明退化路径。
- PDF 无文本层：用 `scripts/formula_extract.py --pdf` 的逐页文本回退；仍失败则 `insufficient_evidence`，不要凭图表猜测公式。
- `sympy` 不可用：`numeric_check.py` 会输出 `symbolic_backend_missing`，此时只做量纲与括号平衡检查，并在 `uncertainty` 中声明未做数值核验。
- 预算紧张（64 次请求 / 900 秒）：先落盘 `result.json` 骨架与 formula 抽取结果，再逐项改进；任何时刻的中间产物都要可读。

## 资源

- `scripts/formula_extract.py`：MathML/XML → LaTeX，保留 `id`；支持 PDF 文本回退。
- `scripts/symbol_table.py`：符号提取与变量表前两列。
- `scripts/numeric_check.py`：LaTeX → sympy，代算得中间值与最终值。
- `scripts/assemble_result.py`：按 `output_contract` 装配 `result.json`。
- `scripts/audit.py`：生成 `audit.md` 自审清单。
- `scripts/dimension_check.py`：量纲引擎，符号单位带入同一表达式求值，核对结果量纲。
- `scripts/latex_compare.py`：两个 LaTeX 的结构规范化比较与数值等价抽样，用于判断"写法不同、含义相同"。
- `scripts/link_refs.py`：把正文中的编号引用连到带 `<label>` 的公式，产出依赖边。
- `scripts/validate_corpus.py`：对一批出版商 XML 出覆盖报告（取得方式、id 与编号留存、空结果与截断数），用于先摸清某家出版社的公式表示方式。
- `install.py`：把 Skill 幂等复制到 `/app/submission`，兼容两种目录约定。
- `benchmark/`：自建 10 条公式基准，期望值来自与 LaTeX 转换独立的表达式；`run_benchmark.py` 输出通过率与逐条表达式。它检验的是转换保真度，不是官方分数。
- `templates/`：变量表与报告模板。
- `examples/`：最小可运行示例，输出已标注为示例。

## 预算分配

单案例预算 64 次请求、900 秒，按下面的顺序花：

| 阶段 | 请求数 | 产出 |
|-|-|-|
| 清点材料、跑 `run_case.py` | 1–2 | `inventory.json`、`formulas.jsonl`、骨架 `result.json` |
| 逐条核对公式与补齐变量表 | 8–12 | `symbols.csv` 的语义列 |
| 推导与原文对照 | 6–10 | `derivation` 字段 |
| 数值核验 | 2–4 | `check.json` |
| 自审与修订 | 3–5 | `audit.md`、最终 `result.json` |

先落盘骨架再改进：任何时刻的 `result.json` 都应是合法、字段齐全的，即使值还是 `insufficient_evidence`。

## 输出片段示例

```json
{
 "case_id": "C0X",
 "status": "partial",
 "formulas": [{"id": "eq3", "latex": "{C}_{p}=\\frac{12}{5}{\\pi}^{4}N{k}_{B}{(\\frac{T}{\\Theta})}^{3}",
               "source": "artifacts/source-formulas.xml"}],
 "symbol_table": [{"symbol": "k_B", "meaning": "Boltzmann constant",
                   "unit": "not_reported", "source": "eq3"}],
 "derivation": [{"step": 1, "from": ["eq3"], "assumptions": ["T << Theta"], "source_id": "eq3"}],
 "numeric_check": {"formula_id": "eq3", "value": 3.2277063390481063e-27,
                   "evaluated_with": {"N": 1.0, "k_B": 1.380649e-23, "T": 10.0, "Theta": 1000.0}},
 "uncertainty": [{"kind": "undefined_symbols", "symbols": ["C_p"]}]
}
```

示例中的数值由 `scripts/numeric_check.py` 算出，不是手写；换成实际案例时必须重新算。

## 质量闸门

提交前逐条自查：

1. 每条公式的 `id` 能指回原文件的具体节点或页码。
2. 变量表中每个符号都有来源；`not_reported` 只用于原文确实未给。
3. 推导步骤数量与材料一致，没有补写。
4. 数值核验留有中间值，失败项写明了原因。
5. `result.json` 覆盖 `output_contract` 的全部字段，缺项有状态说明。
