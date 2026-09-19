# 实验评审输出合同

`analyze(request, path)` 返回 `status/title/summary/metric_contract/kpis/tables/charts/findings/evidence/trace/limitations/suggestions`，并附以下字段。

| 字段 | 解释 |
|---|---|
| `experiment_contract` | 来自注册表的设计、窗口与业务约定 |
| `plan` | 根据预注册基线、MDE、功效、分配比和围栏计算的样本需求；不是后验功效 |
| `checks` | 各门槛的规则、观测值、通过状态与证据；`passed=null` 表示无法评价 |
| `experiment_statistics.srm` | 预注册比例下的卡方统计、p 值、期望人数与近似可用性 |
| `experiment_statistics.primary` | D7 效应、区间、相对变化和辅助 p 值；质量/成熟门槛失败为 `null` |
| `experiment_statistics.guardrail` | 负反馈效应、非劣界值及是否足以证明非劣 |
| `experiment_statistics.inference_valid` | 数据与观察是否满足统计解释前提；不表示已证实业务收益 |
| `decision` | 决策代码、标签、原因、行动和门槛快照；`executes_rollout=false` |

状态与决策：

- `needs_clarification`：输入不支持，提供 `clarification`，不开展分析。
- `invalid_data`：质量合同失败或注册记录缺失。效应字段缺失或为 `null`，显示修复动作。
- `waiting_for_maturity`：观察未完成，原始已观测计数仅供核查。
- `insufficient_data`：没有足够两组记录完成检验；决策为 `insufficient_evidence`。
- `completed`：完成统计评审；决策仍可能是 `insufficient_evidence`、`stop_or_adjust` 或 `review_for_gradual_rollout`。

证据使用绑定参数 SQL，可在同一数据库快照重放。质量未通过时，分组表的原始计数不自动具备因果解释。图表的留存与负反馈单位为百分比，效应差异为百分点，不混用。
