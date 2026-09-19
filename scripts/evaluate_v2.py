#!/usr/bin/env python3
"""Public deterministic regression for onboarding and experiment decisions.

Independent gold reads raw events and uses Python sets / event ordering. No
business domain's private calculation function is used as an oracle.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
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

REGISTRY = json.loads((ROOT/"app/data/onboarding_metrics.json").read_text(encoding="utf-8"))
DEFAULT_DATES = ("2026-08-24", "2026-08-30", "2026-08-17", "2026-08-23")
LIMITATIONS = [
    "这是公开的确定性业务回归与验收任务，不是盲测、行业基准或真实业务泛化证明。",
    "demo 没有调用大模型；通过率不表示 LLM 准确率。结构化日期/筛选由样本提供，不验证任意自然语言抽取。",
    "数值基准独立读取原始用户/事件/批次清单，使用 Python 集合、时间比较和排序复算；没有把业务函数结果用作 gold。",
    "SQL 重放与引用存在验证不等于自然语言证据语义已全部经过人工审阅。",
    "重复执行报告唯一任务数和执行次数；同一任务多次执行不是多个独立问题。",
    "本机引擎耗时不等于云服务延迟、人工工作时长或业务收益。真实模型结果单独记录，未调用时保持 not_run。",
]


def connection(domain):
    con = sqlite3.connect(engine.database(domain).resolve().as_uri()+"?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only=ON")
    return con


def add(checks, name, actual, expected, kind="numeric", tolerance=.0011):
    if actual is None or expected is None:
        passed = actual is expected
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        passed = isinstance(actual, (int, float)) and not isinstance(actual, bool) and math.isfinite(actual) and abs(actual-expected) <= tolerance
    else:
        passed = actual == expected
    checks.append({"name": name, "kind": kind, "passed": passed, "expected": expected, "actual": actual})


def periods(request):
    start, end = request.get("start") or DEFAULT_DATES[0], request.get("end") or DEFAULT_DATES[1]
    previous_end = request.get("compare_end") or (date.fromisoformat(start)-timedelta(days=1)).isoformat()
    previous_start = request.get("compare_start") or (date.fromisoformat(previous_end)-(date.fromisoformat(end)-date.fromisoformat(start))).isoformat()
    return {"current": (start, end), "previous": (previous_start, previous_end)}


class OnboardingOracle:
    """Contract-driven event walk. No domain analysis SQL or private functions."""
    def __init__(self):
        with connection("onboarding") as con:
            self.users = [dict(row) for row in con.execute("SELECT * FROM onboarding_users")]
            self.events = [dict(row) for row in con.execute("SELECT * FROM onboarding_events")]
            self.batches = [dict(row) for row in con.execute("SELECT * FROM onboarding_ingest_batches")]
            self.snapshots = dict(con.execute("SELECT scenario,as_of FROM onboarding_snapshots"))
        self.by_user = defaultdict(list)
        for event in self.events:
            self.by_user[event["user_id"]].append(event)
        for values in self.by_user.values():
            values.sort(key=lambda value: (value["event_time"], value["event_id"]))
        self.earliest = min(batch["event_date"] for batch in self.batches)
        self.latest = max(batch["event_date"] for batch in self.batches)

    def selected(self, request):
        filters = request.get("filters", {})
        def included(user):
            for field in REGISTRY["allowed_dimensions"]:
                if field in filters:
                    allowed = filters[field] if isinstance(filters[field], list) else [filters[field]]
                    if user[field] not in allowed:
                        return False
            return True
        return {period: [user for user in self.users if start <= user["signup_date"] <= end and included(user)] for period, (start, end) in periods(request).items()}

    def data(self, request):
        as_of = self.snapshots[request.get("filters", {}).get("scenario", "business_drop")]
        selected = self.selected(request)
        devices = {user["device"] for users in selected.values() for user in users}
        arrived = Counter(event["batch_id"] for event in self.events if event["ingested_at"] <= as_of)
        visible_manifests = {(batch["device"], batch["event_date"]): batch for batch in self.batches if batch["manifest_available_at"] <= as_of}
        watermarks = {}
        for device in devices:
            cursor = date.fromisoformat(self.earliest)
            while cursor.isoformat() <= self.latest:
                batch = visible_manifests.get((device, cursor.isoformat()))
                if not batch or arrived[batch["batch_id"]] != batch["expected_events"]:
                    break
                cursor += timedelta(days=1)
            watermarks[device] = cursor.isoformat()+" 00:00:00"
        return as_of, selected, watermarks, min(watermarks.values()) if watermarks else None

    def user_flags(self, user, as_of):
        signup = datetime.fromisoformat(user["signup_at"])
        end = signup+timedelta(hours=REGISTRY["funnel"]["window_hours"])
        events = [event for event in self.by_user[user["user_id"]] if event["ingested_at"] <= as_of]
        active_days = {(datetime.fromisoformat(event["event_time"]).date()-signup.date()).days for event in events if event["event_name"] == "app_active"}
        flags = {"d1": int(1 in active_days), "d7": int(7 in active_days), "within7": int(bool(set(range(1, 8)) & active_days))}
        flags.update(registered=0, onboarded=0, feed_success=0, activated=0)
        cursor = None
        for step in REGISTRY["funnel"]["steps"]:
            candidates = []
            for event in events:
                when = datetime.fromisoformat(event["event_time"])
                if event["event_name"] != step["event"] or not signup <= when < end or (cursor is not None and when <= cursor):
                    continue
                if step["id"] == "activated" and (event["duration_seconds"] is None or event["duration_seconds"] < REGISTRY["activation_duration_seconds"]):
                    continue
                candidates.append(when)
            if not candidates:
                break
            cursor = min(candidates)
            flags[step["id"]] = 1
        return flags

    @staticmethod
    def required_until(users, metric):
        if not users:
            return None
        if metric == "activated_24h":
            return max(datetime.fromisoformat(user["signup_at"])+timedelta(hours=24) for user in users).isoformat(sep=" ")
        days = 1 if metric == "new_user_retention_d1" else 7
        return (datetime.fromisoformat(max(user["signup_date"] for user in users))+timedelta(days=days+1)).isoformat(sep=" ")

    def verify(self, request, result, checks):
        as_of, cohorts, watermarks, watermark = self.data(request)
        quality = result.get("data_quality") or {}
        if quality:
            add(checks, "原始批次连续水位", quality.get("watermark"), watermark, "quality")
            for device, value in watermarks.items():
                add(checks, "分区连续水位 / "+device, quality.get("watermarks_by_device", {}).get(device), value, "quality")
        if result["status"] in ("data_quality_blocked", "insufficient_data"):
            business_values = [item.get("value") for item in result.get("kpis", []) if item["id"] in {"new_user_retention_d1", "new_user_retention_d7", "return_within_days_1_7", "activated_24h"}]
            add(checks, "阻断时不发布受影响业务值", all(value is None for value in business_values), True, "behavior")
            return
        if result["status"] != "completed" or request.get("task") == "quality":
            return
        flags = {period: {user["user_id"]: self.user_flags(user, as_of) for user in users} for period, users in cohorts.items()}
        metrics = {"new_user_retention_d1": "d1", "new_user_retention_d7": "d7", "return_within_days_1_7": "within7", "activated_24h": "activated"}
        metric_rows = {row["metric_id"]: row for table in result.get("tables", []) if table["id"] == "cohort-metrics" for row in table["rows"]}
        for metric, column in metrics.items():
            row = metric_rows.get(metric, {})
            required = self.required_until(cohorts["current"]+cohorts["previous"], metric)
            available = required is not None and as_of >= required and watermark is not None and watermark >= required
            for period, users in cohorts.items():
                n = len(users)
                successes = sum(item[column] for item in flags[period].values())
                add(checks, f"事件集合 / {metric} / {period} 成功数", row.get(period+"_successes"), successes if available else None)
                add(checks, f"事件集合 / {metric} / {period} 分母", row.get(period+"_users"), n)
                add(checks, f"事件集合 / {metric} / {period} 比例", row.get(period+"_pct"), successes/n*100 if available and n else None)
        kpis = {item["id"]: item for item in result.get("kpis", [])}
        selected_metric = result.get("metric_contract", {}).get("id")
        if selected_metric in metrics:
            rates = {period: sum(item[metrics[selected_metric]] for item in items.values())/len(items)*100 for period, items in flags.items() if items}
            if all(period in rates for period in ("current", "previous")):
                add(checks, "主指标当前值独立复算", kpis.get(selected_metric, {}).get("value"), rates["current"])
                add(checks, "主指标变化独立复算", kpis.get(selected_metric, {}).get("delta"), rates["current"]-rates["previous"])
                if "mix_pp" in kpis and "performance_pp" in kpis:
                    add(checks, "分解还原总体变化", kpis["mix_pp"]["value"]+kpis["performance_pp"]["value"], rates["current"]-rates["previous"], tolerance=.0021)
        for step in result.get("funnel", {}).get("steps", []):
            column = step["step_id"]
            for period in ("current", "previous"):
                total = sum(item[column] for item in flags[period].values())
                add(checks, f"事件排序漏斗 / {column} / {period}", step.get(period+"_users"), total, "funnel")
        step_counts = [step["current_users"] for step in result.get("funnel", {}).get("steps", [])]
        if step_counts:
            add(checks, "同 cohort 有序漏斗人数单调", all(a >= b for a, b in zip(step_counts, step_counts[1:])), True, "funnel")


class ExperimentOracle:
    def __init__(self):
        with connection("experiments") as con:
            self.registry = {row["experiment_id"]: dict(row) for row in con.execute("SELECT * FROM experiment_registry")}
            self.users = [dict(row) for row in con.execute("SELECT * FROM experiment_assignments")]
            self.events = [dict(row) for row in con.execute("SELECT * FROM experiment_outcomes")]
        self.by_user = defaultdict(list)
        for event in self.events:
            self.by_user[(event["experiment_id"], event["user_id"])].append(event)

    def verify(self, request, result, checks):
        scenario = request.get("filters", {}).get("scenario", "healthy_gain")
        registry = self.registry[scenario]
        cutoff = datetime.fromisoformat(registry["snapshot_date"])+timedelta(days=1)
        gold = {arm: {"users": 0, "mature_users": 0, "retained_users": 0, "negative_users": 0} for arm in ("control", "treatment")}
        for user in self.users:
            if user["experiment_id"] != scenario:
                continue
            signup = datetime.fromisoformat(user["registered_at"])
            group = gold[user["arm"]]
            group["users"] += 1
            if datetime.combine(signup.date()+timedelta(days=8), datetime.min.time()) > cutoff or signup+timedelta(hours=24) > cutoff:
                continue
            group["mature_users"] += 1
            events = self.by_user[(scenario, user["user_id"])]
            retained, negative = False, False
            for event in events:
                stamp = datetime.fromisoformat(event["event_at"])
                if datetime.fromisoformat(event["ingested_at"]) >= cutoff:
                    continue
                retained |= event["event_name"] == "qualified_activity" and (stamp.date()-signup.date()).days == 7
                negative |= event["event_name"] == "negative_feedback" and signup <= stamp < signup+timedelta(hours=24)
            group["retained_users"] += int(retained)
            group["negative_users"] += int(negative)
        observed = {row["arm"]: row for evidence in result.get("evidence", []) if evidence["id"] == "experiment-groups" for row in evidence["rows"]}
        for arm, counts in gold.items():
            for key, value in counts.items():
                expected = None if counts["mature_users"] == 0 and key in ("retained_users", "negative_users") else value
                add(checks, f"原始实验事件 / {arm} / {key}", observed.get(arm, {}).get(key), expected)
        stats = result.get("experiment_statistics", {})
        for key, success in (("primary", "retained_users"), ("guardrail", "negative_users")):
            if stats.get(key) is None:
                continue
            p0 = gold["control"][success]/gold["control"]["users"]
            p1 = gold["treatment"][success]/gold["treatment"]["users"]
            add(checks, "独立实验率差 / "+key, stats[key]["lift_pp"], (p1-p0)*100)
            add(checks, "独立相对提升 / "+key, stats[key]["relative_lift_pct"], (p1-p0)/p0*100 if p0 else None)
        if result["status"] in ("invalid_data", "waiting_for_maturity"):
            add(checks, "质量或成熟失败不解释效应", stats.get("primary"), None, "behavior")
        add(checks, "实验只建议不执行推全", result.get("decision", {}).get("executes_rollout"), False, "behavior")


def invariant_checks(result, checks, domain):
    required = {"status", "title", "summary", "metric_contract", "kpis", "tables", "charts", "findings", "evidence", "trace", "limitations", "suggestions"}
    add(checks, "完整返回合同", required <= set(result), True, "contract")
    ids = {item["id"] for item in result.get("evidence", [])}
    facts = [item for item in result.get("findings", []) if item.get("kind") == "fact"]
    if facts:
        add(checks, "事实引用存在的证据", all(item.get("evidence_ids") and set(item["evidence_ids"]) <= ids for item in facts), True, "evidence")
    if result.get("evidence"):
        with connection(domain) as con:
            for evidence in result["evidence"]:
                observed = [dict(row) for row in con.execute(evidence["sql"], evidence["parameters"])]
                add(checks, "SQL 重放 / "+evidence["id"], observed == evidence["rows"], True, "evidence")
    if result.get("status") == "needs_clarification":
        add(checks, "澄清时不生成经营数值", result.get("kpis"), [], "behavior")
    add(checks, "图表字段可复算", all(all(chart["x_key"] in row and all(key in row for key in chart["y_keys"]) for row in chart["data"]) for chart in result.get("charts", [])), True, "contract")
    json.dumps(result, allow_nan=False)


def evaluate(cases, mode, repeat):
    onboarding, experiments = OnboardingOracle(), ExperimentOracle()
    outputs = []
    for repetition in range(1, repeat+1):
        for case in cases:
            began = time.perf_counter()
            checks, result, error = [], {}, None
            try:
                request = AnalysisRequest.model_validate({**case["request"], "mode": mode}).model_dump(exclude_none=True)
                if mode == "live":
                    from app.live_agent import execute
                    result = execute(request)
                else:
                    result = engine.analyze_domain(request)
                add(checks, "业务状态", result.get("status"), case["expected_status"], "status")
                if case.get("expected_metric"):
                    add(checks, "指标口径选择", result.get("metric_contract", {}).get("id"), case["expected_metric"], "semantic")
                if case.get("expected_decision"):
                    add(checks, "实验决策", result.get("decision", {}).get("code"), case["expected_decision"], "decision")
                invariant_checks(result, checks, request["domain"])
                if case.get("oracle"):
                    if case["oracle"] == "onboarding":
                        onboarding.verify(request, result, checks)
                    else:
                        experiments.verify(request, result, checks)
            except Exception as exc:
                # Failed provider calls stay failures; exception messages are omitted to avoid secrets from third-party errors.
                error = type(exc).__name__
                add(checks, "正常返回业务结果", error, "no exception", "contract")
            duration = round((time.perf_counter()-began)*1000, 3)
            row = {"id": case["id"], "repetition": repetition, "split": "public_regression", "domain": case["request"]["domain"],
                   "question": case["request"]["question"], "request": case["request"], "category": case["category"],
                   "expected_status": case["expected_status"], "actual_status": result.get("status", "error"),
                   "passed": bool(checks) and all(check["passed"] for check in checks), "checks": checks, "duration_ms": duration,
                   "summary": result.get("summary", ""), "error": error}
            if result.get("model_run"):
                row["model_run"] = result["model_run"]
            outputs.append(row)
            print(f"{'PASS' if row['passed'] else 'FAIL'} {case['id']} {row['actual_status']} {duration:.1f}ms", flush=True)
    return outputs


def summarize(rows, mode, repeat, source_hash):
    passed = sum(row["passed"] for row in rows)
    metrics = []
    for kind, label in (("status", "业务状态"), ("semantic", "指标合同选择"), ("numeric", "独立事件数值复算"), ("funnel", "有序漏斗独立复算"), ("quality", "批次连续水位复算"), ("decision", "实验决策"), ("evidence", "SQL 重放与引用"), ("behavior", "异常和拒绝行为")):
        applicable = [row for row in rows if any(item["kind"] == kind for item in row["checks"])]
        successes = sum(all(item["passed"] for item in row["checks"] if item["kind"] == kind) for row in applicable)
        metrics.append({"id": kind, "label": label, "passed": successes, "total": len(applicable), "value": round(successes/len(applicable)*100, 2) if applicable else None, "unit": "%", "description": "按适用任务执行计数；该类任一检查失败则该任务失败。"})
    by_id = defaultdict(list)
    for row in rows:
        by_id[row["id"]].append(row["passed"])
    durations = sorted(row["duration_ms"] for row in rows)
    return {"status": "completed", "title": "增长决策 V2：公开确定性业务回归" if mode == "demo" else "增长决策 V2：真实模型公开任务评测",
            "mode": mode, "live_status": "not_run" if mode == "demo" else "completed", "generated_at": datetime.now(timezone.utc).isoformat(),
            "transport": "AnalysisRequest + app.engine / app.live_agent；不含浏览器与云端HTTP链路",
            "total": len(rows), "passed": passed, "failed": len(rows)-passed, "unique_tasks": len(by_id), "repeat": repeat,
            "all_repeats_passed_tasks": sum(all(results) for results in by_id.values()), "cases_sha256": source_hash,
            "metrics": metrics, "cases": rows, "limitations": LIMITATIONS,
            "latency_ms": {"p50": statistics.median(durations) if durations else None, "p95": durations[min(len(durations)-1, math.ceil(len(durations)*.95)-1)] if durations else None}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("demo", "live"), default="demo")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 1 <= args.repeat <= 10:
        parser.error("repeat must be between 1 and 10")
    if args.limit is not None and args.limit < 1:
        parser.error("limit must be positive")
    source = ROOT/"evals/v2-cases.json"
    cases = json.loads(source.read_text(encoding="utf-8"))["cases"]
    if args.limit:
        cases = cases[:args.limit]
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    target = args.output or ROOT/"evals"/("v2-results.json" if args.mode == "demo" else "v2-live-results.json")
    if args.mode == "live" and not os.getenv("OPENAI_API_KEY"):
        result = {"status": "not_run", "title": "增长决策 V2 真实模型评测尚未运行", "mode": "live", "live_status": "not_run", "reason": "没有配置可用的 OPENAI_API_KEY，未调用模型；没有使用 demo 结果替代。", "generated_at": datetime.now(timezone.utc).isoformat(), "total": 0, "passed": 0, "failed": 0, "requested_cases": len(cases), "repeat": args.repeat, "cases_sha256": source_hash, "metrics": [], "cases": [], "limitations": LIMITATIONS}
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        print(result["reason"])
        return 2
    engine.initialize()
    result = summarize(evaluate(cases, args.mode, args.repeat), args.mode, args.repeat, source_hash)
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+"\n"
    if result["failed"]:
        first_failure = ROOT/"evals"/("v2-first-run.json" if args.mode == "demo" else "v2-live-first-run.json")
        if not first_failure.exists():
            first_failure.write_text(encoded, encoding="utf-8")
    target.write_text(encoded, encoding="utf-8")
    print(f"{result['passed']}/{result['total']} executions passed; {result['unique_tasks']} unique tasks; output={target}")
    return int(result["failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
