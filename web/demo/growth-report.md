# 增长留存诊断

运行编号：4324e8813a77a2f37f9b127cbda5510f · 模式：静态案例 · 时间：2026-09-19T11:09:20.004583+00:00

本次读取已保存结果，未执行新查询或模型调用。

**数据说明：合成演示数据，不代表任何企业真实经营结果。**

2026-08-24 至 2026-08-30 的次 7 日内留存为 26.85%（294/1095），对比 2026-08-17 至 2026-08-23 的 36.03%，变化 -9.18 个百分点。对称分解中结构贡献 -6.05、组内表现贡献 -3.13 个百分点。

## 指标口径

```json
{
  "id": "retained_within_next_7_days",
  "name": "次 7 日内留存率",
  "version": "growth.v1.0",
  "numerator": "注册后第 1—7 个自然日内，至少有一次活动的成熟队列用户数",
  "denominator": "注册日期 + 7 日不晚于数据快照日的去重注册用户数",
  "grain": "用户",
  "window": "(注册日, 注册日 + 7 日]",
  "unit": "%",
  "timezone": "Asia/Shanghai；数据以本地自然日存储",
  "snapshot_date": "2026-09-06",
  "latest_mature_cohort": "2026-08-30",
  "exclusions": [
    "注册当日活动",
    "未完成 7 日观察的队列"
  ],
  "not_equivalent_to": "精确 D7 留存（仅注册后第 7 日活动）",
  "data_source": "固定种子 71 的合成增长数据；非真实企业经营结果",
  "current_period": [
    "2026-08-24",
    "2026-08-30"
  ],
  "previous_period": [
    "2026-08-17",
    "2026-08-23"
  ]
}
```

## 核验事实

- 2026-08-24 至 2026-08-30 的次 7 日内留存为 26.85%（294/1095），对比 2026-08-17 至 2026-08-23 的 36.03%，变化 -9.18 个百分点。对称分解中结构贡献 -6.05、组内表现贡献 -3.13 个百分点。（证据：growth-totals, growth-strata）
- 按渠道 × 设备共同分层，绝对贡献最大的分层是「自然流量 / iOS」，贡献 -5.11 个百分点；这只是总体变化的算术分解。（证据：growth-strata）

## 验证事项

- 验证事项包括投放记录、版本变更与产品路径；当前分层计数只能分解变化，不能确定原因。（证据：growth-strata, growth-dimensions）

## 后续行动

- 先核对「自然流量 / iOS」的获客来源和产品路径，再对候选改进设定随机实验、次 7 日内留存主指标及成本护栏。（证据：growth-strata）

## 结果表

### 两期成熟队列

完整结果：2行。

| period | users | retained_users | retention_pct |
| --- | --- | --- | --- |
| current | 1095 | 294 | 26.849 |
| previous | 1163 | 419 | 36.028 |
### 渠道 × 设备的对称分解（百分点）

完整结果：12行。

| segment | previous_users | current_users | previous_rate_pct | current_rate_pct | mix_pp | performance_pp | total_pp |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 自然流量 / iOS | 186 | 63 | 46.237 | 39.683 | -4.399 | -0.713 | -5.112 |
| 好友推荐 / iOS | 86 | 21 | 46.512 | 47.619 | -2.578 | 0.052 | -2.526 |
| 自然流量 / 网页 | 86 | 27 | 47.674 | 44.444 | -2.27 | -0.159 | -2.429 |
| 好友推荐 / 网页 | 35 | 6 | 54.286 | 50.0 | -1.284 | -0.076 | -1.36 |
| 自然流量 / Android | 211 | 130 | 31.754 | 41.538 | -2.298 | 1.468 | -0.829 |
| 社交投放 / iOS | 81 | 87 | 29.63 | 20.69 | 0.247 | -0.666 | -0.42 |
| 好友推荐 / Android | 84 | 54 | 34.524 | 44.444 | -0.905 | 0.603 | -0.302 |
| 社交投放 / 网页 | 37 | 27 | 27.027 | 25.926 | -0.189 | -0.031 | -0.221 |
| 社交投放 / Android | 85 | 155 | 21.176 | 16.129 | 1.277 | -0.542 | 0.735 |
| 付费搜索 / Android | 122 | 285 | 30.328 | 15.439 | 3.555 | -2.719 | 0.837 |
| 付费搜索 / 网页 | 45 | 73 | 26.667 | 30.137 | 0.795 | 0.183 | 0.977 |
| 付费搜索 / iOS | 105 | 167 | 34.286 | 29.94 | 1.998 | -0.528 | 1.471 |

### 图表数据：成熟队列的次 7 日内留存趋势

原始单位：%；空值表示未成熟/缺失/校验未通过。

| signup_date | retention_pct |
| --- | --- |
| 2026-08-17 | 37.7143 |
| 2026-08-18 | 32.7273 |
| 2026-08-19 | 36.875 |
| 2026-08-20 | 37.1795 |
| 2026-08-21 | 30.2857 |
| 2026-08-22 | 38.9937 |
| 2026-08-23 | 38.7283 |
| 2026-08-24 | 30.0654 |
| 2026-08-25 | 27.2727 |
| 2026-08-26 | 24.4898 |
| 2026-08-27 | 26.3804 |
| 2026-08-28 | 29.0123 |
| 2026-08-29 | 20.6897 |
| 2026-08-30 | 29.2398 |

### 图表数据：留存变化来源

原始单位：百分点；空值表示未成熟/缺失/校验未通过。

| component | contribution_pp |
| --- | --- |
| 结构变化 | -6.05 |
| 组内表现 | -3.128 |

### 图表数据：分渠道留存率

原始单位：%；空值表示未成熟/缺失/校验未通过。

| segment | previous_pct | current_pct |
| --- | --- | --- |
| 自然流量 | 40.165631469979296 | 41.36363636363637 |
| 付费搜索 | 31.25 | 22.095238095238095 |
| 好友推荐 | 42.926829268292686 | 45.67901234567901 |
| 社交投放 | 25.615763546798032 | 18.587360594795538 |

### 图表数据：分设备留存率

原始单位：%；空值表示未成熟/缺失/校验未通过。

| segment | previous_pct | current_pct |
| --- | --- | --- |
| Android | 30.0796812749004 | 23.557692307692307 |
| iOS | 40.61135371179039 | 30.473372781065088 |
| 网页 | 40.39408866995074 | 33.08270676691729 |

## SQL 与证据

### growth-totals · 两期成熟用户与留存人数

来源：固定种子 71 的合成增长数据；非真实企业经营结果；口径版本：growth.v1.0

```sql
WITH periods AS (SELECT 'current' AS period, :start AS start_date, :end AS end_date UNION ALL SELECT 'previous', :compare_start, :compare_end), cohort AS (
        SELECT p.period, u.user_id, u.signup_date, u.channel, u.device,
            u.experiment_arm, u.incentive_cost, u.revenue_7d,
            EXISTS(SELECT 1 FROM growth_activity a
                WHERE a.user_id = u.user_id
                  AND a.activity_date > u.signup_date
                  AND a.activity_date <= date(u.signup_date, '+7 days')) AS retained
        FROM growth_users u JOIN periods p
          ON u.signup_date BETWEEN p.start_date AND p.end_date
        WHERE date(u.signup_date, '+7 days') <= :snapshot
    ) SELECT period, COUNT(*) AS users, SUM(retained) AS retained_users FROM cohort GROUP BY period
```
参数：{"start": "2026-08-24", "end": "2026-08-30", "snapshot": "2026-09-06", "compare_start": "2026-08-17", "compare_end": "2026-08-23"}
### growth-strata · 两期渠道 × 设备成熟留存

来源：固定种子 71 的合成增长数据；非真实企业经营结果；口径版本：growth.v1.0

```sql
WITH periods AS (SELECT 'current' AS period, :start AS start_date, :end AS end_date UNION ALL SELECT 'previous', :compare_start, :compare_end), cohort AS (
        SELECT p.period, u.user_id, u.signup_date, u.channel, u.device,
            u.experiment_arm, u.incentive_cost, u.revenue_7d,
            EXISTS(SELECT 1 FROM growth_activity a
                WHERE a.user_id = u.user_id
                  AND a.activity_date > u.signup_date
                  AND a.activity_date <= date(u.signup_date, '+7 days')) AS retained
        FROM growth_users u JOIN periods p
          ON u.signup_date BETWEEN p.start_date AND p.end_date
        WHERE date(u.signup_date, '+7 days') <= :snapshot
    ) SELECT period, channel, device, COUNT(*) AS users, SUM(retained) AS retained_users FROM cohort GROUP BY period, channel, device ORDER BY period, channel, device
```
参数：{"start": "2026-08-24", "end": "2026-08-30", "snapshot": "2026-09-06", "compare_start": "2026-08-17", "compare_end": "2026-08-23"}
### growth-daily · 按注册日的成熟队列趋势

来源：固定种子 71 的合成增长数据；非真实企业经营结果；口径版本：growth.v1.0

```sql
WITH periods AS (SELECT 'current' AS period, :start AS start_date, :end AS end_date UNION ALL SELECT 'previous', :compare_start, :compare_end), cohort AS (
        SELECT p.period, u.user_id, u.signup_date, u.channel, u.device,
            u.experiment_arm, u.incentive_cost, u.revenue_7d,
            EXISTS(SELECT 1 FROM growth_activity a
                WHERE a.user_id = u.user_id
                  AND a.activity_date > u.signup_date
                  AND a.activity_date <= date(u.signup_date, '+7 days')) AS retained
        FROM growth_users u JOIN periods p
          ON u.signup_date BETWEEN p.start_date AND p.end_date
        WHERE date(u.signup_date, '+7 days') <= :snapshot
    ) SELECT period, signup_date, COUNT(*) AS users, SUM(retained) AS retained_users, ROUND(100.0 * SUM(retained) / COUNT(*), 4) AS retention_pct FROM cohort GROUP BY period, signup_date ORDER BY signup_date
```
参数：{"start": "2026-08-24", "end": "2026-08-30", "snapshot": "2026-09-06", "compare_start": "2026-08-17", "compare_end": "2026-08-23"}
### growth-dimensions · 渠道及设备单维留存对比

来源：固定种子 71 的合成增长数据；非真实企业经营结果；口径版本：growth.v1.0

```sql
WITH periods AS (SELECT 'current' AS period, :start AS start_date, :end AS end_date UNION ALL SELECT 'previous', :compare_start, :compare_end), cohort AS (
        SELECT p.period, u.user_id, u.signup_date, u.channel, u.device,
            u.experiment_arm, u.incentive_cost, u.revenue_7d,
            EXISTS(SELECT 1 FROM growth_activity a
                WHERE a.user_id = u.user_id
                  AND a.activity_date > u.signup_date
                  AND a.activity_date <= date(u.signup_date, '+7 days')) AS retained
        FROM growth_users u JOIN periods p
          ON u.signup_date BETWEEN p.start_date AND p.end_date
        WHERE date(u.signup_date, '+7 days') <= :snapshot
    ) SELECT period, 'channel' AS dimension, channel AS segment, COUNT(*) AS users, SUM(retained) AS retained_users FROM cohort GROUP BY period, channel UNION ALL SELECT period, 'device', device, COUNT(*), SUM(retained) FROM cohort GROUP BY period, device
```
参数：{"start": "2026-08-24", "end": "2026-08-30", "snapshot": "2026-09-06", "compare_start": "2026-08-17", "compare_end": "2026-08-23"}

## 边界与限制

- 固定种子 71 的合成增长数据；非真实企业经营结果
- 分层分解是描述性归因，不能证明渠道或设备变化导致留存变化。
- 渠道和设备分层表存在交叉，不能相加；总变化仅由渠道 × 设备联合分层计算。

## 执行记录

- static_snapshot：静态案例：读取已保存的 Python / SQL 计算结果，未调用模型。
- query_metric：两期成熟用户与留存人数
- query_metric：两期渠道 × 设备成熟留存
- query_metric：按注册日的成熟队列趋势
- query_metric：渠道及设备单维留存对比
- decompose_change：结构 + 表现 = -9.178200 pp；与总体变化的误差 0.000000000 pp。

## 版本与来源

```json
{
  "application_version": "0.2.1",
  "data_kind": "synthetic",
  "metric_version": "growth.v1.0",
  "snapshot_sha256": "4324e8813a77a2f37f9b127cbda5510f41821b3114a782fde8028771544c9b0d",
  "fingerprint_scope": "request, metric_contract, kpis, status",
  "execution": "Python business tools; no model call"
}
```
