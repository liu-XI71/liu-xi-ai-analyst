#!/usr/bin/env python3
"""Run the actual application engine against a frozen, public acceptance corpus.

Gold numbers come from raw table reads and independent event-level aggregation,
never from app.domains output. Demo routing results are not LLM accuracy.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import engine
from app.schemas import AnalysisRequest

SPEC = {
    "growth_snapshot": "2026-09-06", "growth_start": "2026-08-24", "growth_end": "2026-08-30",
    "experiment_start": "2026-08-17", "experiment_end": "2026-08-30",
    "repurchase_start": "2026-03-01", "repurchase_end": "2026-05-31", "repurchase_snapshot": "2026-06-30",
}


def _connection(domain):
    con = sqlite3.connect(engine.database(domain).resolve().as_uri() + "?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only=ON")
    return con


def _add(checks, name, actual, expected, kind="numeric", tolerance=1e-7):
    if actual is None or expected is None:
        passed = actual is expected
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        passed = isinstance(actual, (int, float)) and not isinstance(actual, bool) and math.isfinite(actual) and abs(actual - expected) <= tolerance
    else:
        passed = actual == expected
    checks.append({"name": name, "kind": kind, "passed": passed, "expected": expected, "actual": actual})


def _period(request, experiment=False):
    start = request.get("start") or SPEC["experiment_start" if experiment else "growth_start"]
    end = request.get("end") or SPEC["experiment_end" if experiment else "growth_end"]
    day0, day1 = date.fromisoformat(start), date.fromisoformat(end)
    previous_end = request.get("compare_end") or (day0 - timedelta(days=1)).isoformat()
    previous_start = request.get("compare_start") or (date.fromisoformat(previous_end) - (day1 - day0)).isoformat()
    return start, end, previous_start, previous_end


def _growth_raw(start, end, filters):
    # Independent event-level aggregation: deliberately not the domain's SQL CTE.
    with _connection("growth") as con:
        rows = con.execute("SELECT u.*, a.activity_date FROM growth_users u LEFT JOIN growth_activity a ON a.user_id=u.user_id WHERE u.signup_date>=? AND u.signup_date<=?", (start, end)).fetchall()
    users = {}
    snapshot = date.fromisoformat(SPEC["growth_snapshot"])
    for row in rows:
        if any(row[field] not in (value if isinstance(value, list) else [value]) for field, value in filters.items() if field in ("channel", "device")):
            continue
        signup = date.fromisoformat(row["signup_date"])
        if (snapshot - signup).days < 7:
            continue
        record = users.setdefault(row["user_id"], {"retained": False, "arm": row["experiment_arm"], "cost": row["incentive_cost"], "revenue": row["revenue_7d"]})
        if row["activity_date"] and 1 <= (date.fromisoformat(row["activity_date"]) - signup).days <= 7:
            record["retained"] = True
    return list(users.values())


def _growth_oracle(request, result, checks, experiment=False):
    start, end, previous_start, previous_end = _period(request, experiment)
    users = _growth_raw(start, end, request.get("filters", {}))
    kpis = {row["id"]: row for row in result.get("kpis", [])}
    if experiment:
        groups = {arm: [user for user in users if user["arm"] == arm] for arm in ("control", "treatment")}
        if not all(groups.values()):
            _add(checks, "实验必须存在两个随机组", result["status"], "insufficient_data", "behavior")
            return
        n0, n1 = len(groups["control"]), len(groups["treatment"])
        p0 = sum(user["retained"] for user in groups["control"]) / n0
        p1 = sum(user["retained"] for user in groups["treatment"]) / n1
        se = math.sqrt(p0 * (1 - p0) / n0 + p1 * (1 - p1) / n1)
        lift = (p1 - p0) * 100
        expected = (n0 + n1) / 2
        srm = math.erfc(math.sqrt(((n0 - expected) ** 2 / expected + (n1 - expected) ** 2 / expected) / 2))
        stats = result.get("experiment_statistics", {})
        for key, value in {"control_users": n0, "treatment_users": n1, "lift_pp": lift, "ci95_low_pp": max(-100, lift - 1.959963984540054 * se * 100), "ci95_high_pp": min(100, lift + 1.959963984540054 * se * 100), "srm_p_value": srm}.items():
            _add(checks, "独立事件聚合 / " + key, stats.get(key), value)
        gates = result.get("decision", {}).get("gates", {})
        if "sample_size" in gates and not gates["sample_size"]:
            _add(checks, "不足样本不能放量", result["status"], "insufficient_data", "behavior")
        return
    previous = _growth_raw(previous_start, previous_end, request.get("filters", {}))
    if not users or not previous:
        _add(checks, "无可比较成熟用户", result["status"], "insufficient_data", "behavior")
        return
    current_pct = sum(user["retained"] for user in users) / len(users) * 100
    previous_pct = sum(user["retained"] for user in previous) / len(previous) * 100
    _add(checks, "独立原始表 / 本期成熟人数", kpis.get("mature_users", {}).get("value"), len(users))
    _add(checks, "独立原始表 / 对比期成熟人数", kpis.get("mature_users", {}).get("previous"), len(previous))
    _add(checks, "独立事件聚合 / 本期次7日内留存", kpis.get("retention_pct", {}).get("value"), current_pct, tolerance=.001)
    _add(checks, "独立事件聚合 / 对比期次7日内留存", kpis.get("retention_pct", {}).get("previous"), previous_pct, tolerance=.001)
    _add(checks, "独立事件聚合 / 留存绝对变化", kpis.get("retention_pct", {}).get("delta"), current_pct - previous_pct, tolerance=.001)
    mix = kpis.get("mix_pp", {}).get("value")
    performance = kpis.get("performance_pp", {}).get("value")
    _add(checks, "可验证不变量 / 分解还原总体变化", mix + performance if mix is not None and performance is not None else None, current_pct - previous_pct, tolerance=.002)


def _retail_raw(region):
    with _connection("repurchase") as con:
        rows = con.execute("SELECT o.customer_id,o.order_date,o.amount_cents,c.region FROM repurchase_orders o JOIN repurchase_customers c ON o.customer_id=c.customer_id ORDER BY o.customer_id,o.order_date,o.order_id").fetchall()
    customers = defaultdict(list)
    for row in rows:
        if region != "all" and row["region"] != region:
            continue
        customers[row["customer_id"]].append(dict(row))
    return customers


def _cohort_gold(customers, start, end):
    snapshot = date.fromisoformat(SPEC["repurchase_snapshot"])
    cohort = [orders for orders in customers.values() if start <= orders[0]["order_date"] <= end]
    mature = {7: [], 30: []}
    rates = {}
    for days in (7, 30):
        mature[days] = [orders for orders in cohort if (snapshot - date.fromisoformat(orders[0]["order_date"])).days >= days]
        repeaters = sum(any(1 <= (date.fromisoformat(order["order_date"]) - date.fromisoformat(orders[0]["order_date"])).days <= days for order in orders) for orders in mature[days])
        rates[days] = repeaters / len(mature[days]) if mature[days] else None
    value30 = sum(order["amount_cents"] for orders in mature[30] for order in orders if 0 <= (date.fromisoformat(order["order_date"]) - date.fromisoformat(orders[0]["order_date"])).days <= 29)
    return {"customers": len(cohort), "repeat7": rates[7], "repeat30": rates[30], "value30": round(value30 / len(mature[30]) / 100, 2) if mature[30] else None}


def _repurchase_oracle(request, result, checks):
    filters = request.get("filters", {})
    start, end = request.get("start") or SPEC["repurchase_start"], request.get("end") or SPEC["repurchase_end"]
    customers = _retail_raw(filters.get("region", "all"))
    kpis = {row["id"]: row for row in result.get("kpis", [])}
    gold = _cohort_gold(customers, start, end)
    for key, value in gold.items():
        if key in kpis:
            _add(checks, "独立订单聚合 / " + key, kpis[key].get("value"), value)
    if request.get("compare_start"):
        previous = _cohort_gold(customers, request["compare_start"], request["compare_end"])
        for key, value in previous.items():
            if key in kpis:
                _add(checks, "独立订单聚合 / 对比期 " + key, kpis[key].get("previous"), value)
    if "rfm_customers" not in kpis:
        return
    history = {}
    cutoff = date.fromisoformat(end)
    for customer, orders in customers.items():
        observed = [order for order in orders if order["order_date"] <= end]
        if not observed:
            continue
        recency = (cutoff - date.fromisoformat(observed[-1]["order_date"])).days
        frequency = len(observed)
        if frequency == 1:
            segment = "first" if recency <= 30 else "single"
        else:
            segment = "active" if recency <= 30 else ("cooling" if recency <= 60 else "dormant")
        history[customer] = {"segment": segment, "recency": recency, "frequency": frequency, "value": sum(order["amount_cents"] for order in observed if order["order_date"] >= start) / 100}
    segment_filter = filters.get("segment", "all")
    population = {key: value for key, value in history.items() if segment_filter == "all" or value["segment"] == segment_filter}
    _add(checks, "独立截止日聚合 / 分群人数", kpis["rfm_customers"]["value"], len(population))
    candidates = next((table["rows"] for table in result.get("tables", []) if table["id"] == "rp-candidates-table"), [])
    valid = all(row["customer_id"] in population and (segment_filter != "all" or population[row["customer_id"]]["segment"] in ("cooling", "dormant")) for row in candidates)
    _add(checks, "候选资格 / 截止日前数据", valid, True)
    _add(checks, "候选无重复客户", len({row["customer_id"] for row in candidates}), len(candidates))
    values_valid = all(row["recency"] == population[row["customer_id"]]["recency"] and row["frequency"] == population[row["customer_id"]]["frequency"] and abs(row["window_value"] - population[row["customer_id"]]["value"]) < .0001 for row in candidates if row["customer_id"] in population)
    _add(checks, "候选R/F/M与原始截止日订单一致", values_valid, True)
    cost = sum(row["planned_cost"] for row in candidates)
    _add(checks, "处理成本总和与KPI一致", kpis.get("planned_cost", {}).get("value"), cost, tolerance=.0001)
    _add(checks, "计划成本不超过预算", cost <= float(filters.get("budget", 200)) + 1e-8, True)
    holdouts = sum(row["assignment"] == "随机留出" for row in candidates)
    _add(checks, "留出人数与KPI一致", kpis.get("holdout", {}).get("value"), holdouts)
    _add(checks, "留出人数符合请求比例的整数舍入", holdouts, math.floor(len(candidates) * float(filters.get("holdout_ratio", .2)) + .5))
    _add(checks, "留出组不计触达成本", all(row["planned_cost"] == 0 for row in candidates if row["assignment"] == "随机留出"), True)


def _invariants(result, checks):
    required = {"status", "title", "summary", "metric_contract", "kpis", "tables", "charts", "findings", "evidence", "trace", "limitations", "suggestions"}
    _add(checks, "结果合同字段完整", required <= set(result), True, "contract")
    evidence_ids = {row["id"] for row in result.get("evidence", [])}
    facts = [finding for finding in result.get("findings", []) if finding.get("kind") == "fact"]
    if facts:
        grounded = all(finding.get("evidence_ids") and set(finding["evidence_ids"]) <= evidence_ids for finding in facts)
        _add(checks, "所有事实引用存在的证据", grounded, True, "evidence")
    if result.get("status") == "needs_clarification":
        _add(checks, "澄清结果不输出数值结论", result.get("kpis"), [], "behavior")
    chart_keys_valid = all(all(chart["x_key"] in row and all(key in row for key in chart["y_keys"]) for row in chart["data"]) for chart in result.get("charts", []))
    _add(checks, "图表字段可解析", chart_keys_valid, True, "contract")
    json.dumps(result, allow_nan=False)


def _percent(passed, total):
    return round(100 * passed / total, 2) if total else None


def evaluate(cases, mode, repeat):
    from app.live_agent import execute as live_execute
    outputs = []
    for repetition in range(1, repeat + 1):
        for case in cases:
            checks = []
            began = time.perf_counter()
            error, result = None, {}
            try:
                payload = AnalysisRequest.model_validate({**case["request"], "mode": mode}).model_dump(exclude_none=True)
                if mode == "live":
                    result = live_execute(payload)
                    actual_task = next((step.get("arguments", {}).get("task") for step in result.get("trace", []) if step.get("tool") == "analyze_business"), None)
                else:
                    actual_task = payload.get("task") or engine.infer_demo_task(payload["question"], payload["domain"])
                    result = engine.analyze_domain(payload)
                duration_ms = round((time.perf_counter() - began) * 1000, 3)
                _add(checks, "业务状态", result.get("status"), case["expected_status"], "status")
                if "expected_task" in case and (mode == "demo" or case["expected_status"] == "completed"):
                    _add(checks, "任务路由", actual_task, case["expected_task"], "intent")
                _invariants(result, checks)
                if case.get("oracle") and result.get("status") in ("completed", "insufficient_data"):
                    if case["oracle"] == "repurchase":
                        _repurchase_oracle(case["request"], result, checks)
                    else:
                        _growth_oracle(case["request"], result, checks, case["oracle"] == "experiment")
                elif case.get("oracle"):
                    _add(checks, "数值基准要求产生可核查结果", False, True)
            except Exception as exc:
                # Record exceptions as failures; never turn errors into successful cases.
                error = f"{type(exc).__name__}: {exc}"
                duration_ms = round((time.perf_counter() - began) * 1000, 3)
                _add(checks, "正常返回业务结果", error, "no exception", "contract")
            row = {"id": case["id"], "repetition": repetition, "split": case["split"], "domain": case["request"]["domain"], "question": case["request"]["question"], "request": case["request"], "category": case["category"], "expected_status": case["expected_status"], "actual_status": result.get("status", "error"), "passed": bool(checks) and all(check["passed"] for check in checks), "checks": checks, "duration_ms": duration_ms, "summary": result.get("summary", ""), "error": error}
            if result.get("model_run"):
                row["model_run"] = result["model_run"]
            outputs.append(row)
            print(f"{'PASS' if row['passed'] else 'FAIL'} {case['id']} {mode} {duration_ms:.1f}ms", flush=True)
    return outputs


def summarize(rows, mode, source_hash, repeat):
    total = len(rows)
    passed = sum(row["passed"] for row in rows)
    metrics = []
    for kind, label in [("intent", "有限任务路由通过率" if mode == "demo" else "模型任务选择通过率"), ("numeric", "独立数值与不变量验证"), ("status", "业务状态验证"), ("evidence", "事实证据引用验证")]:
        applicable = [row for row in rows if any(check["kind"] == kind for check in row["checks"])]
        successes = sum(all(check["passed"] for check in row["checks"] if check["kind"] == kind) for row in applicable)
        metrics.append({"id": kind, "label": label, "value": _percent(successes, len(applicable)), "unit": "%", "passed": successes, "total": len(applicable), "description": f"{successes}/{len(applicable)} 个适用样本；以样本为单位，任一该类检查失败即失败。"})
    exceptional = [row for row in rows if row["category"] != "normal"]
    behavior_passed = sum(row["actual_status"] == row["expected_status"] for row in exceptional)
    metrics.append({"id": "exception_behavior", "label": "异常与边界行为", "value": _percent(behavior_passed, len(exceptional)), "unit": "%", "passed": behavior_passed, "total": len(exceptional), "description": "澄清、空数据、不成熟窗口、拒绝与口径歧义的预期状态。"})
    durations = sorted(row["duration_ms"] for row in rows)
    split_names = [name for name in ("development", "heldout", "audit") if any(row["split"] == name for row in rows)]
    splits = {split: {"total": sum(row["split"] == split for row in rows), "passed": sum(row["split"] == split and row["passed"] for row in rows)} for split in split_names}
    return {"status": "completed", "title": "固定样本确定性流程验证" if mode == "demo" else "固定样本真实模型工具调用评测", "generated_at": datetime.now(timezone.utc).isoformat(), "mode": mode, "transport": "AnalysisRequest validation + actual app.engine / app.live_agent", "live_status": "not_run" if mode == "demo" else "completed", "total": total, "passed": passed, "failed": total - passed, "repeat": repeat, "cases_sha256": source_hash, "metrics": metrics, "splits": splits, "cases": rows, "latency_ms": {"p50": statistics.median(durations) if durations else None, "p95": durations[min(len(durations) - 1, math.ceil(len(durations) * .95) - 1)] if durations else None}, "limitations": ["这是本项目固定合成数据的公开验收与回归样本，不是行业基准，也不证明真实业务问题的泛化能力。", "demo 模式没有调用大模型；关键词路由与确定性工具验证不能称为 LLM 准确率。", "demo 日期与筛选由结构化请求字段提供；不评自然语言日期或筛选抽取能力。", "heldout 是预先分开的项目验收子集；公开运行后属于已暴露回归集。进一步调参需另建未见测试集。", "数值基准独立读取原始用户/活动/订单表并逐事件聚合，不使用业务函数输出生成 gold；部分复杂流程仅校验明确列出的不变量。", "这里直接执行实际请求模型和应用引擎，不包含浏览器、远端网络、HTTP限流或报告下载的端到端验收。", "当前耗时为本机引擎时间；不代表云服务延迟、人工节省时间或投资回报。"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("demo", "live"), default="demo")
    parser.add_argument("--split", choices=("all", "development", "heldout", "audit"), default="all")
    parser.add_argument("--suite", choices=("main", "audit"), default="main")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 1 <= args.repeat <= 10:
        parser.error("repeat must be between 1 and 10")
    source = ROOT / "evals" / ("cases.json" if args.suite == "main" else "audit-cases.json")
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    cases = json.loads(source.read_text())["cases"]
    if args.split != "all":
        cases = [case for case in cases if case["split"] == args.split]
    if args.limit is not None:
        if args.limit < 1:
            parser.error("limit must be positive")
        cases = cases[:args.limit]
    target = args.output or ROOT / "evals" / (("audit-results.json" if args.suite == "audit" else "results.json") if args.mode == "demo" else "live-results.json")
    if args.mode == "live" and not os.getenv("OPENAI_API_KEY"):
        result = {"status": "not_run", "title": "真实模型评测尚未运行", "mode": "live", "live_status": "not_run", "reason": "没有 OPENAI_API_KEY；未调用模型，也未以demo结果代替。", "generated_at": datetime.now(timezone.utc).isoformat(), "total": 0, "passed": 0, "failed": 0, "requested_cases": len(cases), "cases_sha256": source_hash, "metrics": [], "cases": []}
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(result["reason"])
        return 2
    engine.initialize()
    result = summarize(evaluate(cases, args.mode, args.repeat), args.mode, source_hash, args.repeat)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(f"\n{result['passed']}/{result['total']} passed; {result['failed']} failed. Output: {target}")
    return int(result["failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
