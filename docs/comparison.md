# 对照协议：如何验证加载 Skill 前后的差异

题面的"使用增益"以同案例下基础 Agent 与 Skill Agent 的结果对比为依据。本文件给出可复现的对照方法，供评审或第三方按同一条件重跑；它描述方法，不预设结论。

## 对照条件

1. 同一份 `/input/case.json` 与 `artifacts/`，同一时限与请求预算。
2. A 组：不加载本 Skill，按题面直接作答。
3. B 组：加载本 Skill，按 `SKILL.md` 流程执行 `scripts/run_case.py` 起手。
4. 两组输出都保存 `result.json` 与 `audit.md`，保留 `sources` 中的公式 `id`。

## 可比较的指标

| 指标 | 取值方式 | 说明 |
|-|-|-|
| 公式带来源 id 的比例 | `formulas.jsonl` 中 `id` 非空的行数 / 总行数 | 对应"结果可核验性" |
| 变量表可回溯比例 | `symbols.csv` 中 `definition_status` 非空的行数 / 总行数 | 对应"讲得清" |
| 数值核验是否留中间值 | `check.json` 的 `checks.intermediates` 是否存在 | 对应"算得回" |
| 量纲是否与原文一致 | `dims.json` 的 `dimension_match` | 单位错误的检出 |
| 契约字段覆盖率 | `audit.md` 的"契约字段 n/m" | 对应"结果完整性" |
| 状态是否诚实 | `result.json` 的 `status` 与未填字段是否一致 | 防止把未知写成事实 |

## 记录要求

- 两组都要保留原始调用记录与运行日志；文字自述不能替代实际运行证据。
- 出现服务失败、超时或权限问题时单列，不计入质量对比。
- 本文件不提供白板或隐藏测试；对照结果由平台生成时，以平台记录为准。
