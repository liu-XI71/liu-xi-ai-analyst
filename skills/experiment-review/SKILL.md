---
name: experiment-review
description: Review a preregistered new-user randomized experiment using its assignment, event and collection logs. Applies to exact D7 retention, negative-feedback guardrails, SRM, maturity and decision reports; not before/after comparisons or automatic rollout.
---

# 新用户实验评审

交付可复算的实验决策备忘录。指标、检验与决策由 `app.domains.experiments` 计算，语言模型组织问题与证据解释。当前数据是固定种子合成日志，不表示实际企业收益。

## 输入与调用

- `domain=experiments`；`task=experiment` 或 `report`。
- `filters.scenario` 是单个场景：`healthy_gain`、`srm`、`guardrail`、`immature`、`underpowered`、`unequal_allocation`、`config_change`、`data_gap`。
- `start/end` 同时留空时使用选定实验的完整预注册窗口。显式提供时必须与该窗口完全一致。不可接受前后对比日期或任意事后子组筛选。
- 读取 `metadata()` 获取当前口径和场景日期；不要从案例名称推断结果。
- 应用工具使用 `analyze_business` 时传入上述结构化请求；本地直接执行 [评审脚本](scripts/review_experiment.py)。脚本复用同一业务函数，无额外计算分支。

```bash
.venv/bin/python skills/experiment-review/scripts/review_experiment.py \
  --db var/experiments.sqlite --scenario guardrail
```

只有需要初始化合成实验表时添加 `--init`。脚本将分析 JSON 写到标准输出，`--output` 可保存同一结果。

## 评审约束

1. 先看 `status`、`checks` 与 `decision.code`。质量异常和未成熟时，保留核查证据并停止效应结论；不把缺失观测计为零。
2. 主指标固定精确 D7，按原始分配 ITT，包括未暴露用户。不能改成次 7 日任意回访，也不能筛选实际活跃或曝光用户提高表现。
3. 使用实际注册分配比例检查 SRM，使用预注册 MDE、alpha、功效和围栏假设解释样本要求。不得用统一人数阈值代替设计。
4. 解释主要效应的百分点、相对值及区间；相对值 `null` 表示分母为零，不能改写为 0%。围栏只有差异区间上界低于非劣界值才通过，“不显著”不是安全证明。
5. 复用工具的决策状态和 SQL 证据 ID。可以调整措辞，不能通过删掉失败门槛把结论改成可放量。报告区分事实、适用范围和行动。
6. 不进行每日显著即停、事后修改口径或固定窗口，不自动发布策略。长期 Holdout 只在长期或组合效应问题中讨论，不凭缺少 Holdout 否定所有有效随机实验。

## 结果交付

报告包含业务问题、实验与指标合同、数据截至时间、设计样本、质量与成熟结果、主要/围栏效应、决策及复查动作。所有数字引用工具结果，不补写未执行的查询或未发生的业务收益。

解释字段与中止状态时读取 [输出合同](references/output-contract.md)。需要核对公式与假设时读取 [实验方法](../../docs/experiment-methods.md)。工具报错仅修复明确的参数问题后重试；不能用文字补齐缺失结果。
