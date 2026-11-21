# formula-parse-audit

一个把论文公式变成可复核结构的 Skill：保结构 LaTeX、可回溯原文的变量表、分步推导说明、数值代算核验，以及材料缺失时明确的状态标注。

## 三分钟上手

见 [docs/quickstart.md](docs/quickstart.md)：一条命令跑完流水线并打印摘要，再补内容与自检。

## 依赖

- Python 3.8+，仅用标准库（`xml.etree`、`json`、`csv`、`re`、`math`）。
- 可选：`PyMuPDF`（`import fitz`）用于 PDF 文本层抽取；缺失时 `formula_extract.py --pdf` 会返回 `unavailable` 而不猜测内容。
- 不需要 antlr4、不需要 LaTeX、不需要 sympy；`sympy` 若可用只作为交叉核对。

## 目录

```
SKILL.md                      Skill 说明与调用流程
scripts/run_case.py           一条命令跑通 /input -> work/ + 骨架 result.json
scripts/formula_extract.py    MathML/XML -> LaTeX，保留 id；PDF 文本回退
scripts/symbol_table.py       符号提取与变量表前四列
scripts/numeric_check.py      LaTeX -> Python，代算并给出中间值
scripts/assemble_result.py    按 output_contract 装配 result.json
scripts/audit.py              生成 audit.md 自审清单
scripts/dimension_check.py    量纲引擎：带入符号单位求值，核对结果量纲
scripts/latex_compare.py      结构规范化比较与数值等价抽样
scripts/link_refs.py          正文编号引用连到带 label 的公式
templates/                    变量表与报告模板
examples/case/                合成示例（含 case.json、values.json、答案与公式 XML）
examples/case_missing/        缺公式表示的示例，演示 insufficient_evidence 分支
examples/expected_output/     示例运行产生的 result.json 与 audit.md，仅作示例
selftest.py                   一键自检
```

## 最小调用示例

```bash
python scripts/run_case.py --input /input --work /app/work --output /app/output
python scripts/numeric_check.py \
  --latex "\frac{12}{5}{\pi}^{4}N{k}_{B}{(\frac{T}{\Theta})}^{3}" \
  --values work/values.json --symbol-table work/symbols.csv --output work/check.json
python scripts/assemble_result.py --case /input/case.json --answers work/answers.json \
  --formulas work/formulas.jsonl --symbols work/symbols.csv --output /app/output/result.json
```

示例输出（`examples/expected_output/result.json`）里 eq1 在 N=1、k_B=1.380649e-23、T=10、Θ=1000 下得 `3.2277e-27`，该数值由 `numeric_check.py` 算出，不是手写。

## 自检

```bash
python selftest.py                 # 三件事：抽取、装配、降级
python benchmark/run_benchmark.py  # 自建 10 条公式基准，输出通过率
```

`selftest.py` 覆盖：公式带 id 抽取、分式与希腊字母正确转换、变量表非空、`output_contract` 每个字段都出现在 `result.json`，并对"没有公式表示的材料"单独断言必须降级为 `partial` 而不是编造内容。

`benchmark/` 是本题作品自建的基准，分两部分：10 条教科书公式的**数值核对**（期望值来自与 LaTeX 转换独立的 Python 表达式，两条路径算出同一个数才算通过），以及 8 条 **MathML → LaTeX 结构还原**（含 U+2061/U+2062 不可见算符、函数作用、根号下的分式、上下标并存、分段函数、大写希腊字母、alttext 优先）。它检验转换保真度，**不是**平台官方的三道隐藏案例，通过率不能当作官方得分。

## 比较两个公式是否等价

```bash
python scripts/latex_compare.py --a "E = m c^{2}" --b "E=mc^2" --symbols c,m,E
```

先做结构规范化（忽略空格、`\left/\right`、`\dfrac` 与 `\frac` 的差异、单字符多余花括号），再做数值等价抽样：在若干随机取值下两边算出的数一致才算等价。用于判断评审给出的参考写法与自己还原的写法是否"写法不同、含义相同"。

## 量纲核对

材料声明符号单位时，把同一表达式换成单位求值，检查结果量纲：

```bash
python scripts/dimension_check.py \
  --latex "p=\frac{n R T}{V}" \
  --units units.json --expect Pa --output work/dims.json
```

`units.json` 形如 `{"n": "mol", "R": "J/(mol K)", "T": "K", "V": "m^3"}`。若把 `R` 误写成 `J/mol`，结果量纲变成 `K·kg/(m·s^2)`，脚本返回 `dimension_match: false` 并把状态降为 `partial`——数值看似合理但单位错的公式会被这一步拦下。支持 `J`、`N`、`Pa`、`W`、`C`、`V`、`F`、`ohm`、`T`、`Hz`、`eV` 等派生单位与括号、幂次。

## 安装位置

若运行环境要求 Skill 位于 `/app/submission`：

```bash
python install.py --target /app/submission
```

脚本幂等：已存在的文件默认不覆盖，`--force` 才重写。

## 已知限制

- MathML 覆盖常用子集（`mrow/mfrac/msub/msup/msubsup/msqrt/mroot/mfenced/mtable/munderover/munder/mover`）；`menclose`、`mmultiscripts` 会退化为子节点拼接，此时应在 `uncertainty` 标注。
- 数值代算要求公式能转成 Python 表达式；含求和、积分、分段函数的公式会转换失败并报 `evaluation_failed`，不会静默返回 0。
- 手写 LaTeX 中相邻符号无空格连写（如 `3Nk_B`）时，按单字母变量拆分；若连写中含有拼写出的希腊名（如 `epsilon_0`）则保持整名，判定依据是名称表，可能对罕见命名失效。
- 变量表只给出符号与出现位置，含义、单位、取值范围需按 `templates/symbol_table.md` 从原文补齐。
- PDF 路线依赖文本层；扫描件需要外部 OCR，本 Skill 不内置。

## 版本

- 1.6.0：run_case 一条命令收敛全流程并输出 summary.json；新增 docs/quickstart.md。
- 1.5.0：符号段落级定位（first_body_location）与公式交叉引用（link_refs）；正文段落带 [pID] 标记。
- 1.4.0：结构还原基准 8/8；支持不可见算符（U+2061/U+2062）、alttext 优先、JATS label 公式编号、命令与字母间距；新增 latex_compare 等价比较。
- 1.3.0：新增量纲核对 dimension_check.py（支持派生单位与括号），示例与自检覆盖单位错误检出。
- 1.2.0：新增 10 条自建基准与 `install.py`；抽取优先采用原文 LaTeX 注释、继承 `disp-formula` 级别 ID、标记截断；数值核验增加数量级区间核对；示例输出显式标注为示例。
- 1.1.0：新增 audit.py 自审清单、munderover/matrix 覆盖、缺失材料示例；数值核验去除 antlr4 依赖。





