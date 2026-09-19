"""Point-in-time retail operations over reproducible synthetic positive orders.

Metric definitions and segment boundaries adapted from Liu Xi's existing
liu-xi-evidence-analytics (analytics.py / operations.py). No original orders,
private customer data, or measured marketing results are copied.
"""
from __future__ import annotations

import hashlib
import math
import random
import sqlite3
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

VERSION = "repurchase-1.0.0"
SOURCE = "固定种子合成订单；非真实客户、非实际营销结果"
DATA_START = "2026-01-01"
DATA_END = "2026-06-30"
REGIONS = ("华东", "华南", "华北", "西部")
SEGMENTS = {
    "first": "近期单次购买",
    "active": "活跃复购",
    "cooling": "31—60日未购",
    "dormant": "60日以上未购",
    "single": "单次购买沉默",
}
DEFAULT = {"question": "截至5月31日，按历史购买分群，在200元预算内制定召回候选与随机留出方案。", "domain": "repurchase", "task": "segment", "start": "2026-03-01", "end": "2026-05-31", "filters": {"budget": 200, "contact_cost": 2, "holdout_ratio": 0.2}}
METRICS = [
    {"id": "customers", "label": "首次观察购买客户数", "unit": "count", "rule": "全量明细中首次观察购买日在所选窗口内的去重客户数，不等于真实获客。"},
    {"id": "repeat7", "label": "次7日内复购率", "unit": "ratio", "rule": "首个观察购买日后D1—D7至少一笔正向订单的客户 / 完整观察D7的客户；当日再购排除。"},
    {"id": "repeat30", "label": "次30日内复购率", "unit": "ratio", "rule": "首个观察购买日后D1—D30至少一笔正向订单的客户 / 完整观察D30的客户。"},
    {"id": "value30", "label": "首购起30日人均正向交易额", "unit": "CNY", "rule": "完整观察D30客户从首个观察购买日D0至D29的正向订单金额 / 完整观察D30客户数；未扣退款、成本，不是净LTV或利润。"},
    {"id": "rfm", "label": "时点RFM分群", "unit": "customers", "rule": "R为截止日距最近正向购买天数，F为截止日及之前全部观察订单数，M为所选start/end窗口正向交易额；不使用未来订单排序。"},
]


def metadata() -> dict:
    return {"id": "repurchase", "name": "复购运营 Agent", "description": "从正向订单计算成熟队列复购、时点RFM分群、预算内匿名候选和可复现随机留出计划。", "data_source": SOURCE, "data_range": {"start": DATA_START, "end": DATA_END}, "default_request": {**DEFAULT, "filters": dict(DEFAULT["filters"])}, "metrics": METRICS, "tables": [
        {"name": "repurchase_customers", "description": "固定种子合成匿名客户", "columns": [{"name": "customer_id", "type": "TEXT", "description": "合成匿名客户ID"}, {"name": "region", "type": "TEXT", "description": "合成地区"}]},
        {"name": "repurchase_orders", "description": "仅含正向交易；不存在真实退款、成本和营销触达记录", "columns": [{"name": "order_id", "type": "TEXT"}, {"name": "customer_id", "type": "TEXT"}, {"name": "order_date", "type": "TEXT"}, {"name": "amount_cents", "type": "INTEGER", "description": "合成CNY分"}]},
    ], "filters": {"region": ["all", *REGIONS], "segment": ["all", *SEGMENTS], "budget": "0—1000000元，默认200", "contact_cost": "每位处理组客户的最大计划成本，默认2元", "holdout_ratio": "0.1—0.5，默认0.2", "seed": "分组种子，默认liuxi-2026", "limit": "候选人数上限，默认100，最多200"}, "examples": [
        {"question": DEFAULT["question"], "task": "segment"},
        {"question": "分析3月至5月首次观察购买队列的次7日和次30日复购，按地区拆分。", "task": "diagnose"},
        {"question": "生成复购运营报告，说明成熟窗口、候选预算和留出计划。", "task": "report"},
    ]}


def build_database(path: Path) -> None:
    """Idempotently create our namespaced tables; leave other domains untouched."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS repurchase_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        existing = conn.execute("SELECT value FROM repurchase_metadata WHERE key='version'").fetchone()
        if existing and existing[0] == VERSION:
            return
        conn.executescript("""
            DROP TABLE IF EXISTS repurchase_orders;
            DROP TABLE IF EXISTS repurchase_customers;
            CREATE TABLE repurchase_customers (customer_id TEXT PRIMARY KEY, region TEXT NOT NULL);
            CREATE TABLE repurchase_orders (order_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES repurchase_customers(customer_id), order_date TEXT NOT NULL, amount_cents INTEGER NOT NULL CHECK(amount_cents>0));
            CREATE INDEX repurchase_order_customer_date ON repurchase_orders(customer_id,order_date);
            CREATE INDEX repurchase_order_date ON repurchase_orders(order_date);
        """)
        rng = random.Random(7102026)
        beginning, ending = date.fromisoformat(DATA_START), date.fromisoformat(DATA_END)
        customers, orders = [], []
        for index in range(1200):
            customer = "SYN-" + hashlib.sha256(f"liuxi-retail:{index}".encode()).hexdigest()[:10]
            region = rng.choices(REGIONS, weights=(4, 3, 2, 1))[0]
            first = beginning + timedelta(days=rng.randrange(181))
            propensity = rng.choices((0.0, 0.008, 0.026, 0.065), weights=(4, 2, 3, 1))[0]
            baseline = rng.randint(1800, 24000)
            customers.append((customer, region))
            def add_order(day: date) -> None:
                amount = max(100, round(baseline * rng.uniform(0.5, 1.8)))
                orders.append((f"SYN-O{len(orders)+1:06d}", customer, day.isoformat(), amount))
            add_order(first)
            if rng.random() < 0.09:
                add_order(first)  # same-day second orders are deliberately present
            for offset in range(1, (ending - first).days + 1):
                day = first + timedelta(days=offset)
                seasonal_factor = 0.68 if region == "华南" and day.month >= 5 else 1.0
                if rng.random() < propensity * seasonal_factor:
                    add_order(day)
        conn.executemany("INSERT INTO repurchase_customers VALUES (?,?)", customers)
        conn.executemany("INSERT INTO repurchase_orders VALUES (?,?,?,?)", orders)
        conn.executemany("INSERT OR REPLACE INTO repurchase_metadata VALUES (?,?)", [("version", VERSION), ("observed_start", DATA_START), ("observed_end", DATA_END), ("source", SOURCE), ("seed", "7102026")])


COHORT_CTE = """WITH firsts AS (
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
"""
COHORT_FIELDS = """COUNT(*) AS customers, COALESCE(SUM(mature7),0) AS mature7,
 COALESCE(SUM(mature7*returned7),0) AS repeat7, COALESCE(SUM(mature30),0) AS mature30,
 COALESCE(SUM(mature30*returned30),0) AS repeat30, COALESCE(SUM(mature30*value30_cents),0) AS value30_cents"""
COHORT_SQL = COHORT_CTE + "SELECT " + COHORT_FIELDS + " FROM cohort"
REGION_SQL = COHORT_CTE + "SELECT region," + COHORT_FIELDS + " FROM cohort GROUP BY region ORDER BY region"
WEEKLY_SQL = COHORT_CTE + "SELECT strftime('%Y-%W',first_date) AS week," + COHORT_FIELDS + " FROM cohort GROUP BY week ORDER BY week"

RFM_CTE = """WITH history AS (
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
"""
SEGMENT_SQL = RFM_CTE + """SELECT segment,COUNT(*) AS customers,ROUND(AVG(recency),2) AS avg_recency,
 ROUND(AVG(frequency),2) AS avg_frequency,SUM(window_value_cents) AS window_value_cents,
 SUM(history_value_cents) AS history_value_cents FROM rfm
 WHERE (:segment='all' OR segment=:segment) GROUP BY segment ORDER BY customers DESC,segment"""
CANDIDATE_SQL = RFM_CTE + """SELECT customer_id,region,recency,frequency,window_value_cents,history_value_cents,segment
 FROM rfm WHERE ((:segment='all' AND segment IN ('cooling','dormant')) OR segment=:segment)
 ORDER BY window_value_cents DESC,history_value_cents DESC,recency ASC,customer_id LIMIT :limit"""


def _base() -> dict:
    return {"status": "completed", "title": "复购运营分析", "summary": "", "metric_contract": {"version": VERSION, "data_source": SOURCE, "observation_end": DATA_END, "metrics": METRICS}, "kpis": [], "tables": [], "charts": [], "findings": [], "evidence": [], "trace": [], "limitations": ["数据为固定种子合成交易，不代表真实公司经营结果。", "首次观察购买不等于真实首购或广告获客；正向交易额未扣退款、成本，不属于净LTV、利润或ROI。", "分群是描述性规则，不识别复购原因；候选没有联系方式和营销同意信息。", "随机留出属于实验分配计划；未执行触达、未观测营销增量。"], "suggestions": []}


def _clarify(result: dict, message: str, options: list[str] | None = None) -> dict:
    result.update(status="needs_clarification", summary=message, clarification={"question": message, "options": options or []})
    result["trace"].append({"tool": "validate_repurchase_request", "status": "needs_clarification", "description": message})
    return result


def _date(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field}应使用YYYY-MM-DD日期。")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field}应使用YYYY-MM-DD日期。") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{field}应使用YYYY-MM-DD日期。")
    if not DATA_START <= value <= DATA_END:
        raise ValueError(f"{field}超出合成数据范围{DATA_START}至{DATA_END}。")
    return value


def _money(value: Any, label: str, allow_zero: bool) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label}应为有效金额。")
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0 or (not allow_zero and amount <= 0) or amount > 1000000:
            raise ValueError(f"{label}应{'大于等于0' if allow_zero else '大于0'}且不超过1000000元。")
        cents = int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        if not allow_zero and cents == 0:
            raise ValueError(f"{label}至少为0.01元。")
        return cents
    except (InvalidOperation, TypeError) as exc:
        raise ValueError(f"{label}应为有效金额。") from exc


def _enrich(row: dict) -> dict:
    return {**row, "rate7": row["repeat7"] / row["mature7"] if row["mature7"] else None,
            "rate30": row["repeat30"] / row["mature30"] if row["mature30"] else None,
            "avg_value30": round(row["value30_cents"] / row["mature30"] / 100, 2) if row["mature30"] else None}


def analyze(request: dict, db_path: Path) -> dict:
    result = _base()
    task = request.get("task") or "segment"
    if task not in ("segment", "diagnose", "report"):
        return _clarify(result, "复购场景支持分群、复购诊断与报告；目前没有真实随机触达结果，无法估计营销增量。", ["制定随机留出计划", "诊断成熟队列复购", "生成复购运营报告"])
    try:
        start = _date(DEFAULT["start"] if request.get("start") is None else request["start"], "开始日期")
        end = _date(DEFAULT["end"] if request.get("end") is None else request["end"], "结束日期")
        if start > end:
            raise ValueError("结束日期不能早于开始日期。")
        compare_start, compare_end = request.get("compare_start"), request.get("compare_end")
        if (compare_start is not None) != (compare_end is not None):
            raise ValueError("对照窗口须同时提供compare_start和compare_end。")
        if compare_start is not None:
            compare_start, compare_end = _date(compare_start, "对照开始日期"), _date(compare_end, "对照结束日期")
            if compare_start > compare_end:
                raise ValueError("对照结束日期不能早于对照开始日期。")
            if task == "segment":
                raise ValueError("分群任务按单一截止日生成候选；需要比较队列时请选择diagnose或report。")
        filters = {} if request.get("filters") is None else request["filters"]
        if not isinstance(filters, dict):
            raise ValueError("filters应为对象。")
        allowed = {"region", "segment", "budget", "contact_cost", "holdout_ratio", "seed", "limit"}
        unknown = set(filters) - allowed
        if unknown:
            raise ValueError("不支持的筛选字段：" + "、".join(sorted(unknown)))
        region, segment = filters.get("region", "all"), filters.get("segment", "all")
        if region not in ("all", *REGIONS):
            raise ValueError("请选择已登记地区：all、" + "、".join(REGIONS))
        if segment not in ("all", *SEGMENTS):
            raise ValueError("分群应为all、first、active、cooling、dormant或single。")
        if task == "diagnose" and any(k in filters for k in ("segment", "budget", "contact_cost", "holdout_ratio", "seed", "limit")):
            raise ValueError("队列诊断只支持region筛选；候选、预算和分群条件请使用segment或report任务。")
        budget = _money(filters.get("budget", 200), "预算", True)
        cost = _money(filters.get("contact_cost", 2), "每人计划成本", False)
        if isinstance(filters.get("holdout_ratio", 0.2), bool):
            raise ValueError("留出比例应为0.1—0.5之间的数值。")
        try:
            holdout_ratio = float(filters.get("holdout_ratio", 0.2))
        except (ValueError, TypeError) as exc:
            raise ValueError("留出比例应为0.1—0.5之间的数值。") from exc
        if not math.isfinite(holdout_ratio) or not 0.1 <= holdout_ratio <= 0.5:
            raise ValueError("留出比例应为0.1—0.5之间的数值。")
        limit = filters.get("limit", 100)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
            raise ValueError("候选人数上限limit应为1—200的整数。")
        seed = filters.get("seed", "liuxi-2026")
        if isinstance(seed, bool) or not isinstance(seed, (int, str)) or not 1 <= len(str(seed)) <= 100:
            raise ValueError("分组种子应为1—100字符的字符串或整数。")
    except ValueError as exc:
        return _clarify(result, str(exc))
    result["metric_contract"].update(window={"start": start, "end": end}, candidate_cutoff=end, monetary_window={"start": start, "end": end}, frequency_window={"start": DATA_START, "end": end})
    if compare_start:
        result["metric_contract"]["comparison_window"] = {"start": compare_start, "end": compare_end}
    result["trace"].append({"tool": "validate_repurchase_request", "status": "completed", "description": "日期、任务、地区、预算和留出比例校验通过。"})
    path = Path(db_path)
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        def query(eid: str, label: str, sql: str, params: dict) -> list[dict]:
            rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
            result["evidence"].append({"id": eid, "label": label, "sql": sql, "parameters": dict(params), "rows": rows, "source": SOURCE, "metric_version": VERSION})
            result["trace"].append({"tool": "query_repurchase_sql", "status": "completed", "description": f"{label}：只读SQL返回{len(rows)}行，证据{eid}。"})
            return rows
        params = {"start": start, "end": end, "observed_end": DATA_END, "region": region}
        current = _enrich(query("rp-cohort", "当前窗口成熟队列", COHORT_SQL, params)[0])
        previous = None
        if compare_start:
            previous = _enrich(query("rp-compare", "对照窗口成熟队列", COHORT_SQL, {**params, "start": compare_start, "end": compare_end})[0])
        if task in ("diagnose", "report"):
            regions = [_enrich(row) for row in query("rp-regions", "地区成熟队列", REGION_SQL, params)]
            weeks = [_enrich(row) for row in query("rp-weeks", "首个观察购买周队列", WEEKLY_SQL, params)]
            for metric, key, label, unit in (("customers", "customers", "首次观察购买客户", "count"), ("repeat7", "rate7", "次7日内复购率", "ratio"), ("repeat30", "rate30", "次30日内复购率", "ratio"), ("value30", "avg_value30", "30日人均正向交易额", "CNY")):
                kpi = {"id": metric, "label": label, "value": current[key], "unit": unit}
                if previous is not None:
                    kpi["previous"] = previous[key]
                    kpi["delta"] = current[key] - previous[key] if current[key] is not None and previous[key] is not None else None
                result["kpis"].append(kpi)
            result["tables"].append({"id": "rp-regions-table", "title": "按地区核验成熟分母", "columns": ["region", "customers", "mature7", "repeat7", "rate7", "mature30", "repeat30", "rate30", "avg_value30"], "rows": regions})
            result["charts"].extend([
                {"id": "rp-weekly", "title": "按首个观察购买周的成熟队列复购率", "type": "line", "x_key": "week", "y_keys": ["rate7", "rate30"], "data": weeks, "unit": "ratio"},
                {"id": "rp-region-chart", "title": "地区次30日内复购率", "type": "bar", "x_key": "region", "y_keys": ["rate30"], "data": regions, "unit": "ratio"},
            ])
            rate_text = lambda val: "无成熟分母" if val is None else f"{val:.2%}"
            result["findings"].append({"kind": "fact", "text": f"窗口内首次观察购买客户{current['customers']}人；成熟7日客户{current['mature7']}人，其中{current['repeat7']}人次7日内复购，复购率{rate_text(current['rate7'])}。成熟30日客户{current['mature30']}人，其中{current['repeat30']}人次30日内复购，复购率{rate_text(current['rate30'])}。", "evidence_ids": ["rp-cohort"]})
            if current["mature30"] < current["customers"]:
                result["limitations"].append(f"{current['customers']-current['mature30']}名客户尚未完整观察30日，已排除于30日复购和交易额分母。")
            if previous is not None:
                result["tables"].append({"id": "rp-periods", "title": "队列窗口对照（统一观察截至日）", "columns": ["period", "start", "end", "customers", "mature7", "rate7", "mature30", "rate30", "avg_value30"], "rows": [{"period": "本期", "start": start, "end": end, **current}, {"period": "对照", "start": compare_start, "end": compare_end, **previous}]})
                if previous["customers"] == 0:
                    result["limitations"].append("对照窗口无首次观察购买客户，无法计算有效变化；未将缺失值视为0。")
                if max(start, compare_start) <= min(end, compare_end):
                    result["limitations"].append("当前与对照窗口重叠；两者并非独立样本，不作独立样本检验或因果推断。")
        if task in ("segment", "report"):
            rparams = {"start": start, "end": end, "region": region, "segment": segment}
            segment_rows = query("rp-segments", "截至日RFM分群", SEGMENT_SQL, rparams)
            segment_rows_display = [{**row, "label": SEGMENTS[row["segment"]], "window_value": row["window_value_cents"] / 100, "history_value": row["history_value_cents"] / 100} for row in segment_rows]
            capacity = budget // cost
            sample_limit = min(limit, math.floor(capacity / (1 - holdout_ratio)) + 1) if capacity else 0
            candidates = list(query("rp-candidates", "仅用截止日前信息排序的候选", CANDIDATE_SQL, {**rparams, "limit": sample_limit}))
            while candidates and len(candidates) - math.floor(len(candidates) * holdout_ratio + 0.5) > capacity:
                candidates.pop()
            holdout_n = math.floor(len(candidates) * holdout_ratio + 0.5)
            holdout_ids = {row["customer_id"] for row in sorted(candidates, key=lambda row: hashlib.sha256(f"{seed}:{row['customer_id']}".encode()).hexdigest())[:holdout_n]}
            allocated = [{"customer_id": row["customer_id"], "region": row["region"], "segment": SEGMENTS[row["segment"]], "recency": row["recency"], "frequency": row["frequency"], "window_value": row["window_value_cents"] / 100, "assignment": "随机留出" if row["customer_id"] in holdout_ids else "计划处理", "planned_cost": 0 if row["customer_id"] in holdout_ids else cost / 100} for row in candidates]
            treatment_n = len(allocated) - holdout_n
            planned_cents = treatment_n * cost
            segment_total = sum(row["customers"] for row in segment_rows)
            result["kpis"].extend([
                {"id": "rfm_customers", "label": "截至日分群客户", "value": segment_total, "unit": "count"},
                {"id": "candidates", "label": "预算内候选（含留出）", "value": len(allocated), "unit": "count"},
                {"id": "planned_cost", "label": "计划处理成本", "value": planned_cents / 100, "unit": "CNY"},
                {"id": "holdout", "label": "随机留出人数", "value": holdout_n, "unit": "count"},
            ])
            result["tables"].extend([
                {"id": "rp-segments-table", "title": "截止日RFM分群（M为所选窗口金额）", "columns": ["label", "customers", "avg_recency", "avg_frequency", "window_value", "history_value"], "rows": segment_rows_display},
                {"id": "rp-candidates-table", "title": "匿名候选与随机分配计划（未执行触达）", "columns": ["customer_id", "region", "segment", "recency", "frequency", "window_value", "assignment", "planned_cost"], "rows": allocated},
            ])
            result["charts"].append({"id": "rp-segment-chart", "title": "截至日客户分群", "type": "bar", "x_key": "label", "y_keys": ["customers"], "data": segment_rows_display, "unit": "count"})
            result["metric_contract"]["allocation"] = {"budget": budget / 100, "contact_cost": cost / 100, "planned_cost": planned_cents / 100, "holdout_ratio_requested": holdout_ratio, "holdout_ratio_actual": holdout_n / len(allocated) if allocated else None, "seed": str(seed), "algorithm": "候选按窗口金额、历史金额、最近购买排序；SHA-256(seed:customer_id)稳定排序后前round(n*ratio)人为留出；只计划处理组计成本", "candidate_limit": limit, "treatment_n": treatment_n, "holdout_n": holdout_n}
            result["findings"].append({"kind": "fact", "text": f"截至{end}，所选分群有{segment_total}名客户；预算{budget/100:.2f}元、每位计划处理成本{cost/100:.2f}元，共安排{len(allocated)}名候选，其中计划处理{treatment_n}人、随机留出{holdout_n}人，计划成本{planned_cents/100:.2f}元。", "evidence_ids": ["rp-segments", "rp-candidates"]})
            result["findings"].append({"kind": "action", "text": "候选仅作运营讨论；先核验营销同意和触达条件，再预注册客户级随机实验、D1—D30复购主指标、退款与成本护栏及所需样本量。当前没有营销增量结果。", "evidence_ids": ["rp-candidates"]})
            result["trace"].append({"tool": "allocate_repurchase_holdout", "status": "completed", "description": f"用种子{seed}生成可复现分配，计划成本{planned_cents/100:.2f}元不超过预算{budget/100:.2f}元；不执行触达。"})
            if holdout_n < 10 or treatment_n < 10:
                result["limitations"].append("本次分配任一组不足10人，仅能演示流程；未通过实验功效计算，不能据此承诺统计有效性。")
            if not allocated:
                result["limitations"].append("当前筛选与预算下没有可安排候选。可检查预算、地区、分群或截止日。")
            if task == "segment" and not allocated:
                result["status"] = "insufficient_data"
        if current["customers"] == 0 and task == "diagnose":
            result["status"] = "insufficient_data"
        if task in ("diagnose", "report") and not current["mature7"] and not current["mature30"]:
            result["status"] = "insufficient_data"
            result["limitations"].append("当前队列没有完整观察7日或30日的客户，复购率保持空值。")
    result["title"] = {"segment": "复购分群与预算留出计划", "diagnose": "成熟队列复购诊断", "report": "复购运营报告"}[task]
    result["summary"] = f"{start}至{end}，地区：{'全部' if region=='all' else region}。候选分群仅使用{end}及之前订单；队列结果统一观察截至{DATA_END}。所有数据均为合成。" + ("当前样本或预算不足，请参阅说明。" if result["status"] == "insufficient_data" else "")
    result["suggestions"] = ["查看查询 SQL 与参数，复核成熟分母和D1—D7/D1—D30口径。", "用相同种子复现留出；改变seed只改变分配，不改变候选历史分群。", "导出报告保存数据快照、口径版本和计划，后续接入经授权的订单再验证。"]
    result["trace"].append({"tool": "validate_repurchase_output", "status": "completed", "description": "事实来自只读SQL与确定性计算；未生成无证据的营销增量或净LTV。"})
    return result
