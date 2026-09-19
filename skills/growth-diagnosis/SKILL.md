---
name: growth-diagnosis
description: Diagnose mature-cohort growth retention, review a randomized retention experiment, or generate an evidence-backed growth report from this portfolio's growth database. Use for channel/device retention changes and growth experiment questions; do not route repurchase or arbitrary CSV tasks here.
---

# 增长诊断与周报

用于这个项目的增长队列、渠道/设备分解和随机实验复盘。业务结论必须来自已执行工具返回的证据；数据为固定种子合成数据，不对应刘希的实习业绩。

## 输入与路由

- `task=diagnose`：留存变化，默认本期 2026-08-24—30，对比期 2026-08-17—23。
- `task=report`：相同分析范围，组织成带图表和证据的周报。
- `task=experiment`：默认 2026-08-17—30，比较同一时段的随机组，不接收 `compare_start/compare_end`。
- `start/end`、`compare_start/compare_end` 成对使用，YYYY-MM-DD；两期不能重叠。
- 筛选仅允许 `channel=organic|paid_search|social|referral` 和 `device=android|ios|web`，各字段可为单值或列表。未知字段或值需澄清，不能静默删除。
- 用户的时间范围优先；「最近」指当前数据快照的最近成熟队列，应在答案中写出实际日期，不能假装实时数据。

## 执行步骤

1. 读取 [指标与数据合同](references/metric-dictionary.md)，把用户问题转成受支持的任务、日期和筛选。遇到「D7」先确认是精确第 7 日，还是次 7 日内；当前工具仅支持后者。
2. 调用增长分析工具，保留它返回的口径、SQL、绑定参数、结果、证据 ID 和状态。工具返回 `needs_clarification` 或 `insufficient_data` 时停止生成经营建议，展示原因和可用下一步。
3. 诊断按总体 → 渠道 × 设备联合分层 → 对称分解 → 单维核对。核对结构项与表现项之和等于总体变化（允许显示舍入差）；单维渠道和设备贡献不能再次相加。
4. 实验只使用有随机分组的成熟用户，按原始分配进行 ITT 分析；核对样本量、SRM、绝对提升、95% CI、业务提升门槛与成本护栏。子组是探索性结果，不包装为总体实验结论。
5. 使用确定性计算结果生成图表；报告文字中的数字必须能回溯到证据。区分 `fact`、`hypothesis`、`action`，每项引用工具证据 ID。
6. 输出实际日期、数据来源、指标口径、结论、证据、限制和建议；报告导出复用本次运行的结果，不触发一轮新取数来替换原始证据。

## 停止条件与边界

- 注册后 7 日尚未完整观察、某期无数据、日期超出覆盖范围时，不把不成熟用户当作未留存，也不拿部分期间冒充完整期间。
- 缺关键口径、任务不支持、要求精确 D7、GMV、利润或其它不存在的指标时，澄清或明确当前工具不支持。
- 分层变化属于描述性分解；未经随机实验，不能把它写成因果关系。
- 统计显著不等于商业可行；业务门槛未通过或 SRM 异常时，不能建议扩大投放。
- 当前 7 日收入与激励成本不构成完整 ROI、LTV 或利润；不将比值改名为这些概念。
- 工具报错时不能编造 SQL 结果；最多依据明确可修正的输入错误重试一次，仍失败则报告缺口。
- 不执行数据库写入、外部投放或自动给业务人员发消息。该 Skill 的交付物是可核验的分析。

这些规则需要由模型实际加载，并配合应用的输入校验、只读查询和确定性计算执行；目录存在本身不构成可靠性证明。
