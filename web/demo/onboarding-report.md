# 新用户留存诊断

运行编号：d5c20f7afe9d6c92d05b3890be8777c2 · 模式：demo · 时间：2026-09-19T09:24:37.144573+00:00

**数据说明：合成演示数据，不代表任何企业真实经营结果。**

本期 精确 D7 留存率 21.27%（191/898），对比期 27.22%（233/856），变化 -5.95 个百分点。渠道 × 端对称分解中，结构贡献 -0.92、组内表现贡献 -5.03 个百分点；质量检查已通过。

## 决策备忘录

```json
{
  "status": "investigate_then_experiment",
  "label": "先定位路径问题，再验证修复增量",
  "actions": [
    "复核 自然流量 / iOS 的来源、端与版本关联。",
    "检查「首屏加载成功」路径的首屏请求和用户反馈。",
    "预注册修复实验、D7 主要结果、样本量与负反馈/性能围栏，再评审增量。"
  ],
  "review_trigger": "下一批完整成熟 cohort；如进入实验，等待预注册观察窗口与样本条件",
  "owner": "待分配",
  "evidence_ids": [
    "onboarding-strata",
    "onboarding-version-slices",
    "onboarding-totals"
  ]
}
```

## 数据质量

```json
{
  "status": "passed",
  "as_of": "2026-09-19 08:00:00",
  "watermark": "2026-09-19 00:00:00",
  "watermarks_by_device": {
    "android": "2026-09-19 00:00:00",
    "ios": "2026-09-19 00:00:00",
    "web": "2026-09-19 00:00:00"
  },
  "required_until": "2026-09-07 00:00:00",
  "checks": [
    {
      "id": "observation_mature",
      "name": "完整观察窗口",
      "status": "passed",
      "observed": "2026-09-19 08:00:00",
      "expected": "2026-09-07 00:00:00",
      "detail": "快照时间必须覆盖完整自然日或实际注册时间 + 24 小时；不截掉未成熟用户后继续解释原请求。",
      "evidence_ids": [
        "onboarding-cohort-scope"
      ]
    },
    {
      "id": "continuous_watermark",
      "name": "连续数据水位",
      "status": "passed",
      "observed": "2026-09-19 00:00:00",
      "expected": "2026-09-07 00:00:00",
      "detail": "水位为所有相关设备分区已完整到达事件时间的排他上界；缺一日不能跳过。",
      "evidence_ids": [
        "onboarding-batch-watermark"
      ]
    },
    {
      "id": "source_manifest",
      "name": "源端清单计数",
      "status": "passed",
      "observed": 0,
      "expected": 0,
      "detail": "按已知源端批次 expected_events 比较已到达去重事件；缺少清单也无法通过连续水位。",
      "evidence_ids": [
        "onboarding-batch-watermark"
      ]
    },
    {
      "id": "schema_version",
      "name": "事件版本兼容",
      "status": "passed",
      "observed": 0,
      "expected": 0,
      "detail": "只接受版本化指标合同支持的埋点 schema。",
      "evidence_ids": [
        "onboarding-event-validation"
      ]
    },
    {
      "id": "event_integrity",
      "name": "事件关系与幂等性",
      "status": "passed",
      "observed": 0,
      "expected": 0,
      "detail": "检查匿名用户归属、事件时间/自然日、批次日期/设备、事件先后与 event_id 唯一性。",
      "evidence_ids": [
        "onboarding-event-validation"
      ]
    }
  ],
  "affected_batches": [],
  "affected_metrics": [],
  "metric_availability": [
    {
      "metric_id": "new_user_retention_d1",
      "metric": "精确 D1 留存率",
      "required_until": "2026-09-01 00:00:00",
      "mature": true,
      "watermark_complete": true,
      "schema_valid": true,
      "event_integrity_valid": true,
      "unsupported_schema_events": 0,
      "invalid_event_relationships": 0,
      "evidence_ids": [
        "onboarding-event-validation-new_user_retention_d1",
        "onboarding-batch-watermark"
      ],
      "available": true
    },
    {
      "metric_id": "new_user_retention_d7",
      "metric": "精确 D7 留存率",
      "required_until": "2026-09-07 00:00:00",
      "mature": true,
      "watermark_complete": true,
      "schema_valid": true,
      "event_integrity_valid": true,
      "unsupported_schema_events": 0,
      "invalid_event_relationships": 0,
      "evidence_ids": [
        "onboarding-event-validation",
        "onboarding-batch-watermark"
      ],
      "available": true
    },
    {
      "metric_id": "return_within_days_1_7",
      "metric": "次 1—7 日内回访率",
      "required_until": "2026-09-07 00:00:00",
      "mature": true,
      "watermark_complete": true,
      "schema_valid": true,
      "event_integrity_valid": true,
      "unsupported_schema_events": 0,
      "invalid_event_relationships": 0,
      "evidence_ids": [
        "onboarding-event-validation",
        "onboarding-batch-watermark"
      ],
      "available": true
    },
    {
      "metric_id": "activated_24h",
      "metric": "24 小时有序激活率",
      "required_until": "2026-08-31 23:55:31",
      "mature": true,
      "watermark_complete": true,
      "schema_valid": true,
      "event_integrity_valid": true,
      "unsupported_schema_events": 0,
      "invalid_event_relationships": 0,
      "evidence_ids": [
        "onboarding-event-validation-new_user_retention_d1",
        "onboarding-batch-watermark"
      ],
      "available": true
    }
  ],
  "message": "所选主指标及有序漏斗质量检查通过；旁路指标按各自窗口单独判断可用性。",
  "cohorts": [
    {
      "period": "current",
      "users": 898,
      "first_signup_date": "2026-08-24",
      "last_signup_date": "2026-08-30",
      "latest_signup_at": "2026-08-30 23:55:31"
    },
    {
      "period": "previous",
      "users": 856,
      "first_signup_date": "2026-08-17",
      "last_signup_date": "2026-08-23",
      "latest_signup_at": "2026-08-23 23:43:21"
    }
  ],
  "provenance": "源端日 × 设备批次清单 + 可见 ingested_at；质量门禁按相关设备分区保守检查，不证明未知源端漏数不存在。"
}
```

## 假设与验证

```json
[
  {
    "id": "mix",
    "title": "获客结构变化影响总体指标",
    "status": "descriptive_support",
    "supporting_evidence_ids": [
      "onboarding-strata",
      "onboarding-change-log"
    ],
    "observation": "对称分解的结构项为 -0.916 pp。",
    "counter_evidence": "控制在联合分层内仍有 -5.034 pp 表现项；纯结构解释不能覆盖这部分变化。",
    "next_test": "对比预算和渠道质量记录，并以固定渠道 × 端权重追踪后续成熟 cohort；不将重新加权当作因果估计。"
  },
  {
    "id": "experience",
    "title": "引导或首屏体验变化影响后续回访",
    "status": "needs_validation",
    "supporting_evidence_ids": [
      "onboarding-version-slices",
      "onboarding-totals",
      "onboarding-change-log"
    ],
    "observation": "本期激活 43.54%，前期 62.50%；存在可检索的端与版本切片。",
    "counter_evidence": "版本发布与渠道结构同时变化；未随机分配版本，用户选择和其他同期变化仍可能解释差异。",
    "next_test": "优先核对当前筛选下「Android / 1.9.0」的首屏请求错误与性能日志，预注册候选路径修复实验；D7 为主要结果，24h 激活为早期信号，负反馈与性能为围栏。"
  },
  {
    "id": "ingestion",
    "title": "数据延迟造成表面下降",
    "status": "not_supported_in_scope",
    "supporting_evidence_ids": [
      "onboarding-batch-watermark",
      "onboarding-event-validation"
    ],
    "observation": "本次主指标与有序漏斗涉及的连续水位、源端清单及事件版本通过检查；旁路指标独立判断。",
    "counter_evidence": "现有已知批次未发现缺口；源端清单自身未知漏报仍不在可验证范围内。",
    "next_test": "下一批次继续核对源端计数、到达时间和 schema；新分区不能沿用旧快照的通过状态。"
  }
]
```

## 分析步骤

```json
[
  {
    "step": 1,
    "tool": "get_metric_contract",
    "purpose": "冻结指标、cohort、时区和完整观察窗口",
    "status": "completed"
  },
  {
    "step": 2,
    "tool": "check_data_quality",
    "purpose": "验证实际到达批次、连续水位和事件版本",
    "status": "completed"
  },
  {
    "step": 3,
    "tool": "query_cohort_metrics",
    "purpose": "用同一 cohort 计算精确留存和有序漏斗",
    "status": "completed"
  },
  {
    "step": 4,
    "tool": "decompose_change",
    "purpose": "区分结构变化、分层表现与版本关联",
    "status": "completed"
  },
  {
    "step": 5,
    "tool": "build_evidence_report",
    "purpose": "组织证据、竞争解释、行动和复查条件",
    "status": "completed"
  }
]
```

## 指标口径

```json
{
  "id": "new_user_retention_d7",
  "name": "精确 D7 留存率",
  "unit": "%",
  "kind": "rate",
  "numerator": "注册后第 7 个自然日发生 app_active 的 cohort 去重用户数",
  "denominator": "D7 自然日已完整结束且数据水位覆盖的注册 cohort 用户数",
  "grain": "用户",
  "window": "注册日 + 7 自然日",
  "maturity": {
    "type": "calendar",
    "days": 7
  },
  "calculation": {
    "success_column": "d7"
  },
  "not_equivalent_to": "次 1—7 日内任意回访率",
  "version": "onboarding.v2.0.0",
  "timezone": "Asia/Shanghai",
  "data_source": "固定种子 710919 的匿名合成产品事件；用于复现增长分析方法，不代表真实企业经营收益",
  "dimensions": [
    "channel",
    "device",
    "app_version"
  ],
  "current_period": [
    "2026-08-24",
    "2026-08-30"
  ],
  "previous_period": [
    "2026-08-17",
    "2026-08-23"
  ],
  "data_as_of": "2026-09-19 08:00:00",
  "watermark": "2026-09-19 00:00:00"
}
```

## 核验事实

- 本期 精确 D7 留存率 21.27%（191/898），对比期 27.22%（233/856），变化 -5.95 个百分点。渠道 × 端对称分解中，结构贡献 -0.92、组内表现贡献 -5.03 个百分点；质量检查已通过。（证据：onboarding-totals, onboarding-strata, onboarding-batch-watermark, onboarding-event-validation）
- 绝对贡献最大的联合分层为 自然流量 / iOS，算术贡献 -4.39 pp；不能把渠道和设备单独分解再相加。（证据：onboarding-strata）
- 本期有序漏斗在「首屏加载成功」这一步流失人数最多：181 人。人数损失与环节转化率变化需要分别观察。（证据：onboarding-totals）
- 相对前期，环节转化率变化最小的步骤为「首屏加载成功」，变化 -18.111 pp。（证据：onboarding-totals）

## 待验证假设

- 将获客结构、产品路径和数据可用性作为竞争解释；版本与留存的同期关联仍需实验或额外证据区分。（证据：onboarding-strata, onboarding-version-slices, onboarding-change-log, onboarding-batch-watermark, onboarding-event-validation）

## 后续行动

- 优先复核 自然流量 / iOS 的用户路径与版本错误记录，保持当前指标口径；验证候选修复后再按预注册实验评审决定是否扩大。（证据：onboarding-strata, onboarding-totals, onboarding-version-slices）

## 结果表

### 数据可用性门禁

完整结果：5行。

| name | status | observed | expected | detail |
| --- | --- | --- | --- | --- |
| 完整观察窗口 | passed | 2026-09-19 08:00:00 | 2026-09-07 00:00:00 | 快照时间必须覆盖完整自然日或实际注册时间 + 24 小时；不截掉未成熟用户后继续解释原请求。 |
| 连续数据水位 | passed | 2026-09-19 00:00:00 | 2026-09-07 00:00:00 | 水位为所有相关设备分区已完整到达事件时间的排他上界；缺一日不能跳过。 |
| 源端清单计数 | passed | 0 | 0 | 按已知源端批次 expected_events 比较已到达去重事件；缺少清单也无法通过连续水位。 |
| 事件版本兼容 | passed | 0 | 0 | 只接受版本化指标合同支持的埋点 schema。 |
| 事件关系与幂等性 | passed | 0 | 0 | 检查匿名用户归属、事件时间/自然日、批次日期/设备、事件先后与 event_id 唯一性。 |
### 不同指标分别判断成熟与可用性

完整结果：4行。

| metric | required_until | mature | watermark_complete | schema_valid | event_integrity_valid | available |
| --- | --- | --- | --- | --- | --- | --- |
| 精确 D1 留存率 | 2026-09-01 00:00:00 | True | True | True | True | True |
| 精确 D7 留存率 | 2026-09-07 00:00:00 | True | True | True | True | True |
| 次 1—7 日内回访率 | 2026-09-07 00:00:00 | True | True | True | True | True |
| 24 小时有序激活率 | 2026-08-31 23:55:31 | True | True | True | True | True |
### 相同 cohort，不同留存窗口分别计算

完整结果：4行。

| metric | previous_users | current_users | previous_successes | current_successes | previous_pct | current_pct | delta_pp | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 精确 D1 留存率 | 856 | 898 | 333 | 265 | 38.902 | 29.51 | -9.392 | available |
| 精确 D7 留存率 | 856 | 898 | 233 | 191 | 27.22 | 21.269 | -5.95 | available |
| 次 1—7 日内回访率 | 856 | 898 | 513 | 423 | 59.93 | 47.105 | -12.825 | available |
| 24 小时有序激活率 | 856 | 898 | 535 | 391 | 62.5 | 43.541 | -18.959 | available |
### 渠道 × 端对称分解（百分点）

完整结果：12行。

| segment | previous_users | current_users | previous_rate_pct | current_rate_pct | mix_pp | performance_pp | total_pp |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 自然流量 / iOS | 155 | 51 | 31.613 | 23.529 | -3.427 | -0.961 | -4.388 |
| 自然流量 / Android | 186 | 120 | 22.581 | 25.833 | -2.025 | 0.571 | -1.454 |
| 自然流量 / 网页 | 55 | 26 | 34.545 | 26.923 | -1.085 | -0.355 | -1.44 |
| 好友推荐 / Android | 49 | 41 | 32.653 | 19.512 | -0.302 | -0.676 | -0.978 |
| 社交投放 / 网页 | 30 | 26 | 23.333 | 15.385 | -0.118 | -0.254 | -0.372 |
| 好友推荐 / 网页 | 11 | 12 | 18.182 | 8.333 | 0.007 | -0.129 | -0.122 |
| 好友推荐 / iOS | 31 | 21 | 25.806 | 38.095 | -0.41 | 0.366 | -0.044 |
| 社交投放 / iOS | 71 | 72 | 23.944 | 25.0 | -0.068 | 0.086 | 0.018 |
| 付费搜索 / iOS | 72 | 116 | 30.556 | 21.552 | 1.174 | -0.96 | 0.214 |
| 社交投放 / Android | 71 | 124 | 26.761 | 18.548 | 1.249 | -0.908 | 0.342 |
| 付费搜索 / 网页 | 24 | 38 | 8.333 | 21.053 | 0.21 | 0.447 | 0.657 |
| 付费搜索 / Android | 101 | 251 | 29.703 | 18.327 | 3.879 | -2.261 | 1.618 |
### 版本关联与体验围栏

完整结果：8行。

| period | segment | users | metric_pct | activation_pct | first_feed_failure_pct | feed_result_unresolved | negative_feedback_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| current | Android / 1.8.0 | 69 | 24.638 | 71.014 | 0.0 | 0 | 1.449 |
| current | Android / 1.9.0 | 467 | 19.486 | 30.407 | 43.597 | 0 | 8.994 |
| current | iOS / 1.8.0 | 260 | 24.231 | 52.692 | 6.573 | 0 | 3.462 |
| current | 网页 / 1.8.0 | 102 | 19.608 | 61.765 | 7.865 | 0 | 3.922 |
| previous | Android / 1.8.0 | 330 | 27.576 | 63.03 | 5.556 | 0 | 4.242 |
| previous | Android / 1.9.0 | 77 | 20.779 | 49.351 | 20.635 | 0 | 5.195 |
| previous | iOS / 1.8.0 | 329 | 29.179 | 64.438 | 6.207 | 0 | 2.432 |
| previous | 网页 / 1.8.0 | 120 | 25.0 | 64.167 | 3.883 | 0 | 0.833 |
### 同期变更记录

完整结果：3行。

| change_at | device | app_version | change_type | description |
| --- | --- | --- | --- | --- |
| 2026-08-17 00:00:00 | android | 1.9.0 | release | Android 1.9.0 开始分阶段发布，调整新用户引导与首屏推荐接口。 |
| 2026-08-24 00:00:00 | 未成熟/缺失 | 未成熟/缺失 | acquisition | 获客预算分配调整，提高付费搜索与社交渠道的配置比例。 |
| 2026-08-24 00:00:00 | android | 1.9.0 | release | Android 1.9.0 扩大发布覆盖；需要结合版本、端和用户结构评估效果。 |
### 注册后 24 小时有序漏斗

完整结果：4行。

| step | previous_users | current_users | previous_cohort_pct | current_cohort_pct | previous_step_pct | current_step_pct | step_delta_pp | current_lost_users |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 注册成功 | 856 | 898 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 | 0 |
| 完成引导 | 744 | 725 | 86.916 | 80.735 | 86.916 | 80.735 | -6.181 | 173 |
| 首屏加载成功 | 693 | 544 | 80.958 | 60.579 | 93.145 | 75.034 | -18.111 | 181 |
| 有效内容消费 ≥ 60 秒 | 535 | 391 | 62.5 | 43.541 | 77.201 | 71.875 | -5.326 | 153 |

### 图表数据：日活跃背景（全注册样本，逐日去重）

原始单位：人；空值表示未成熟/缺失。

| event_date | active_users |
| --- | --- |
| 2026-08-17 | 552 |
| 2026-08-18 | 560 |
| 2026-08-19 | 545 |
| 2026-08-20 | 525 |
| 2026-08-21 | 587 |
| 2026-08-22 | 526 |
| 2026-08-23 | 567 |
| 2026-08-24 | 542 |
| 2026-08-25 | 532 |
| 2026-08-26 | 513 |
| 2026-08-27 | 527 |
| 2026-08-28 | 502 |
| 2026-08-29 | 507 |
| 2026-08-30 | 531 |

### 图表数据：精确 D7 留存率：成熟 cohort 趋势

原始单位：%；空值表示未成熟/缺失。

| signup_date | metric_pct |
| --- | --- |
| 2026-08-17 | 27.11864406779661 |
| 2026-08-18 | 25.19083969465649 |
| 2026-08-19 | 23.529411764705884 |
| 2026-08-20 | 31.9672131147541 |
| 2026-08-21 | 30.0 |
| 2026-08-22 | 24.324324324324323 |
| 2026-08-23 | 28.0 |
| 2026-08-24 | 14.166666666666666 |
| 2026-08-25 | 20.74074074074074 |
| 2026-08-26 | 22.22222222222222 |
| 2026-08-27 | 28.571428571428573 |
| 2026-08-28 | 17.094017094017094 |
| 2026-08-29 | 20.72072072072072 |
| 2026-08-30 | 23.571428571428573 |

### 图表数据：总体变化的算术分解

原始单位：百分点；空值表示未成熟/缺失。

| component | contribution_pp |
| --- | --- |
| 结构变化 | -0.916 |
| 组内表现 | -5.034 |

### 图表数据：同 cohort 的 24 小时路径

原始单位：%；空值表示未成熟/缺失。

| step | previous_cohort_pct | current_cohort_pct |
| --- | --- | --- |
| 注册成功 | 100.0 | 100.0 |
| 完成引导 | 86.916 | 80.735 |
| 首屏加载成功 | 80.958 | 60.579 |
| 有效内容消费 ≥ 60 秒 | 62.5 | 43.541 |

### 图表数据：本期端 × 版本主指标

原始单位：%；空值表示未成熟/缺失。

| segment | metric_pct | activation_pct |
| --- | --- | --- |
| Android / 1.8.0 | 24.638 | 71.014 |
| Android / 1.9.0 | 19.486 | 30.407 |
| iOS / 1.8.0 | 24.231 | 52.692 |
| 网页 / 1.8.0 | 19.608 | 61.765 |

## SQL 与证据

### onboarding-cohort-scope · 注册 cohort 范围、人数与最晚注册时间

来源：固定种子 710919 的匿名合成产品事件；用于复现增长分析方法，不代表真实企业经营收益；口径版本：onboarding.v2.0.0

```sql
WITH periods AS (
      SELECT 'current' AS period, :start AS start_date, :end AS end_date
      UNION ALL SELECT 'previous', :compare_start, :compare_end
    ), users AS (
      SELECT p.period, u.* FROM onboarding_users u JOIN periods p
        ON u.signup_date BETWEEN p.start_date AND p.end_date
      WHERE u.signup_at < :as_of
    ) SELECT period, COUNT(*) AS users, MIN(signup_date) AS first_signup_date, MAX(signup_date) AS last_signup_date, MAX(signup_at) AS latest_signup_at FROM users GROUP BY period ORDER BY period
```
参数：{"start": "2026-08-24", "end": "2026-08-30", "compare_start": "2026-08-17", "compare_end": "2026-08-23", "as_of": "2026-09-19 08:00:00", "activation_seconds": 60}
### onboarding-cohort-devices · 当前筛选实际涉及的设备分区

来源：固定种子 710919 的匿名合成产品事件；用于复现增长分析方法，不代表真实企业经营收益；口径版本：onboarding.v2.0.0

```sql
WITH periods AS (
      SELECT 'current' AS period, :start AS start_date, :end AS end_date
      UNION ALL SELECT 'previous', :compare_start, :compare_end
    ), users AS (
      SELECT p.period, u.* FROM onboarding_users u JOIN periods p
        ON u.signup_date BETWEEN p.start_date AND p.end_date
      WHERE u.signup_at < :as_of
    ) SELECT DISTINCT device FROM users ORDER BY device
```
参数：{"start": "2026-08-24", "end": "2026-08-30", "compare_start": "2026-08-17", "compare_end": "2026-08-23", "as_of": "2026-09-19 08:00:00", "activation_seconds": 60}
### onboarding-batch-watermark · 源端批次清单与快照可见事件，计算连续设备水位

来源：固定种子 710919 的匿名合成产品事件；用于复现增长分析方法，不代表真实企业经营收益；口径版本：onboarding.v2.0.0

```sql
SELECT b.event_date,b.device,b.expected_events,COUNT(e.event_id) AS observed_events,
      MAX(e.ingested_at) AS latest_arrival
      FROM onboarding_ingest_batches b LEFT JOIN onboarding_events e
        ON e.batch_id=b.batch_id AND e.ingested_at<=:as_of
      WHERE b.event_date BETWEEN :batch_start AND :batch_end
        AND b.manifest_available_at<=:as_of AND b.device IN (:quality_device_0,:quality_device_1,:quality_device_2)
      GROUP BY b.batch_id ORDER BY b.event_date,b.device
```
参数：{"start": "2026-08-24", "end": "2026-08-30", "compare_start": "2026-08-17", "compare_end": "2026-08-23", "as_of": "2026-09-19 08:00:00", "activation_seconds": 60, "batch_start": "2026-06-01", "batch_end": "2026-09-18", "quality_device_0": "android", "quality_device_1": "ios", "quality_device_2": "web"}
### onboarding-event-validation · 窗口内事件版本、时间/日期、用户归属与批次一致性

来源：固定种子 710919 的匿名合成产品事件；用于复现增长分析方法，不代表真实企业经营收益；口径版本：onboarding.v2.0.0

```sql
SELECT COUNT(*) AS visible_events,
          COALESCE(SUM(CASE WHEN e.schema_version NOT IN (:schema_0) THEN 1 ELSE 0 END),0) AS unsupported_schema_events,
          COALESCE(SUM(CASE WHEN u.user_id IS NULL OR b.batch_id IS NULL
            OR datetime(e.event_time) IS NULL OR datetime(e.ingested_at) IS NULL
            OR datetime(e.event_time,'+0 days')<>e.event_time
            OR datetime(e.ingested_at,'+0 days')<>e.ingested_at
            OR datetime(u.signup_at,'+0 days') IS NULL
            OR datetime(u.signup_at,'+0 days')<>u.signup_at
            OR u.signup_date<>date(u.signup_at)
            OR e.event_time<u.signup_at OR e.event_time>e.ingested_at
            OR e.event_date<>date(e.event_time)
            OR e.device<>u.device OR e.channel<>u.channel OR e.app_version<>u.app_version
            OR e.batch_id<>(e.event_date || ':' || e.device)
            OR e.event_date<>b.event_date OR e.device<>b.device
            THEN 1 ELSE 0 END),0) AS invalid_event_relationships,
          COUNT(*)-COUNT(DISTINCT e.event_id) AS duplicate_event_ids
          FROM onboarding_events e LEFT JOIN onboarding_users u ON e.user_id=u.user_id
          LEFT JOIN onboarding_ingest_batches b ON e.batch_id=b.batch_id
          WHERE (e.event_date BETWEEN :relevant_start AND :relevant_end
            OR date(e.event_time) BETWEEN :relevant_start AND :relevant_end
            OR b.event_date BETWEEN :relevant_start AND :relevant_end)
            AND (u.device IN (:quality_device_0,:quality_device_1,:quality_device_2) OR e.device IN (:quality_device_0,:quality_device_1,:quality_device_2)
              OR b.device IN (:quality_device_0,:quality_device_1,:quality_device_2))
            AND e.ingested_at<=:as_of
```
参数：{"start": "2026-08-24", "end": "2026-08-30", "compare_start": "2026-08-17", "compare_end": "2026-08-23", "as_of": "2026-09-19 08:00:00", "activation_seconds": 60, "batch_start": "2026-06-01", "batch_end": "2026-09-18", "quality_device_0": "android", "quality_device_1": "ios", "quality_device_2": "web", "relevant_start": "2026-08-17", "relevant_end": "2026-09-06", "schema_0": "1.0"}
### onboarding-event-validation-new_user_retention_d1 · 窗口内事件版本、时间/日期、用户归属与批次一致性

来源：固定种子 710919 的匿名合成产品事件；用于复现增长分析方法，不代表真实企业经营收益；口径版本：onboarding.v2.0.0

```sql
SELECT COUNT(*) AS visible_events,
          COALESCE(SUM(CASE WHEN e.schema_version NOT IN (:schema_0) THEN 1 ELSE 0 END),0) AS unsupported_schema_events,
          COALESCE(SUM(CASE WHEN u.user_id IS NULL OR b.batch_id IS NULL
            OR datetime(e.event_time) IS NULL OR datetime(e.ingested_at) IS NULL
            OR datetime(e.event_time,'+0 days')<>e.event_time
            OR datetime(e.ingested_at,'+0 days')<>e.ingested_at
            OR datetime(u.signup_at,'+0 days') IS NULL
            OR datetime(u.signup_at,'+0 days')<>u.signup_at
            OR u.signup_date<>date(u.signup_at)
            OR e.event_time<u.signup_at OR e.event_time>e.ingested_at
            OR e.event_date<>date(e.event_time)
            OR e.device<>u.device OR e.channel<>u.channel OR e.app_version<>u.app_version
            OR e.batch_id<>(e.event_date || ':' || e.device)
            OR e.event_date<>b.event_date OR e.device<>b.device
            THEN 1 ELSE 0 END),0) AS invalid_event_relationships,
          COUNT(*)-COUNT(DISTINCT e.event_id) AS duplicate_event_ids
          FROM onboarding_events e LEFT JOIN onboarding_users u ON e.user_id=u.user_id
          LEFT JOIN onboarding_ingest_batches b ON e.batch_id=b.batch_id
          WHERE (e.event_date BETWEEN :relevant_start AND :relevant_end
            OR date(e.event_time) BETWEEN :relevant_start AND :relevant_end
            OR b.event_date BETWEEN :relevant_start AND :relevant_end)
            AND (u.device IN (:quality_device_0,:quality_device_1,:quality_device_2) OR e.device IN (:quality_device_0,:quality_device_1,:quality_device_2)
              OR b.device IN (:quality_device_0,:quality_device_1,:quality_device_2))
            AND e.ingested_at<=:as_of
```
参数：{"start": "2026-08-24", "end": "2026-08-30", "compare_start": "2026-08-17", "compare_end": "2026-08-23", "as_of": "2026-09-19 08:00:00", "activation_seconds": 60, "batch_start": "2026-06-01", "batch_end": "2026-09-18", "quality_device_0": "android", "quality_device_1": "ios", "quality_device_2": "web", "relevant_start": "2026-08-17", "relevant_end": "2026-08-31", "schema_0": "1.0"}
### onboarding-totals · 两期 cohort 指标；未成熟或缺数的旁路指标保持 NULL

来源：固定种子 710919 的匿名合成产品事件；用于复现增长分析方法，不代表真实企业经营收益；口径版本：onboarding.v2.0.0

```sql
WITH periods AS (
      SELECT 'current' AS period, :start AS start_date, :end AS end_date
      UNION ALL SELECT 'previous', :compare_start, :compare_end
    ), users AS (
      SELECT p.period, u.* FROM onboarding_users u JOIN periods p
        ON u.signup_date BETWEEN p.start_date AND p.end_date
      WHERE u.signup_at < :as_of
    ), requests AS (
      SELECT u.*, (SELECT e.event_id FROM onboarding_events e
        WHERE e.user_id=u.user_id AND e.event_name='feed_requested'
          AND e.event_time>=u.signup_at AND e.event_time<datetime(u.signup_at,'+24 hours')
          AND e.ingested_at<=:as_of ORDER BY e.event_time,e.event_id LIMIT 1
      ) AS first_request_event_id FROM users u
    ), onboarding AS (
      SELECT u.*, r.request_id AS first_request_id, r.event_time AS first_requested_at,
        (SELECT MIN(e.event_time) FROM onboarding_events e
        WHERE e.user_id=u.user_id AND e.event_name='onboarding_completed'
          AND e.event_time>u.signup_at AND e.event_time<datetime(u.signup_at,'+24 hours')
          AND e.ingested_at<=:as_of) AS onboarded_at FROM requests u
      LEFT JOIN onboarding_events r ON r.event_id=u.first_request_event_id
    ), feed AS (
      SELECT u.*, (SELECT COUNT(DISTINCT e.event_name) FROM onboarding_events e
        WHERE e.user_id=u.user_id AND e.request_id=u.first_request_id
          AND e.event_name IN ('first_feed_success','first_feed_failure')
          AND e.event_time>=u.first_requested_at
          AND e.event_time<datetime(u.signup_at,'+24 hours')
          AND e.ingested_at<=:as_of) AS first_result_kinds,
        (SELECT COUNT(*) FROM onboarding_events e
          WHERE e.user_id=u.user_id AND e.event_name='feed_requested'
            AND e.request_id=u.first_request_id AND e.ingested_at<=:as_of
        ) AS first_request_id_occurrences,
        (SELECT MIN(e.event_time) FROM onboarding_events e
        WHERE e.user_id=u.user_id AND e.event_name='first_feed_success'
          AND e.event_time>u.onboarded_at AND e.event_time<datetime(u.signup_at,'+24 hours')
          AND e.ingested_at<=:as_of) AS feed_at FROM onboarding u
    ), cohort AS (
      SELECT u.*, 1 AS registered, (onboarded_at IS NOT NULL) AS onboarded,
        (feed_at IS NOT NULL) AS feed_success,
        EXISTS(SELECT 1 FROM onboarding_events e WHERE e.user_id=u.user_id
          AND e.event_name='content_consumed' AND e.duration_seconds>=:activation_seconds
          AND e.event_time>u.feed_at AND e.event_time<datetime(u.signup_at,'+24 hours')
          AND e.ingested_at<=:as_of) AS activated,
        EXISTS(SELECT 1 FROM onboarding_events e WHERE e.user_id=u.user_id
          AND e.event_name='app_active' AND date(e.event_time)=date(u.signup_date,'+1 day')
          AND e.ingested_at<=:as_of) AS d1,
        EXISTS(SELECT 1 FROM onboarding_events e WHERE e.user_id=u.user_id
          AND e.event_name='app_active' AND date(e.event_time)=date(u.signup_date,'+7 days')
          AND e.ingested_at<=:as_of) AS d7,
        EXISTS(SELECT 1 FROM onboarding_events e WHERE e.user_id=u.user_id
          AND e.event_name='app_active' AND date(e.event_time)>u.signup_date
          AND date(e.event_time)<=date(u.signup_date,'+7 days') AND e.ingested_at<=:as_of) AS within7,
        (first_request_event_id IS NOT NULL) AS feed_requested,
        (first_request_event_id IS NOT NULL AND
          (first_request_id IS NULL OR first_request_id='' OR first_result_kinds<>1
           OR first_request_id_occurrences<>1)) AS feed_result_unresolved,
        CASE WHEN first_request_id IS NOT NULL AND first_request_id<>''
          AND first_result_kinds=1 AND first_request_id_occurrences=1 THEN
          EXISTS(SELECT 1 FROM onboarding_events e WHERE e.user_id=u.user_id
            AND e.event_name='first_feed_failure' AND e.request_id=u.first_request_id
            AND e.event_time>=u.first_requested_at
            AND e.event_time<datetime(u.signup_at,'+24 hours') AND e.ingested_at<=:as_of)
          ELSE NULL END AS feed_failed,
        EXISTS(SELECT 1 FROM onboarding_events e WHERE e.user_id=u.user_id
          AND e.event_name='negative_feedback' AND e.event_time>=u.signup_at
          AND e.event_time<datetime(u.signup_at,'+24 hours') AND e.ingested_at<=:as_of) AS negative_feedback
      FROM feed u
    ) SELECT period,COUNT(*) AS users,
      SUM(registered) AS registered,SUM(onboarded) AS onboarded,SUM(feed_success) AS feed_success,
      SUM(activated) AS activated,SUM(d1) AS d1,SUM(d7) AS d7,SUM(within7) AS within7,
      SUM(feed_requested) AS feed_requested,
      CASE WHEN SUM(feed_result_unresolved)=0 THEN COALESCE(SUM(feed_failed),0) ELSE NULL END AS feed_failed,
      SUM(feed_result_unresolved) AS feed_result_unresolved,
      SUM(negative_feedback) AS negative_feedback FROM cohort GROUP BY period ORDER BY period
```
参数：{"start": "2026-08-24", "end": "2026-08-30", "compare_start": "2026-08-17", "compare_end": "2026-08-23", "as_of": "2026-09-19 08:00:00", "activation_seconds": 60}
### onboarding-strata · 渠道 × 端的两期联合分层

来源：固定种子 710919 的匿名合成产品事件；用于复现增长分析方法，不代表真实企业经营收益；口径版本：onboarding.v2.0.0

```sql
WITH periods AS (
      SELECT 'current' AS period, :start AS start_date, :end AS end_date
      UNION ALL SELECT 'previous', :compare_start, :compare_end
    ), users AS (
      SELECT p.period, u.* FROM onboarding_users u JOIN periods p
        ON u.signup_date BETWEEN p.start_date AND p.end_date
      WHERE u.signup_at < :as_of
    ), requests AS (
      SELECT u.*, (SELECT e.event_id FROM onboarding_events e
        WHERE e.user_id=u.user_id AND e.event_name='feed_requested'
          AND e.event_time>=u.signup_at AND e.event_time<datetime(u.signup_at,'+24 hours')
          AND e.ingested_at<=:as_of ORDER BY e.event_time,e.event_id LIMIT 1
      ) AS first_request_event_id FROM users u
    ), onboarding AS (
      SELECT u.*, r.request_id AS first_request_id, r.event_time AS first_requested_at,
        (SELECT MIN(e.event_time) FROM onboarding_events e
        WHERE e.user_id=u.user_id AND e.event_name='onboarding_completed'
          AND e.event_time>u.signup_at AND e.event_time<datetime(u.signup_at,'+24 hours')
          AND e.ingested_at<=:as_of) AS onboarded_at FROM requests u
      LEFT JOIN onboarding_events r ON r.event_id=u.first_request_event_id
    ), feed AS (
      SELECT u.*, (SELECT COUNT(DISTINCT e.event_name) FROM onboarding_events e
        WHERE e.user_id=u.user_id AND e.request_id=u.first_request_id
          AND e.event_name IN ('first_feed_success','first_feed_failure')
          AND e.event_time>=u.first_requested_at
          AND e.event_time<datetime(u.signup_at,'+24 hours')
          AND e.ingested_at<=:as_of) AS first_result_kinds,
        (SELECT COUNT(*) FROM onboarding_events e
          WHERE e.user_id=u.user_id AND e.event_name='feed_requested'
            AND e.request_id=u.first_request_id AND e.ingested_at<=:as_of
        ) AS first_request_id_occurrences,
        (SELECT MIN(e.event_time) FROM onboarding_events e
        WHERE e.user_id=u.user_id AND e.event_name='first_feed_success'
          AND e.event_time>u.onboarded_at AND e.event_time<datetime(u.signup_at,'+24 hours')
          AND e.ingested_at<=:as_of) AS feed_at FROM onboarding u
    ), cohort AS (
      SELECT u.*, 1 AS registered, (onboarded_at IS NOT NULL) AS onboarded,
        (feed_at IS NOT NULL) AS feed_success,
        EXISTS(SELECT 1 FROM onboarding_events e WHERE e.user_id=u.user_id
          AND e.event_name='content_consumed' AND e.duration_seconds>=:activation_seconds
          AND e.event_time>u.feed_at AND e.event_time<datetime(u.signup_at,'+24 hours')
          AND e.ingested_at<=:as_of) AS activated,
        EXISTS(SELECT 1 FROM onboarding_events e WHERE e.user_id=u.user_id
          AND e.event_name='app_active' AND date(e.event_time)=date(u.signup_date,'+1 day')
          AND e.ingested_at<=:as_of) AS d1,
        EXISTS(SELECT 1 FROM onboarding_events e WHERE e.user_id=u.user_id
          AND e.event_name='app_active' AND date(e.event_time)=date(u.signup_date,'+7 days')
          AND e.ingested_at<=:as_of) AS d7,
        EXISTS(SELECT 1 FROM onboarding_events e WHERE e.user_id=u.user_id
          AND e.event_name='app_active' AND date(e.event_time)>u.signup_date
          AND date(e.event_time)<=date(u.signup_date,'+7 days') AND e.ingested_at<=:as_of) AS within7,
        (first_request_event_id IS NOT NULL) AS feed_requested,
        (first_request_event_id IS NOT NULL AND
          (first_request_id IS NULL OR first_request_id='' OR first_result_kinds<>1
           OR first_request_id_occurrences<>1)) AS feed_result_unresolved,
        CASE WHEN first_request_id IS NOT NULL AND first_request_id<>''
          AND first_result_kinds=1 AND first_request_id_occurrences=1 THEN
          EXISTS(SELECT 1 FROM onboarding_events e WHERE e.user_id=u.user_id
            AND e.event_name='first_feed_failure' AND e.request_id=u.first_request_id
            AND e.event_time>=u.first_requested_at
            AND e.event_time<datetime(u.signup_at,'+24 hours') AND e.ingested_at<=:as_of)
          ELSE NULL END AS feed_failed,
        EXISTS(SELECT 1 FROM onboarding_events e WHERE e.user_id=u.user_id
          AND e.event_name='negative_feedback' AND e.event_time>=u.signup_at
          AND e.event_time<datetime(u.signup_at,'+24 hours') AND e.ingested_at<=:as_of) AS negative_feedback
      FROM feed u
    ) SELECT period,channel,device,COUNT(*) AS users,SUM(d7) AS retained_users FROM cohort GROUP BY period,channel,device ORDER BY period,channel,device
```
参数：{"start": "2026-08-24", "end": "2026-08-30", "compare_start": "2026-08-17", "compare_end": "2026-08-23", "as_of": "2026-09-19 08:00:00", "activation_seconds": 60}
### onboarding-daily · 按注册 cohort 日计算的主指标趋势

来源：固定种子 710919 的匿名合成产品事件；用于复现增长分析方法，不代表真实企业经营收益；口径版本：onboarding.v2.0.0

```sql
WITH periods AS (
      SELECT 'current' AS period, :start AS start_date, :end AS end_date
      UNION ALL SELECT 'previous', :compare_start, :compare_end
    ), users AS (
      SELECT p.period, u.* FROM onboarding_users u JOIN periods p
        ON u.signup_date BETWEEN p.start_date AND p.end_date
      WHERE u.signup_at < :as_of
    ), requests AS (
      SELECT u.*, (SELECT e.event_id FROM onboarding_events e
        WHERE e.user_id=u.user_id AND e.event_name='feed_requested'
          AND e.event_time>=u.signup_at AND e.event_time<datetime(u.signup_at,'+24 hours')
          AND e.ingested_at<=:as_of ORDER BY e.event_time,e.event_id LIMIT 1
      ) AS first_request_event_id FROM users u
    ), onboarding AS (
      SELECT u.*, r.request_id AS first_request_id, r.event_time AS first_requested_at,
        (SELECT MIN(e.event_time) FROM onboarding_events e
        WHERE e.user_id=u.user_id AND e.event_name='onboarding_completed'
          AND e.event_time>u.signup_at AND e.event_time<datetime(u.signup_at,'+24 hours')
          AND e.ingested_at<=:as_of) AS onboarded_at FROM requests u
      LEFT JOIN onboarding_events r ON r.event_id=u.first_request_event_id
    ), feed AS (
      SELECT u.*, (SELECT COUNT(DISTINCT e.event_name) FROM onboarding_events e
        WHERE e.user_id=u.user_id AND e.request_id=u.first_request_id
          AND e.event_name IN ('first_feed_success','first_feed_failure')
          AND e.event_time>=u.first_requested_at
          AND e.event_time<datetime(u.signup_at,'+24 hours')
          AND e.ingested_at<=:as_of) AS first_result_kinds,
        (SELECT COUNT(*) FROM onboarding_events e
          WHERE e.user_id=u.user_id AND e.event_name='feed_requested'
            AND e.request_id=u.first_request_id AND e.ingested_at<=:as_of
        ) AS first_request_id_occurrences,
        (SELECT MIN(e.event_time) FROM onboarding_events e
        WHERE e.user_id=u.user_id AND e.event_name='first_feed_success'
          AND e.event_time>u.onboarded_at AND e.event_time<datetime(u.signup_at,'+24 hours')
          AND e.ingested_at<=:as_of) AS feed_at FROM onboarding u
    ), cohort AS (
      SELECT u.*, 1 AS registered, (onboarded_at IS NOT NULL) AS onboarded,
        (feed_at IS NOT NULL) AS feed_success,
        EXISTS(SELECT 1 FROM onboarding_events e WHERE e.user_id=u.user_id
          AND e.event_name='content_consumed' AND e.duration_seconds>=:activation_seconds
          AND e.event_time>u.feed_at AND e.event_time<datetime(u.signup_at,'+24 hours')
          AND e.ingested_at<=:as_of) AS activated,
        EXISTS(SELECT 1 FROM onboarding_events e WHERE e.user_id=u.user_id
          AND e.event_name='app_active' AND date(e.event_time)=date(u.signup_date,'+1 day')
          AND e.ingested_at<=:as_of) AS d1,
        EXISTS(SELECT 1 FROM onboarding_events e WHERE e.user_id=u.user_id
          AND e.event_name='app_active' AND date(e.event_time)=date(u.signup_date,'+7 days')
          AND e.ingested_at<=:as_of) AS d7,
        EXISTS(SELECT 1 FROM onboarding_events e WHERE e.user_id=u.user_id
          AND e.event_name='app_active' AND date(e.event_time)>u.signup_date
          AND date(e.event_time)<=date(u.signup_date,'+7 days') AND e.ingested_at<=:as_of) AS within7,
        (first_request_event_id IS NOT NULL) AS feed_requested,
        (first_request_event_id IS NOT NULL AND
          (first_request_id IS NULL OR first_request_id='' OR first_result_kinds<>1
           OR first_request_id_occurrences<>1)) AS feed_result_unresolved,
        CASE WHEN first_request_id IS NOT NULL AND first_request_id<>''
          AND first_result_kinds=1 AND first_request_id_occurrences=1 THEN
          EXISTS(SELECT 1 FROM onboarding_events e WHERE e.user_id=u.user_id
            AND e.event_name='first_feed_failure' AND e.request_id=u.first_request_id
            AND e.event_time>=u.first_requested_at
            AND e.event_time<datetime(u.signup_at,'+24 hours') AND e.ingested_at<=:as_of)
          ELSE NULL END AS feed_failed,
        EXISTS(SELECT 1 FROM onboarding_events e WHERE e.user_id=u.user_id
          AND e.event_name='negative_feedback' AND e.event_time>=u.signup_at
          AND e.event_time<datetime(u.signup_at,'+24 hours') AND e.ingested_at<=:as_of) AS negative_feedback
      FROM feed u
    ) SELECT period,signup_date,COUNT(*) AS users,SUM(d7) AS successes,100.0*SUM(d7)/COUNT(*) AS metric_pct FROM cohort GROUP BY period,signup_date ORDER BY signup_date
```
参数：{"start": "2026-08-24", "end": "2026-08-30", "compare_start": "2026-08-17", "compare_end": "2026-08-23", "as_of": "2026-09-19 08:00:00", "activation_seconds": 60}
### onboarding-version-slices · 端 × 版本的留存、漏斗和首次请求失败

来源：固定种子 710919 的匿名合成产品事件；用于复现增长分析方法，不代表真实企业经营收益；口径版本：onboarding.v2.0.0

```sql
WITH periods AS (
      SELECT 'current' AS period, :start AS start_date, :end AS end_date
      UNION ALL SELECT 'previous', :compare_start, :compare_end
    ), users AS (
      SELECT p.period, u.* FROM onboarding_users u JOIN periods p
        ON u.signup_date BETWEEN p.start_date AND p.end_date
      WHERE u.signup_at < :as_of
    ), requests AS (
      SELECT u.*, (SELECT e.event_id FROM onboarding_events e
        WHERE e.user_id=u.user_id AND e.event_name='feed_requested'
          AND e.event_time>=u.signup_at AND e.event_time<datetime(u.signup_at,'+24 hours')
          AND e.ingested_at<=:as_of ORDER BY e.event_time,e.event_id LIMIT 1
      ) AS first_request_event_id FROM users u
    ), onboarding AS (
      SELECT u.*, r.request_id AS first_request_id, r.event_time AS first_requested_at,
        (SELECT MIN(e.event_time) FROM onboarding_events e
        WHERE e.user_id=u.user_id AND e.event_name='onboarding_completed'
          AND e.event_time>u.signup_at AND e.event_time<datetime(u.signup_at,'+24 hours')
          AND e.ingested_at<=:as_of) AS onboarded_at FROM requests u
      LEFT JOIN onboarding_events r ON r.event_id=u.first_request_event_id
    ), feed AS (
      SELECT u.*, (SELECT COUNT(DISTINCT e.event_name) FROM onboarding_events e
        WHERE e.user_id=u.user_id AND e.request_id=u.first_request_id
          AND e.event_name IN ('first_feed_success','first_feed_failure')
          AND e.event_time>=u.first_requested_at
          AND e.event_time<datetime(u.signup_at,'+24 hours')
          AND e.ingested_at<=:as_of) AS first_result_kinds,
        (SELECT COUNT(*) FROM onboarding_events e
          WHERE e.user_id=u.user_id AND e.event_name='feed_requested'
            AND e.request_id=u.first_request_id AND e.ingested_at<=:as_of
        ) AS first_request_id_occurrences,
        (SELECT MIN(e.event_time) FROM onboarding_events e
        WHERE e.user_id=u.user_id AND e.event_name='first_feed_success'
          AND e.event_time>u.onboarded_at AND e.event_time<datetime(u.signup_at,'+24 hours')
          AND e.ingested_at<=:as_of) AS feed_at FROM onboarding u
    ), cohort AS (
      SELECT u.*, 1 AS registered, (onboarded_at IS NOT NULL) AS onboarded,
        (feed_at IS NOT NULL) AS feed_success,
        EXISTS(SELECT 1 FROM onboarding_events e WHERE e.user_id=u.user_id
          AND e.event_name='content_consumed' AND e.duration_seconds>=:activation_seconds
          AND e.event_time>u.feed_at AND e.event_time<datetime(u.signup_at,'+24 hours')
          AND e.ingested_at<=:as_of) AS activated,
        EXISTS(SELECT 1 FROM onboarding_events e WHERE e.user_id=u.user_id
          AND e.event_name='app_active' AND date(e.event_time)=date(u.signup_date,'+1 day')
          AND e.ingested_at<=:as_of) AS d1,
        EXISTS(SELECT 1 FROM onboarding_events e WHERE e.user_id=u.user_id
          AND e.event_name='app_active' AND date(e.event_time)=date(u.signup_date,'+7 days')
          AND e.ingested_at<=:as_of) AS d7,
        EXISTS(SELECT 1 FROM onboarding_events e WHERE e.user_id=u.user_id
          AND e.event_name='app_active' AND date(e.event_time)>u.signup_date
          AND date(e.event_time)<=date(u.signup_date,'+7 days') AND e.ingested_at<=:as_of) AS within7,
        (first_request_event_id IS NOT NULL) AS feed_requested,
        (first_request_event_id IS NOT NULL AND
          (first_request_id IS NULL OR first_request_id='' OR first_result_kinds<>1
           OR first_request_id_occurrences<>1)) AS feed_result_unresolved,
        CASE WHEN first_request_id IS NOT NULL AND first_request_id<>''
          AND first_result_kinds=1 AND first_request_id_occurrences=1 THEN
          EXISTS(SELECT 1 FROM onboarding_events e WHERE e.user_id=u.user_id
            AND e.event_name='first_feed_failure' AND e.request_id=u.first_request_id
            AND e.event_time>=u.first_requested_at
            AND e.event_time<datetime(u.signup_at,'+24 hours') AND e.ingested_at<=:as_of)
          ELSE NULL END AS feed_failed,
        EXISTS(SELECT 1 FROM onboarding_events e WHERE e.user_id=u.user_id
          AND e.event_name='negative_feedback' AND e.event_time>=u.signup_at
          AND e.event_time<datetime(u.signup_at,'+24 hours') AND e.ingested_at<=:as_of) AS negative_feedback
      FROM feed u
    ) SELECT period,device,app_version,COUNT(*) AS users,SUM(d7) AS successes,
      SUM(onboarded) AS onboarded,SUM(feed_success) AS feed_success,SUM(activated) AS activated,
      SUM(feed_requested) AS feed_requested,
      CASE WHEN SUM(feed_result_unresolved)=0 THEN COALESCE(SUM(feed_failed),0) ELSE NULL END AS feed_failed,
      SUM(feed_result_unresolved) AS feed_result_unresolved,SUM(negative_feedback) AS negative_feedback
      FROM cohort GROUP BY period,device,app_version ORDER BY period,device,app_version
```
参数：{"start": "2026-08-24", "end": "2026-08-30", "compare_start": "2026-08-17", "compare_end": "2026-08-23", "as_of": "2026-09-19 08:00:00", "activation_seconds": 60}
### onboarding-daily-active · 日活跃背景：全注册样本中每天的合格事件去重用户，不跨日相加

来源：固定种子 710919 的匿名合成产品事件；用于复现增长分析方法，不代表真实企业经营收益；口径版本：onboarding.v2.0.0

```sql
SELECT e.event_date,
      COUNT(DISTINCT e.user_id) AS active_users FROM onboarding_events e
      JOIN onboarding_users u ON u.user_id=e.user_id
      WHERE e.event_name IN (:active_event_0,:active_event_1) AND e.ingested_at<=:as_of
        AND (e.event_date BETWEEN :start AND :end OR e.event_date BETWEEN :compare_start AND :compare_end)
         GROUP BY e.event_date ORDER BY e.event_date
```
参数：{"start": "2026-08-24", "end": "2026-08-30", "compare_start": "2026-08-17", "compare_end": "2026-08-23", "as_of": "2026-09-19 08:00:00", "activation_seconds": 60, "active_event_0": "app_active", "active_event_1": "content_consumed"}
### onboarding-change-log · 分析时段附近的可见发布与获客变更

来源：固定种子 710919 的匿名合成产品事件；用于复现增长分析方法，不代表真实企业经营收益；口径版本：onboarding.v2.0.0

```sql
SELECT change_id,change_at,device,app_version,change_type,description FROM onboarding_changes WHERE change_at>=datetime(:compare_start,'-1 day') AND change_at<datetime(:end,'+2 days') AND change_at<=:as_of ORDER BY change_at,change_id
```
参数：{"start": "2026-08-24", "end": "2026-08-30", "compare_start": "2026-08-17", "compare_end": "2026-08-23", "as_of": "2026-09-19 08:00:00", "activation_seconds": 60}

## 边界与限制

- 固定种子 710919 的匿名合成产品事件；用于复现增长分析方法，不代表真实企业经营收益
- 渠道、端、版本与漏斗的拆解是描述性证据；版本同期变化不能直接证明因果。
- 使用稳定匿名 UID；未实现企业跨设备身份合并。
- 精确 D1、精确 D7 和次 1—7 日回访使用不同指标 ID；未成熟或不完整的旁路指标显示不可用。
- 24h 漏斗保持同一 cohort 与事件顺序，D1/D7 是并列后续结果；跨日活跃人数不能直接相加为去重用户。
- 分层缺失时沿用该分层可观察期的比率作为分解约定，该部分只记入结构项，不估计缺失期表现。
- 当前是描述性问题定位，尚未执行真实修复实验，不报告业务增量或收益。

## 执行记录

- static_snapshot：本案例由 Python 分析引擎实际执行并保存；静态页面不执行自由输入问题。
- query_metric：注册 cohort 范围、人数与最晚注册时间
- query_metric：当前筛选实际涉及的设备分区
- query_metric：源端批次清单与快照可见事件，计算连续设备水位
- query_metric：窗口内事件版本、时间/日期、用户归属与批次一致性
- query_metric：窗口内事件版本、时间/日期、用户归属与批次一致性
- query_metric：两期 cohort 指标；未成熟或缺数的旁路指标保持 NULL
- query_metric：渠道 × 端的两期联合分层
- query_metric：按注册 cohort 日计算的主指标趋势
- query_metric：端 × 版本的留存、漏斗和首次请求失败
- query_metric：日活跃背景：全注册样本中每天的合格事件去重用户，不跨日相加
- query_metric：分析时段附近的可见发布与获客变更
- decompose_change：结构项 + 表现项 = -5.95013842 pp，总体变化 -5.95013842 pp；闭合误差 0.0000000000 pp。

## 版本与来源

```json
{
  "application_version": "0.2.0",
  "data_kind": "synthetic",
  "metric_version": "onboarding.v2.0.0",
  "snapshot_sha256": "d5c20f7afe9d6c92d05b3890be8777c2cde5238c09cd9805f4029c294135d974",
  "fingerprint_scope": "request, metric_contract, kpis, status",
  "execution": "Python business tools; no model call"
}
```
