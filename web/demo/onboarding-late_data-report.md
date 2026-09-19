# 新用户留存诊断

运行编号：8bee9a91b87130945b9f3cd30c7f8b34 · 模式：demo · 时间：2026-09-19T09:24:37.144573+00:00

**数据说明：合成演示数据，不代表任何企业真实经营结果。**

相关事件分区不完整或口径校验失败，暂停受影响业务结论，先完成回填与重算。

## 决策备忘录

```json
{
  "status": "repair_data",
  "label": "先修复数据，暂停经营判断",
  "actions": [
    "核对相关源端批次清单与导入日志。",
    "保持原 cohort 和指标口径，回填后重新执行同一查询。"
  ],
  "review_trigger": "2026-09-07 00:00:00"
}
```

## 数据质量

```json
{
  "status": "blocked",
  "as_of": "2026-09-07 08:00:00",
  "watermark": "2026-09-04 00:00:00",
  "watermarks_by_device": {
    "android": "2026-09-04 00:00:00",
    "ios": "2026-09-07 00:00:00",
    "web": "2026-09-07 00:00:00"
  },
  "required_until": "2026-09-07 00:00:00",
  "checks": [
    {
      "id": "observation_mature",
      "name": "完整观察窗口",
      "status": "passed",
      "observed": "2026-09-07 08:00:00",
      "expected": "2026-09-07 00:00:00",
      "detail": "快照时间必须覆盖完整自然日或实际注册时间 + 24 小时；不截掉未成熟用户后继续解释原请求。",
      "evidence_ids": [
        "onboarding-cohort-scope"
      ]
    },
    {
      "id": "continuous_watermark",
      "name": "连续数据水位",
      "status": "blocked",
      "observed": "2026-09-04 00:00:00",
      "expected": "2026-09-07 00:00:00",
      "detail": "水位为所有相关设备分区已完整到达事件时间的排他上界；缺一日不能跳过。",
      "evidence_ids": [
        "onboarding-batch-watermark"
      ]
    },
    {
      "id": "source_manifest",
      "name": "源端清单计数",
      "status": "blocked",
      "observed": 3,
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
  "affected_batches": [
    {
      "event_date": "2026-09-04",
      "device": "android",
      "expected_events": 579,
      "observed_events": 0,
      "latest_arrival": null
    },
    {
      "event_date": "2026-09-05",
      "device": "android",
      "expected_events": 601,
      "observed_events": 0,
      "latest_arrival": null
    },
    {
      "event_date": "2026-09-06",
      "device": "android",
      "expected_events": 517,
      "observed_events": 0,
      "latest_arrival": null
    }
  ],
  "affected_metrics": [
    "new_user_retention_d7",
    "return_within_days_1_7"
  ],
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
      "watermark_complete": false,
      "schema_valid": true,
      "event_integrity_valid": true,
      "unsupported_schema_events": 0,
      "invalid_event_relationships": 0,
      "evidence_ids": [
        "onboarding-event-validation",
        "onboarding-batch-watermark"
      ],
      "available": false
    },
    {
      "metric_id": "return_within_days_1_7",
      "metric": "次 1—7 日内回访率",
      "required_until": "2026-09-07 00:00:00",
      "mature": true,
      "watermark_complete": false,
      "schema_valid": true,
      "event_integrity_valid": true,
      "unsupported_schema_events": 0,
      "invalid_event_relationships": 0,
      "evidence_ids": [
        "onboarding-event-validation",
        "onboarding-batch-watermark"
      ],
      "available": false
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
  "message": "相关事件分区不完整或口径校验失败，暂停受影响业务结论，先完成回填与重算。",
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
    "status": "blocked"
  },
  {
    "step": 3,
    "tool": "query_cohort_metrics",
    "purpose": "用同一 cohort 计算精确留存和有序漏斗",
    "status": "pending"
  },
  {
    "step": 4,
    "tool": "decompose_change",
    "purpose": "区分结构变化、分层表现与版本关联",
    "status": "pending"
  },
  {
    "step": 5,
    "tool": "build_evidence_report",
    "purpose": "组织证据、竞争解释、行动和复查条件",
    "status": "pending"
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
  "data_as_of": "2026-09-07 08:00:00",
  "watermark": "2026-09-04 00:00:00"
}
```

## 核验事实

- 相关事件分区不完整或口径校验失败，暂停受影响业务结论，先完成回填与重算。（证据：onboarding-cohort-scope, onboarding-cohort-devices, onboarding-batch-watermark, onboarding-event-validation, onboarding-event-validation-new_user_retention_d1）

## 待验证假设


## 后续行动

- 没有通过门禁的留存值不显示为 0，也不支持调整获客预算或产品放量。（证据：onboarding-cohort-scope, onboarding-cohort-devices, onboarding-batch-watermark, onboarding-event-validation, onboarding-event-validation-new_user_retention_d1）

## 结果表

### 数据可用性门禁

完整结果：5行。

| name | status | observed | expected | detail |
| --- | --- | --- | --- | --- |
| 完整观察窗口 | passed | 2026-09-07 08:00:00 | 2026-09-07 00:00:00 | 快照时间必须覆盖完整自然日或实际注册时间 + 24 小时；不截掉未成熟用户后继续解释原请求。 |
| 连续数据水位 | blocked | 2026-09-04 00:00:00 | 2026-09-07 00:00:00 | 水位为所有相关设备分区已完整到达事件时间的排他上界；缺一日不能跳过。 |
| 源端清单计数 | blocked | 3 | 0 | 按已知源端批次 expected_events 比较已到达去重事件；缺少清单也无法通过连续水位。 |
| 事件版本兼容 | passed | 0 | 0 | 只接受版本化指标合同支持的埋点 schema。 |
| 事件关系与幂等性 | passed | 0 | 0 | 检查匿名用户归属、事件时间/自然日、批次日期/设备、事件先后与 event_id 唯一性。 |
### 不同指标分别判断成熟与可用性

完整结果：4行。

| metric | required_until | mature | watermark_complete | schema_valid | event_integrity_valid | available |
| --- | --- | --- | --- | --- | --- | --- |
| 精确 D1 留存率 | 2026-09-01 00:00:00 | True | True | True | True | True |
| 精确 D7 留存率 | 2026-09-07 00:00:00 | True | False | True | True | False |
| 次 1—7 日内回访率 | 2026-09-07 00:00:00 | True | False | True | True | False |
| 24 小时有序激活率 | 2026-08-31 23:55:31 | True | True | True | True | True |
### 需要回填的分区

完整结果：3行。

| event_date | device | expected_events | observed_events | latest_arrival |
| --- | --- | --- | --- | --- |
| 2026-09-04 | android | 579 | 0 | 未成熟/缺失 |
| 2026-09-05 | android | 601 | 0 | 未成熟/缺失 |
| 2026-09-06 | android | 517 | 0 | 未成熟/缺失 |

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
参数：{"start": "2026-08-24", "end": "2026-08-30", "compare_start": "2026-08-17", "compare_end": "2026-08-23", "as_of": "2026-09-07 08:00:00", "activation_seconds": 60}
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
参数：{"start": "2026-08-24", "end": "2026-08-30", "compare_start": "2026-08-17", "compare_end": "2026-08-23", "as_of": "2026-09-07 08:00:00", "activation_seconds": 60}
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
参数：{"start": "2026-08-24", "end": "2026-08-30", "compare_start": "2026-08-17", "compare_end": "2026-08-23", "as_of": "2026-09-07 08:00:00", "activation_seconds": 60, "batch_start": "2026-06-01", "batch_end": "2026-09-06", "quality_device_0": "android", "quality_device_1": "ios", "quality_device_2": "web"}
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
参数：{"start": "2026-08-24", "end": "2026-08-30", "compare_start": "2026-08-17", "compare_end": "2026-08-23", "as_of": "2026-09-07 08:00:00", "activation_seconds": 60, "batch_start": "2026-06-01", "batch_end": "2026-09-06", "quality_device_0": "android", "quality_device_1": "ios", "quality_device_2": "web", "relevant_start": "2026-08-17", "relevant_end": "2026-09-06", "schema_0": "1.0"}
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
参数：{"start": "2026-08-24", "end": "2026-08-30", "compare_start": "2026-08-17", "compare_end": "2026-08-23", "as_of": "2026-09-07 08:00:00", "activation_seconds": 60, "batch_start": "2026-06-01", "batch_end": "2026-09-06", "quality_device_0": "android", "quality_device_1": "ios", "quality_device_2": "web", "relevant_start": "2026-08-17", "relevant_end": "2026-08-31", "schema_0": "1.0"}

## 边界与限制

- 固定种子 710919 的匿名合成产品事件；用于复现增长分析方法，不代表真实企业经营收益
- 渠道、端、版本与漏斗的拆解是描述性证据；版本同期变化不能直接证明因果。
- 使用稳定匿名 UID；未实现企业跨设备身份合并。

## 执行记录

- static_snapshot：本案例由 Python 分析引擎实际执行并保存；静态页面不执行自由输入问题。
- query_metric：注册 cohort 范围、人数与最晚注册时间
- query_metric：当前筛选实际涉及的设备分区
- query_metric：源端批次清单与快照可见事件，计算连续设备水位
- query_metric：窗口内事件版本、时间/日期、用户归属与批次一致性
- query_metric：窗口内事件版本、时间/日期、用户归属与批次一致性

## 版本与来源

```json
{
  "application_version": "0.2.0",
  "data_kind": "synthetic",
  "metric_version": "onboarding.v2.0.0",
  "snapshot_sha256": "8bee9a91b87130945b9f3cd30c7f8b34eea41d26aa368134b891f0660b22ce10",
  "fingerprint_scope": "request, metric_contract, kpis, status",
  "execution": "Python business tools; no model call"
}
```
