# 新用户承接实验评审

运行编号：c0a3bcd352b1ab43f50fd546879e221f · 模式：静态案例 · 时间：2026-09-19T11:09:20.004583+00:00

本次读取已保存结果，未执行新查询或模型调用。

**数据说明：合成演示数据，不代表任何企业真实经营结果。**

处理组精确 D7 留存 28.12%，对照组 30.36%；差异 -2.23 pp，95% 区间 [-13.71, 9.15] pp。证据不足。未达到预注册 MDE 与围栏所需样本量。

## 决策备忘录

```json
{
  "code": "insufficient_evidence",
  "label": "证据不足",
  "reason": "未达到预注册 MDE 与围栏所需样本量。",
  "action": "报告区间与不确定性；不根据当前 p 值临时改指标、延长实验或宣布成功。按新实验计划补充证据。",
  "gates": {
    "source_reconciliation": true,
    "identity": true,
    "eligibility": true,
    "configuration": true,
    "collection": true,
    "events": true,
    "srm": true,
    "maturity": true,
    "planned_sample": false,
    "primary_effect": false,
    "negative_feedback": false
  },
  "executes_rollout": false
}
```

## 实验设计

```json
{
  "experiment_id": "underpowered",
  "start_date": "2026-08-17",
  "end_date": "2026-08-30",
  "snapshot_date": "2026-09-06",
  "expected_treatment_share": 0.5,
  "baseline_rate": 0.28,
  "mde": 0.025,
  "alpha": 0.05,
  "power": 0.8,
  "min_business_lift": 0.01,
  "negative_baseline": 0.04,
  "negative_margin": 0.015,
  "guardrail_alpha": 0.025,
  "config_version": "onboarding-v1",
  "expected_assignment_count": 240,
  "population": "新注册用户，注册成功后即时随机分配，按分配组 ITT",
  "design": "单一主指标、单一预注册围栏、固定窗口",
  "srm_alpha": 0.001,
  "guardrail": "负反馈率越低越好；H0: treatment−control ≥ margin；须单侧置信上界严格小于 margin",
  "guardrail_window": "[registered_at, registered_at+24h)",
  "business_rule": "主要效应区间下界达到预注册最低业务提升；不是只看点估计",
  "rollout": "进入人工灰度评审；系统不执行发布"
}
```

## 分析步骤

```json
{
  "control_required": 5196,
  "treatment_required": 5196,
  "primary_control_required": 5196,
  "primary_treatment_required": 5196,
  "guardrail_control_required": 2680,
  "guardrail_treatment_required": 2680,
  "total_required": 10392,
  "allocation_treatment_to_control": 1.0,
  "primary_method": "Cohen h 正态近似：nC=(1+1/r)×(z(1−alpha/2)+z(power))²/h²；nT=ceil(r×nC)",
  "guardrail_method": "非劣设计正态近似，假设真实差异为 0：nC=p(1−p)(1+1/r)×(z(1−alphaNI)+z(power))²/margin²",
  "planning_assumptions": "两项各自达到设计功效，不声明联合功效；主要设计检验差异为零，不保证业务区间门槛也有相同功效；样本量取较大需求，不计算事后 observed power。",
  "evidence_ids": [
    "experiment-registry"
  ]
}
```

## 指标口径

```json
{
  "id": "experiment_new_user_retention_d7",
  "name": "实验新用户精确 D7 留存率",
  "version": "experiments.v2.0",
  "numerator": "注册后第 7 个自然日发生至少一次 qualified_activity 的原始分配用户数",
  "denominator": "预注册入组窗口内所有合格的新注册随机分配用户；固定窗口全部成熟后评审",
  "grain": "用户",
  "unit": "%",
  "timezone": "Asia/Shanghai；时间戳为该时区本地时间",
  "timestamp_format": "YYYY-MM-DD HH:MM:SS；有效公历日期，秒精度，空格分隔，无时区后缀",
  "date_format": "YYYY-MM-DD；有效公历日期",
  "timestamp_policy": "非规范时间格式整份评审标记 invalid_data；接入层须显式转换时区并规范化，不静默丢弃事件",
  "window": "[注册日 + 7 日 00:00:00, 注册日 + 8 日 00:00:00)",
  "analysis_population": "ITT：按原始分配组分析，包括未暴露用户；不按事后活跃筛选",
  "maturity": "采集水位覆盖完整 D7 自然日，且注册后 24 小时负反馈窗口完整",
  "not_equivalent_to": "次 7 日内任意回访、D1 或曝光用户中的留存",
  "data_source": "固定种子 7109 的合成实验日志；用于方法验证，不代表真实企业收益",
  "snapshot_date": "2026-09-06",
  "data_as_of_exclusive": "2026-09-07 00:00:00",
  "experiment_period": [
    "2026-08-17",
    "2026-08-30"
  ]
}
```

## 核验事实

- 入组窗口 2026-08-17 至 2026-08-30，数据完整截至 2026-09-06；共 240 名分配用户，0 名尚未完成观察。（证据：experiment-registry, experiment-quality）
- 处理组精确 D7 留存 28.12%，对照组 30.36%；差异 -2.23 pp，95% 区间 [-13.71, 9.15] pp。（证据：experiment-groups, experiment-registry）
- 负反馈差异 +0.45 pp，非劣评审上界 5.41 pp，预注册容忍界值 1.50 pp。（证据：experiment-groups, experiment-registry）

## 验证事项


## 后续行动

- 证据不足：报告区间与不确定性；不根据当前 p 值临时改指标、延长实验或宣布成功。按新实验计划补充证据。（证据：experiment-registry, experiment-quality, experiment-changes, experiment-groups）

## 结果表

### ITT 人群与观测计数

完整结果：2行。

| arm | users | mature_users | exposed_users | retained_users | negative_users |
| --- | --- | --- | --- | --- | --- |
| control | 112 | 112 | 102 | 34 | 3 |
| treatment | 128 | 128 | 117 | 36 | 4 |
### 预注册样本规划

完整结果：2行。

| metric | baseline_pct | threshold_pp | alpha | power | control_required | treatment_required |
| --- | --- | --- | --- | --- | --- | --- |
| 精确 D7 提升 | 28.000000000000004 | 2.5 | 0.05 | 0.8 | 5196 | 5196 |
| 负反馈非劣围栏 | 4.0 | 1.5 | 0.025 | 0.8 | 2680 | 2680 |
### 配置变更轨迹

完整结果：0行。

| changed_at | field | old_value | new_value | material |
| --- | --- | --- | --- | --- |
### 效应、相对变化与区间

完整结果：2行。

| metric | control_rate_pct | treatment_rate_pct | lift_pp | relative_lift_pct | ci_low_pp | ci_high_pp | p_value |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 精确 D7 留存 | 30.357143 | 28.125 | -2.232143 | -7.352941 | -13.712282 | 9.149643 | 0.70428 |
| 24h 负反馈 | 2.678571 | 3.125 | 0.446429 | 16.666667 | -4.812033 | 5.405352 | 0.837539 |
### 实验评审门槛

完整结果：11行。

| label | rule | observed | passed |
| --- | --- | --- | --- |
| 来源人数对账 | 分配日志条数等于源端清单 | 240 / 240 | True |
| 随机单位唯一 | 用户不重复、不串组、分组合法 | 重复 0；串组 0；未知组 0 | True |
| 入组资格与时间 | 规范本地秒精度时间；注册成功即时分配且处于完整预注册入组窗口 | 0 | True |
| 配置稳定 | 同一冻结配置，变更时间规范，无入组或观察期内实质变更 | 版本不符 0；变更 0；时间无效 0 | True |
| 采集覆盖完整 | 所有分配用户均有完整到数清单，水位与注册快照一致 | 缺清单 0；未完整 0 | True |
| 事件与暴露合同 | 事件有分配来源、版本合法、时间为规范本地秒精度且曝光组不串组 | 孤立事件 0；无效事件 0；无效曝光 0 | True |
| 分配比例 SRM | 对照:处理=50%:50%；卡方 p≥0.001，期望人数均≥5 | 0.301699582478348 | True |
| 固定观察窗口成熟 | 全部分配用户已完整观察 D7 与 24h 围栏；入组窗口已结束 | 0 | True |
| 达到设计样本 | 对照≥5196、处理≥5196；由 MDE/功效和围栏共同规划 | 对照 112 / 处理 128 | False |
| 主要指标与业务门槛 | D7 差异双侧 95% 区间下界≥1 pp | [-13.712, 9.150] pp | False |
| 负反馈非劣围栏 | 负反馈差异单侧 97.5% 上界<1.5 pp | 上界 5.405 pp | False |

### 图表数据：分配人数与预注册期望

原始单位：人；空值表示未成熟/缺失/校验未通过。

| group | actual_users | expected_users |
| --- | --- | --- |
| 对照组 | 112 | 120.0 |
| 处理组 | 128 | 120.0 |

### 图表数据：ITT 用户结果：留存与负反馈

原始单位：%；空值表示未成熟/缺失/校验未通过。

| group | d7_retention_pct | negative_feedback_pct |
| --- | --- | --- |
| 对照组 | 30.357142857142854 | 2.6785714285714284 |
| 处理组 | 28.125 | 3.125 |

## SQL 与证据

### experiment-registry · 实验预注册参数与固定窗口

来源：固定种子 7109 的合成实验日志；用于方法验证，不代表真实企业收益；口径版本：experiments.v2.0

```sql
SELECT * FROM experiment_registry WHERE experiment_id=:experiment_id
```
参数：{"experiment_id": "underpowered"}
### experiment-quality · 分配、身份、配置、采集覆盖与成熟检查

来源：固定种子 7109 的合成实验日志；用于方法验证，不代表真实企业收益；口径版本：experiments.v2.0

```sql
WITH a AS (SELECT * FROM experiment_assignments WHERE experiment_id=:experiment_id),
uid AS (SELECT user_id,COUNT(*) AS records,COUNT(DISTINCT arm) AS arms FROM a GROUP BY user_id)
SELECT
 (SELECT COUNT(*) FROM a) AS assignment_records,
 (SELECT COUNT(*) FROM uid) AS assigned_users,
 (SELECT COUNT(*) FROM uid WHERE records>1) AS duplicate_users,
 (SELECT COUNT(*) FROM uid WHERE arms>1) AS cross_arm_users,
 (SELECT COUNT(*) FROM a WHERE arm NOT IN ('control','treatment')) AS unknown_arms,
 (SELECT COUNT(*) FROM a WHERE date(registered_at)<:start OR date(registered_at)>:end
    OR COALESCE((typeof(registered_at)='text' AND length(registered_at)=19 AND registered_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]' AND substr(registered_at,1,4) BETWEEN '0001' AND '9999' AND datetime(registered_at,'+0 seconds')=registered_at),0)=0 OR COALESCE((typeof(assigned_at)='text' AND length(assigned_at)=19 AND assigned_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]' AND substr(assigned_at,1,4) BETWEEN '0001' AND '9999' AND datetime(assigned_at,'+0 seconds')=assigned_at),0)=0
    OR assigned_at<>registered_at) AS invalid_registration_or_assignment,
 (SELECT COUNT(*) FROM a WHERE config_version<>:config_version) AS config_mismatches,
 (SELECT COUNT(*) FROM a LEFT JOIN experiment_coverage c
    ON c.experiment_id=a.experiment_id AND c.user_id=a.user_id WHERE c.user_id IS NULL) AS missing_coverage,
 (SELECT COUNT(*) FROM a JOIN experiment_coverage c ON c.experiment_id=a.experiment_id AND c.user_id=a.user_id
    WHERE c.complete<>1 OR c.observed_until<>:cutoff OR COALESCE((typeof(c.observed_until)='text' AND length(c.observed_until)=19 AND c.observed_until GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]' AND substr(c.observed_until,1,4) BETWEEN '0001' AND '9999' AND datetime(c.observed_until,'+0 seconds')=c.observed_until),0)=0) AS incomplete_coverage,
 (SELECT COUNT(*) FROM experiment_outcomes o LEFT JOIN a ON a.user_id=o.user_id
    WHERE o.experiment_id=:experiment_id AND a.user_id IS NULL) AS orphan_outcomes,
 (SELECT COUNT(*) FROM experiment_outcomes o JOIN a ON a.user_id=o.user_id
    WHERE o.experiment_id=:experiment_id AND (o.schema_version<>'events-v1'
      OR o.event_name NOT IN ('qualified_activity','negative_feedback')
      OR COALESCE((typeof(o.event_at)='text' AND length(o.event_at)=19 AND o.event_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]' AND substr(o.event_at,1,4) BETWEEN '0001' AND '9999' AND datetime(o.event_at,'+0 seconds')=o.event_at),0)=0 OR COALESCE((typeof(o.ingested_at)='text' AND length(o.ingested_at)=19 AND o.ingested_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]' AND substr(o.ingested_at,1,4) BETWEEN '0001' AND '9999' AND datetime(o.ingested_at,'+0 seconds')=o.ingested_at),0)=0
      OR o.event_at<a.registered_at OR o.ingested_at<o.event_at
      OR o.event_at>=:cutoff OR o.ingested_at>=:cutoff)) AS invalid_outcomes,
 (SELECT COUNT(*) FROM experiment_exposures e LEFT JOIN a ON a.user_id=e.user_id
    WHERE e.experiment_id=:experiment_id AND (a.user_id IS NULL OR e.arm<>a.arm
      OR COALESCE((typeof(e.exposed_at)='text' AND length(e.exposed_at)=19 AND e.exposed_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]' AND substr(e.exposed_at,1,4) BETWEEN '0001' AND '9999' AND datetime(e.exposed_at,'+0 seconds')=e.exposed_at),0)=0 OR e.exposed_at<a.assigned_at OR e.exposed_at>=:cutoff)) AS invalid_exposures,
 (SELECT COUNT(*) FROM experiment_changelog WHERE experiment_id=:experiment_id
    AND (COALESCE((typeof(changed_at)='text' AND length(changed_at)=19 AND changed_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]' AND substr(changed_at,1,4) BETWEEN '0001' AND '9999' AND datetime(changed_at,'+0 seconds')=changed_at),0)=0)) AS invalid_change_timestamps,
 (SELECT COUNT(*) FROM experiment_changelog WHERE experiment_id=:experiment_id AND material=1
    AND changed_at>=:start AND changed_at<:cutoff) AS material_changes,
 (SELECT COUNT(*) FROM a WHERE datetime(date(registered_at),'+8 days')>:cutoff
    OR datetime(registered_at,'+24 hours')>:cutoff) AS immature_users

```
参数：{"experiment_id": "underpowered", "start": "2026-08-17", "end": "2026-08-30", "cutoff": "2026-09-07 00:00:00", "config_version": "onboarding-v1"}
### experiment-changes · 实验配置变更记录

来源：固定种子 7109 的合成实验日志；用于方法验证，不代表真实企业收益；口径版本：experiments.v2.0

```sql
SELECT changed_at,field,old_value,new_value,material FROM experiment_changelog WHERE experiment_id=:experiment_id ORDER BY changed_at
```
参数：{"experiment_id": "underpowered", "start": "2026-08-17", "end": "2026-08-30", "cutoff": "2026-09-07 00:00:00", "config_version": "onboarding-v1"}
### experiment-groups · ITT 分配人数、暴露与成熟窗口结果

来源：固定种子 7109 的合成实验日志；用于方法验证，不代表真实企业收益；口径版本：experiments.v2.0

```sql
WITH users AS (
 SELECT a.user_id,a.arm,date(a.registered_at) AS cohort_date,
  CASE WHEN datetime(date(a.registered_at),'+8 days')<=:cutoff
    AND datetime(a.registered_at,'+24 hours')<=:cutoff THEN 1 ELSE 0 END AS mature,
  EXISTS(SELECT 1 FROM experiment_exposures e WHERE e.experiment_id=a.experiment_id AND e.user_id=a.user_id) AS exposed,
  EXISTS(SELECT 1 FROM experiment_outcomes o WHERE o.experiment_id=a.experiment_id AND o.user_id=a.user_id
    AND o.event_name='qualified_activity'
    AND o.event_at>=datetime(date(a.registered_at),'+7 days')
    AND o.event_at<datetime(date(a.registered_at),'+8 days') AND o.ingested_at<:cutoff) AS retained_d7,
  EXISTS(SELECT 1 FROM experiment_outcomes o WHERE o.experiment_id=a.experiment_id AND o.user_id=a.user_id
    AND o.event_name='negative_feedback' AND o.event_at>=a.registered_at
    AND o.event_at<datetime(a.registered_at,'+24 hours') AND o.ingested_at<:cutoff) AS negative_feedback
 FROM experiment_assignments a WHERE a.experiment_id=:experiment_id
)
SELECT arm,COUNT(*) AS users,SUM(mature) AS mature_users,SUM(exposed) AS exposed_users,
 SUM(CASE WHEN mature=1 THEN retained_d7 ELSE NULL END) AS retained_users,
 SUM(CASE WHEN mature=1 THEN negative_feedback ELSE NULL END) AS negative_users
FROM users GROUP BY arm ORDER BY arm
```
参数：{"experiment_id": "underpowered", "start": "2026-08-17", "end": "2026-08-30", "cutoff": "2026-09-07 00:00:00", "config_version": "onboarding-v1"}

## 边界与限制

- 固定种子 7109 的合成实验日志；用于方法验证，不代表真实企业收益
- 实验日志与增长诊断样本独立生成，不是已实施修复的成效记录。
- 随机化与采集合同成立时，ITT 估计该入组人群和观察窗口的平均因果效应；结果不能外推为长期 LTV 或全平台收益。
- SRM 通过不证明不存在所有数据问题；完整性只针对本地来源清单与合同核查。
- 固定窗口设计禁止因每日出现显著结果而提前结束；若需连续决策，应另预注册顺序检验。
- 负反馈围栏要求差异区间上界低于非劣界值；未发现显著恶化不等于已证明安全。
- 长期 Holdout 用于长期或组合效应评估；是否设置取决于预注册的评估目标。

## 执行记录

- static_snapshot：静态案例：读取已保存的 Python / SQL 计算结果，未调用模型。
- query_experiment：实验预注册参数与固定窗口
- query_experiment：分配、身份、配置、采集覆盖与成熟检查
- query_experiment：实验配置变更记录
- query_experiment：ITT 分配人数、暴露与成熟窗口结果
- evaluate_experiment：证据不足；未达到预注册 MDE 与围栏所需样本量。

## 版本与来源

```json
{
  "application_version": "0.2.1",
  "data_kind": "synthetic",
  "metric_version": "experiments.v2.0",
  "snapshot_sha256": "c0a3bcd352b1ab43f50fd546879e221f2f30627a8d62307b87fc81f79e1c5f65",
  "fingerprint_scope": "request, metric_contract, kpis, status",
  "execution": "Python business tools; no model call"
}
```
