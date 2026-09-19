# 复购分群与预算留出计划

运行编号：1ef3bb3529b008714531bdafce111554 · 模式：静态案例 · 时间：2026-09-19T11:09:20.004583+00:00

本次读取已保存结果，未执行新查询或模型调用。

**数据说明：合成演示数据，不代表任何企业真实经营结果。**

2026-03-01至2026-05-31，地区：全部。候选分群仅使用2026-05-31及之前订单；队列结果统一观察截至2026-06-30。所有数据均为合成。

## 指标口径

```json
{
  "version": "repurchase-1.0.0",
  "data_source": "固定种子合成订单；非真实客户、非实际营销结果",
  "observation_end": "2026-06-30",
  "metrics": [
    {
      "id": "customers",
      "label": "首次观察购买客户数",
      "unit": "count",
      "rule": "全量明细中首次观察购买日在所选窗口内的去重客户数，不等于真实获客。"
    },
    {
      "id": "repeat7",
      "label": "次7日内复购率",
      "unit": "ratio",
      "rule": "首个观察购买日后D1—D7至少一笔正向订单的客户 / 完整观察D7的客户；当日再购排除。"
    },
    {
      "id": "repeat30",
      "label": "次30日内复购率",
      "unit": "ratio",
      "rule": "首个观察购买日后D1—D30至少一笔正向订单的客户 / 完整观察D30的客户。"
    },
    {
      "id": "value30",
      "label": "首购起30日人均正向交易额",
      "unit": "CNY",
      "rule": "完整观察D30客户从首个观察购买日D0至D29的正向订单金额 / 完整观察D30客户数；未扣退款、成本，不是净LTV或利润。"
    },
    {
      "id": "rfm",
      "label": "时点RFM分群",
      "unit": "customers",
      "rule": "R为截止日距最近正向购买天数，F为截止日及之前全部观察订单数，M为所选start/end窗口正向交易额；不使用未来订单排序。"
    }
  ],
  "window": {
    "start": "2026-03-01",
    "end": "2026-05-31"
  },
  "candidate_cutoff": "2026-05-31",
  "monetary_window": {
    "start": "2026-03-01",
    "end": "2026-05-31"
  },
  "frequency_window": {
    "start": "2026-01-01",
    "end": "2026-05-31"
  },
  "allocation": {
    "budget": 200.0,
    "contact_cost": 2.0,
    "planned_cost": 160.0,
    "holdout_ratio_requested": 0.2,
    "holdout_ratio_actual": 0.2,
    "seed": "liuxi-2026",
    "algorithm": "候选按窗口金额、历史金额、最近购买排序；SHA-256(seed:customer_id)稳定排序后前round(n*ratio)人为留出；只计划处理组计成本",
    "candidate_limit": 100,
    "treatment_n": 80,
    "holdout_n": 20
  }
}
```

## 核验事实

- 截至2026-05-31，所选分群有1005名客户；预算200.00元、每位计划处理成本2.00元，共安排100名候选，其中计划处理80人、随机留出20人，计划成本160.00元。（证据：rp-segments, rp-candidates）

## 验证事项


## 后续行动

- 候选仅作运营讨论；先核验营销同意和触达条件，再预注册客户级随机实验、D1—D30复购主指标、退款与成本护栏及所需样本量。当前没有营销增量结果。（证据：rp-candidates）

## 结果表

### 截止日RFM分群（M为所选窗口金额）

完整结果：5行。

| label | customers | avg_recency | avg_frequency | window_value | history_value |
| --- | --- | --- | --- | --- | --- |
| 单次购买沉默 | 382 | 88.84 | 1.0 | 27747.77 | 54348.31 |
| 活跃复购 | 277 | 11.42 | 4.55 | 150241.89 | 187637.25 |
| 近期单次购买 | 168 | 14.64 | 1.0 | 25798.02 | 25798.02 |
| 31—60日未购 | 105 | 44.0 | 3.17 | 39237.41 | 53408.59 |
| 60日以上未购 | 73 | 87.36 | 2.51 | 11118.35 | 26399.57 |
### 匿名候选与随机分配计划（未执行触达）

完整结果：100行。

| customer_id | region | segment | recency | frequency | window_value | assignment | planned_cost |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SYN-fbcd152916 | 华南 | 31—60日未购 | 32 | 8 | 1450.3 | 计划处理 | 2.0 |
| SYN-b890f2dba4 | 华南 | 31—60日未购 | 39 | 8 | 1352.2 | 计划处理 | 2.0 |
| SYN-ccd42c931a | 华南 | 31—60日未购 | 31 | 7 | 1334.92 | 计划处理 | 2.0 |
| SYN-8bd0b57ed2 | 西部 | 31—60日未购 | 36 | 5 | 1181.6 | 计划处理 | 2.0 |
| SYN-f9ed36ba93 | 华南 | 31—60日未购 | 33 | 7 | 1169.26 | 计划处理 | 2.0 |
| SYN-0150f2575e | 华南 | 31—60日未购 | 42 | 5 | 925.85 | 计划处理 | 2.0 |
| SYN-29a5d91624 | 华东 | 31—60日未购 | 31 | 5 | 861.97 | 计划处理 | 2.0 |
| SYN-d69b406ca2 | 华南 | 60日以上未购 | 67 | 4 | 860.99 | 计划处理 | 2.0 |
| SYN-101ea504cb | 华东 | 31—60日未购 | 31 | 3 | 832.38 | 计划处理 | 2.0 |
| SYN-3f40f98373 | 华北 | 31—60日未购 | 34 | 3 | 796.62 | 计划处理 | 2.0 |
| SYN-75716c35bc | 华南 | 31—60日未购 | 41 | 3 | 769.4 | 计划处理 | 2.0 |
| SYN-6cbacb89a6 | 华南 | 31—60日未购 | 36 | 6 | 716.19 | 计划处理 | 2.0 |
| SYN-4ec0cf98f0 | 华南 | 31—60日未购 | 56 | 3 | 715.78 | 计划处理 | 2.0 |
| SYN-8242b97818 | 华南 | 31—60日未购 | 32 | 5 | 683.37 | 计划处理 | 2.0 |
| SYN-0e031a522b | 华南 | 31—60日未购 | 40 | 4 | 682.78 | 随机留出 | 0 |
| SYN-1be75d5cfe | 华南 | 60日以上未购 | 82 | 3 | 670.73 | 计划处理 | 2.0 |
| SYN-a339f1dc15 | 华南 | 31—60日未购 | 34 | 3 | 665.93 | 计划处理 | 2.0 |
| SYN-1faede2743 | 华东 | 31—60日未购 | 55 | 3 | 637.61 | 计划处理 | 2.0 |
| SYN-10b4fc4513 | 华北 | 31—60日未购 | 42 | 2 | 625.24 | 计划处理 | 2.0 |
| SYN-2ce66c50e4 | 华南 | 31—60日未购 | 42 | 4 | 622.77 | 计划处理 | 2.0 |
| SYN-d60c8c0607 | 华北 | 31—60日未购 | 34 | 3 | 616.47 | 计划处理 | 2.0 |
| SYN-f3a0e62ab0 | 华南 | 31—60日未购 | 42 | 2 | 601.39 | 计划处理 | 2.0 |
| SYN-7185caade5 | 西部 | 31—60日未购 | 34 | 3 | 573.07 | 计划处理 | 2.0 |
| SYN-06616f2ba7 | 华东 | 31—60日未购 | 59 | 3 | 571.08 | 计划处理 | 2.0 |
| SYN-385173ca4e | 华北 | 60日以上未购 | 62 | 2 | 560.03 | 计划处理 | 2.0 |
| SYN-7d0626c0e4 | 华南 | 60日以上未购 | 61 | 2 | 552.02 | 随机留出 | 0 |
| SYN-77e6e4bcbf | 华北 | 31—60日未购 | 32 | 9 | 545.02 | 计划处理 | 2.0 |
| SYN-b638e39e0b | 华南 | 31—60日未购 | 57 | 4 | 544.99 | 计划处理 | 2.0 |
| SYN-b8d143c9a5 | 华东 | 31—60日未购 | 42 | 2 | 539.66 | 计划处理 | 2.0 |
| SYN-ce4782c7fe | 华南 | 31—60日未购 | 42 | 2 | 526.38 | 计划处理 | 2.0 |
| SYN-b06ab88647 | 华东 | 60日以上未购 | 61 | 2 | 523.74 | 随机留出 | 0 |
| SYN-65f061160d | 西部 | 31—60日未购 | 60 | 3 | 518.97 | 计划处理 | 2.0 |
| SYN-31f3ae9511 | 华东 | 31—60日未购 | 37 | 5 | 516.55 | 计划处理 | 2.0 |
| SYN-52c3035530 | 华东 | 31—60日未购 | 37 | 4 | 516.13 | 随机留出 | 0 |
| SYN-ac7781c3b1 | 华北 | 31—60日未购 | 37 | 3 | 499.79 | 计划处理 | 2.0 |
| SYN-3d6cbfbb35 | 华东 | 31—60日未购 | 52 | 3 | 483.4 | 随机留出 | 0 |
| SYN-8c7b30bb5f | 华北 | 31—60日未购 | 35 | 5 | 476.04 | 计划处理 | 2.0 |
| SYN-c16a480e5b | 华东 | 31—60日未购 | 55 | 2 | 473.31 | 计划处理 | 2.0 |
| SYN-a08ad986fb | 华东 | 31—60日未购 | 59 | 5 | 460.32 | 计划处理 | 2.0 |
| SYN-c1c3bc46a1 | 华北 | 31—60日未购 | 53 | 8 | 455.36 | 计划处理 | 2.0 |
| SYN-833e1b3c62 | 西部 | 31—60日未购 | 46 | 2 | 452.88 | 随机留出 | 0 |
| SYN-8b78a6ad19 | 西部 | 31—60日未购 | 52 | 2 | 446.18 | 计划处理 | 2.0 |
| SYN-a77283a6b0 | 华东 | 31—60日未购 | 37 | 3 | 433.28 | 计划处理 | 2.0 |
| SYN-bf9a08ac14 | 华北 | 31—60日未购 | 39 | 2 | 420.54 | 随机留出 | 0 |
| SYN-230ef9264f | 华东 | 60日以上未购 | 63 | 2 | 418.66 | 计划处理 | 2.0 |
| SYN-9911816cac | 华东 | 31—60日未购 | 38 | 2 | 399.95 | 计划处理 | 2.0 |
| SYN-18a5dc2679 | 华东 | 60日以上未购 | 70 | 3 | 391.47 | 计划处理 | 2.0 |
| SYN-3e48a8f94c | 华北 | 60日以上未购 | 61 | 3 | 391.31 | 计划处理 | 2.0 |
| SYN-c22f6e2576 | 华东 | 60日以上未购 | 76 | 4 | 385.88 | 计划处理 | 2.0 |
| SYN-d5e1dd58dc | 华东 | 60日以上未购 | 67 | 2 | 384.86 | 计划处理 | 2.0 |
| SYN-71dcd96637 | 华北 | 31—60日未购 | 52 | 2 | 379.82 | 计划处理 | 2.0 |
| SYN-27099cf31b | 华北 | 31—60日未购 | 44 | 3 | 373.67 | 计划处理 | 2.0 |
| SYN-5a3664b294 | 西部 | 60日以上未购 | 81 | 2 | 367.71 | 计划处理 | 2.0 |
| SYN-ef1ec8dc74 | 华南 | 31—60日未购 | 50 | 3 | 364.53 | 随机留出 | 0 |
| SYN-c032a63a49 | 华南 | 60日以上未购 | 70 | 3 | 364.52 | 随机留出 | 0 |
| SYN-ee7ab6aa08 | 华东 | 31—60日未购 | 51 | 5 | 356.79 | 计划处理 | 2.0 |
| SYN-b02e8f9606 | 华东 | 31—60日未购 | 31 | 3 | 351.08 | 随机留出 | 0 |
| SYN-8e94b20fb6 | 华南 | 31—60日未购 | 60 | 2 | 348.53 | 计划处理 | 2.0 |
| SYN-b817625929 | 华南 | 60日以上未购 | 79 | 2 | 338.9 | 计划处理 | 2.0 |
| SYN-c3c649793a | 华南 | 31—60日未购 | 47 | 2 | 327.71 | 随机留出 | 0 |
| SYN-0a9c92483a | 华东 | 60日以上未购 | 62 | 3 | 327.22 | 计划处理 | 2.0 |
| SYN-27172dea07 | 华东 | 60日以上未购 | 77 | 3 | 324.3 | 随机留出 | 0 |
| SYN-5a5e42fa72 | 华东 | 31—60日未购 | 32 | 2 | 324.12 | 计划处理 | 2.0 |
| SYN-5ebf7b1de2 | 华南 | 31—60日未购 | 31 | 2 | 315.76 | 随机留出 | 0 |
| SYN-22b84f7180 | 华南 | 31—60日未购 | 39 | 3 | 296.12 | 计划处理 | 2.0 |
| SYN-354a997e26 | 华东 | 60日以上未购 | 67 | 2 | 295.62 | 计划处理 | 2.0 |
| SYN-a58a99eb97 | 华东 | 31—60日未购 | 49 | 2 | 295.07 | 计划处理 | 2.0 |
| SYN-cbd772ef5b | 华东 | 31—60日未购 | 39 | 2 | 293.43 | 计划处理 | 2.0 |
| SYN-440b240ae4 | 西部 | 31—60日未购 | 57 | 2 | 291.31 | 计划处理 | 2.0 |
| SYN-c806554252 | 华南 | 60日以上未购 | 65 | 3 | 280.33 | 计划处理 | 2.0 |
| SYN-48e878a7b0 | 华北 | 31—60日未购 | 49 | 2 | 277.83 | 计划处理 | 2.0 |
| SYN-2c23edb865 | 西部 | 31—60日未购 | 40 | 2 | 277.01 | 计划处理 | 2.0 |
| SYN-386b424ec6 | 华北 | 60日以上未购 | 90 | 2 | 273.56 | 计划处理 | 2.0 |
| SYN-5214677ebc | 华南 | 60日以上未购 | 69 | 2 | 272.93 | 随机留出 | 0 |
| SYN-3985692fc0 | 华东 | 31—60日未购 | 39 | 2 | 268.2 | 计划处理 | 2.0 |
| SYN-77cf65b783 | 华南 | 31—60日未购 | 52 | 2 | 267.82 | 计划处理 | 2.0 |
| SYN-7b1eb60f61 | 华东 | 31—60日未购 | 58 | 2 | 267.55 | 计划处理 | 2.0 |
| SYN-33bcb7e354 | 华南 | 31—60日未购 | 55 | 4 | 256.13 | 计划处理 | 2.0 |
| SYN-bc8bc99584 | 华北 | 31—60日未购 | 42 | 2 | 254.13 | 计划处理 | 2.0 |
| SYN-89de956909 | 华南 | 31—60日未购 | 32 | 3 | 246.1 | 随机留出 | 0 |
| SYN-87642086ac | 华东 | 31—60日未购 | 38 | 3 | 240.53 | 计划处理 | 2.0 |
| SYN-dc98c1d6b5 | 华南 | 31—60日未购 | 55 | 5 | 234.8 | 随机留出 | 0 |
| SYN-5d01ab1699 | 华南 | 31—60日未购 | 55 | 3 | 225.78 | 随机留出 | 0 |
| SYN-2104bb6e6c | 西部 | 60日以上未购 | 78 | 5 | 225.49 | 计划处理 | 2.0 |
| SYN-53abecabd6 | 华南 | 31—60日未购 | 32 | 2 | 224.0 | 计划处理 | 2.0 |
| SYN-30d0398b1c | 华南 | 31—60日未购 | 32 | 2 | 219.11 | 随机留出 | 0 |
| SYN-570d44c9de | 华北 | 31—60日未购 | 59 | 3 | 211.42 | 计划处理 | 2.0 |
| SYN-4946d6d3fd | 华南 | 31—60日未购 | 55 | 4 | 208.2 | 计划处理 | 2.0 |
| SYN-232c9d6fee | 华北 | 60日以上未购 | 76 | 2 | 202.71 | 计划处理 | 2.0 |
| SYN-74f9909fa0 | 华南 | 31—60日未购 | 34 | 2 | 202.46 | 计划处理 | 2.0 |
| SYN-b8dba617c9 | 华南 | 60日以上未购 | 81 | 2 | 202.09 | 计划处理 | 2.0 |
| SYN-6c65a93c51 | 华北 | 31—60日未购 | 47 | 2 | 201.52 | 计划处理 | 2.0 |
| SYN-cf8465e8de | 华南 | 31—60日未购 | 41 | 4 | 200.34 | 计划处理 | 2.0 |
| SYN-bf7cdc4cb8 | 华北 | 60日以上未购 | 75 | 2 | 200.32 | 随机留出 | 0 |
| SYN-cefb1ebccd | 华北 | 31—60日未购 | 38 | 2 | 199.69 | 计划处理 | 2.0 |
| SYN-9ac668d8ca | 华北 | 31—60日未购 | 45 | 2 | 199.41 | 计划处理 | 2.0 |
| SYN-cbf07e7e50 | 华北 | 31—60日未购 | 34 | 4 | 193.18 | 计划处理 | 2.0 |
| SYN-cddfe8ad91 | 华北 | 31—60日未购 | 54 | 3 | 188.94 | 随机留出 | 0 |
| SYN-e8891298cf | 华东 | 31—60日未购 | 52 | 2 | 184.57 | 计划处理 | 2.0 |
| SYN-9875e2119a | 华东 | 31—60日未购 | 45 | 4 | 181.02 | 计划处理 | 2.0 |

### 图表数据：截至日客户分群

原始单位：count；空值表示未成熟/缺失/校验未通过。

| label | customers |
| --- | --- |
| 单次购买沉默 | 382 |
| 活跃复购 | 277 |
| 近期单次购买 | 168 |
| 31—60日未购 | 105 |
| 60日以上未购 | 73 |

## SQL 与证据

### rp-cohort · 当前窗口成熟队列

来源：固定种子合成订单；非真实客户、非实际营销结果；口径版本：repurchase-1.0.0

```sql
WITH firsts AS (
 SELECT customer_id, MIN(order_date) AS first_date FROM repurchase_orders GROUP BY customer_id
), cohort AS (
 SELECT f.customer_id,f.first_date,c.region,
  CASE WHEN date(f.first_date,'+7 days')<=:observed_end THEN 1 ELSE 0 END AS mature7,
  CASE WHEN date(f.first_date,'+30 days')<=:observed_end THEN 1 ELSE 0 END AS mature30,
  CASE WHEN EXISTS(SELECT 1 FROM repurchase_orders o WHERE o.customer_id=f.customer_id
   AND o.order_date>f.first_date AND o.order_date<=date(f.first_date,'+7 days') AND o.order_date<=:observed_end) THEN 1 ELSE 0 END AS returned7,
  CASE WHEN EXISTS(SELECT 1 FROM repurchase_orders o WHERE o.customer_id=f.customer_id
   AND o.order_date>f.first_date AND o.order_date<=date(f.first_date,'+30 days') AND o.order_date<=:observed_end) THEN 1 ELSE 0 END AS returned30,
  (SELECT COALESCE(SUM(o.amount_cents),0) FROM repurchase_orders o WHERE o.customer_id=f.customer_id
   AND o.order_date>=f.first_date AND o.order_date<=date(f.first_date,'+29 days') AND o.order_date<=:observed_end) AS value30_cents
 FROM firsts f JOIN repurchase_customers c USING(customer_id)
 WHERE f.first_date BETWEEN :start AND :end AND (:region='all' OR c.region=:region)
)
SELECT COUNT(*) AS customers, COALESCE(SUM(mature7),0) AS mature7,
 COALESCE(SUM(mature7*returned7),0) AS repeat7, COALESCE(SUM(mature30),0) AS mature30,
 COALESCE(SUM(mature30*returned30),0) AS repeat30, COALESCE(SUM(mature30*value30_cents),0) AS value30_cents FROM cohort
```
参数：{"start": "2026-03-01", "end": "2026-05-31", "observed_end": "2026-06-30", "region": "all"}
### rp-segments · 截至日RFM分群

来源：固定种子合成订单；非真实客户、非实际营销结果；口径版本：repurchase-1.0.0

```sql
WITH history AS (
 SELECT o.customer_id,c.region,MIN(o.order_date) AS first_date,MAX(o.order_date) AS last_date,
 COUNT(*) AS frequency, SUM(o.amount_cents) AS history_value_cents,
 SUM(CASE WHEN o.order_date>=:start THEN o.amount_cents ELSE 0 END) AS window_value_cents,
 CAST(julianday(:end)-julianday(MAX(o.order_date)) AS INTEGER) AS recency
 FROM repurchase_orders o JOIN repurchase_customers c USING(customer_id)
 WHERE o.order_date<=:end AND (:region='all' OR c.region=:region)
 GROUP BY o.customer_id,c.region
), rfm AS (
 SELECT *,CASE WHEN frequency=1 AND recency<=30 THEN 'first'
  WHEN frequency=1 THEN 'single' WHEN recency<=30 THEN 'active'
  WHEN recency<=60 THEN 'cooling' ELSE 'dormant' END AS segment
 FROM history
)
SELECT segment,COUNT(*) AS customers,ROUND(AVG(recency),2) AS avg_recency,
 ROUND(AVG(frequency),2) AS avg_frequency,SUM(window_value_cents) AS window_value_cents,
 SUM(history_value_cents) AS history_value_cents FROM rfm
 WHERE (:segment='all' OR segment=:segment) GROUP BY segment ORDER BY customers DESC,segment
```
参数：{"start": "2026-03-01", "end": "2026-05-31", "region": "all", "segment": "all"}
### rp-candidates · 仅用截止日前信息排序的候选

来源：固定种子合成订单；非真实客户、非实际营销结果；口径版本：repurchase-1.0.0

```sql
WITH history AS (
 SELECT o.customer_id,c.region,MIN(o.order_date) AS first_date,MAX(o.order_date) AS last_date,
 COUNT(*) AS frequency, SUM(o.amount_cents) AS history_value_cents,
 SUM(CASE WHEN o.order_date>=:start THEN o.amount_cents ELSE 0 END) AS window_value_cents,
 CAST(julianday(:end)-julianday(MAX(o.order_date)) AS INTEGER) AS recency
 FROM repurchase_orders o JOIN repurchase_customers c USING(customer_id)
 WHERE o.order_date<=:end AND (:region='all' OR c.region=:region)
 GROUP BY o.customer_id,c.region
), rfm AS (
 SELECT *,CASE WHEN frequency=1 AND recency<=30 THEN 'first'
  WHEN frequency=1 THEN 'single' WHEN recency<=30 THEN 'active'
  WHEN recency<=60 THEN 'cooling' ELSE 'dormant' END AS segment
 FROM history
)
SELECT customer_id,region,recency,frequency,window_value_cents,history_value_cents,segment
 FROM rfm WHERE ((:segment='all' AND segment IN ('cooling','dormant')) OR segment=:segment)
 ORDER BY window_value_cents DESC,history_value_cents DESC,recency ASC,customer_id LIMIT :limit
```
参数：{"start": "2026-03-01", "end": "2026-05-31", "region": "all", "segment": "all", "limit": 100}

## 边界与限制

- 数据为固定种子合成交易，不代表真实公司经营结果。
- 首次观察购买不等于真实首购或广告获客；正向交易额未扣退款、成本，不属于净LTV、利润或ROI。
- 分群是描述性规则，不识别复购原因；候选没有联系方式和营销同意信息。
- 随机留出属于实验分配计划；未执行触达、未观测营销增量。

## 执行记录

- static_snapshot：静态案例：读取已保存的 Python / SQL 计算结果，未调用模型。
- validate_repurchase_request：日期、任务、地区、预算和留出比例校验通过。
- query_repurchase_sql：当前窗口成熟队列：只读SQL返回1行，证据rp-cohort。
- query_repurchase_sql：截至日RFM分群：只读SQL返回5行，证据rp-segments。
- query_repurchase_sql：仅用截止日前信息排序的候选：只读SQL返回100行，证据rp-candidates。
- allocate_repurchase_holdout：用种子liuxi-2026生成可复现分配，计划成本160.00元不超过预算200.00元；不执行触达。
- validate_repurchase_output：事实来自只读SQL与确定性计算；未生成无证据的营销增量或净LTV。

## 版本与来源

```json
{
  "application_version": "0.2.1",
  "data_kind": "synthetic",
  "metric_version": "repurchase-1.0.0",
  "snapshot_sha256": "1ef3bb3529b008714531bdafce1115542139665ed39404f67b1d3959c64e2a61",
  "fingerprint_scope": "request, metric_contract, kpis, status",
  "execution": "Python business tools; no model call"
}
```
