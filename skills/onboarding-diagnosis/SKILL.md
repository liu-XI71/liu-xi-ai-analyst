---
name: onboarding-diagnosis
description: Diagnose new-user onboarding and exact retention changes from versioned event cohorts, including data-quality gating, ordered funnels, descriptive decomposition, and evidence-backed follow-up actions. Use for registration-to-activation or D1/D7 growth questions, not ecommerce repurchase or causal experiment claims.
---

# 新用户增长诊断

目标是交付可复算的增长决策备忘录：确认变化可信，定位值得优先检查的人群与路径，并说明下一步如何区分解释。

## 口径与执行

使用 `app.domains.onboarding.metadata()` 获取枚举和口径，调用 `analyze(request, path)` 执行业务计算。正式合同仅维护于 [`../../app/data/onboarding_metrics.json`](../../app/data/onboarding_metrics.json)。涉及数据来源、时间边界、批次语义时，读取 [`../../docs/onboarding-data.md`](../../docs/onboarding-data.md)。

请求包含 `question`、`task`、两期注册日期以及可选渠道、端、版本、指标与快照。不得将个人标识、问题原文或任意表达式插入 SQL。

- 精确 D1、精确 D7、次 1—7 日任意回访使用不同指标 ID。问题与显式指标不一致时澄清，不暗改合同。
- 24h 漏斗使用同一个注册 cohort 和严格事件顺序；所有步骤发生在 `[signup_at, signup_at+24h)`。D1/D7 是后续结果，不作为必经漏斗步骤。
- 数值由查询与计算函数产出，不在叙述中补造或调整。

## 决策流程

先读取质量结果，再解释业务指标。`data_quality_blocked` 时列出受影响分区、缺口和回填复查条件，停止受影响的预算与产品建议。`insufficient_data` 时说明无 cohort、范围问题或观察未成熟；不能把它当作零留存。各指标单独判断可用性，可用的 D1 不代表 D7 已成熟。

数据可用后，将总体变化拆为渠道 × 端联合分层的结构项和表现项，检查二者闭合。再读取有序漏斗、版本切片和变更记录。同期版本关联是描述性证据，不能写成因果结论；新/消失分层的分解约定需保留。

解释必须能够被证据区分：给出支持、反证或未排除的混杂，以及下一项验证。不要为了凑数量写空泛假设。建议修复验证时写清主指标、早期信号、围栏和复查触发条件，不声称建议已经带来收益。

## 交付

保留 `metric_contract`、数据截至时间与水位、事实与 SQL 引用、主要切片、有序漏斗、候选解释、行动和限制。未提供负责人时保留“待分配”。公开材料明确数据为匿名合成事件，不宣称真实企业成果。

每条事实应引用返回的 `evidence_ids`，并确认其结果确实支持该表述。未成熟的旁路指标保持不可用，不从原始部分到达事件补算一个未经门禁的答案。
