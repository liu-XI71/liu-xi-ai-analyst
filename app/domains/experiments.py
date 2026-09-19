"""Preregistered, user-level experiment review over reproducible synthetic logs.

Decision rules depend on queried records and statistics, never scenario names.
No rollout or messaging side effect is performed by this module.
"""
from __future__ import annotations

import math
import random
import sqlite3
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import NormalDist
from typing import Any

VERSION = "experiments.v2.0"
SEED = 7109
SOURCE = "固定种子 7109 的合成实验日志；用于方法验证，不代表真实企业收益"
START = "2026-08-17"
END = "2026-08-30"
SNAPSHOT = "2026-09-06"
SCENARIOS = (
    {"value": "healthy_gain", "label": "健康正向 · 完整固定窗口", "start": START, "end": END},
    {"value": "srm", "label": "分配异常 · 样本比例失衡", "start": START, "end": END},
    {"value": "guardrail", "label": "体验代价 · 负反馈围栏恶化", "start": START, "end": END},
    {"value": "immature", "label": "等待观察 · D7 尚未成熟", "start": "2026-09-03", "end": SNAPSHOT},
    {"value": "underpowered", "label": "证据不足 · 未达设计样本量", "start": START, "end": END},
    {"value": "unequal_allocation", "label": "非等流量 · 预注册 30:70", "start": START, "end": END},
    {"value": "config_change", "label": "配置变更 · 运行中修改版本", "start": START, "end": END},
    {"value": "data_gap", "label": "到数缺口 · 采集覆盖不完整", "start": START, "end": END},
)
CONTRACT = {
    "id": "experiment_new_user_retention_d7", "name": "实验新用户精确 D7 留存率",
    "version": VERSION, "numerator": "注册后第 7 个自然日发生至少一次 qualified_activity 的原始分配用户数",
    "denominator": "预注册入组窗口内所有合格的新注册随机分配用户；固定窗口全部成熟后评审",
    "grain": "用户", "unit": "%", "timezone": "Asia/Shanghai；时间戳为该时区本地时间",
    "timestamp_format": "YYYY-MM-DD HH:MM:SS；有效公历日期，秒精度，空格分隔，无时区后缀",
    "date_format": "YYYY-MM-DD；有效公历日期",
    "timestamp_policy": "非规范时间格式整份评审标记 invalid_data；接入层须显式转换时区并规范化，不静默丢弃事件",
    "window": "[注册日 + 7 日 00:00:00, 注册日 + 8 日 00:00:00)",
    "analysis_population": "ITT：按原始分配组分析，包括未暴露用户；不按事后活跃筛选",
    "maturity": "采集水位覆盖完整 D7 自然日，且注册后 24 小时负反馈窗口完整",
    "not_equivalent_to": "次 7 日内任意回访、D1 或曝光用户中的留存",
    "data_source": SOURCE,
}
TABLES = [
    {"name": "experiment_registry", "description": "预注册目标、分配比、窗口、功效与围栏", "columns": ["experiment_id", "start_date", "end_date", "snapshot_date", "expected_treatment_share", "baseline_rate", "mde", "alpha", "power", "min_business_lift", "negative_baseline", "negative_margin", "guardrail_alpha", "config_version", "expected_assignment_count"]},
    {"name": "experiment_assignments", "description": "原始用户级随机分配记录；重复和串组在评审时检出", "columns": ["assignment_id", "experiment_id", "user_id", "arm", "registered_at", "assigned_at", "config_version"]},
    {"name": "experiment_exposures", "description": "实际暴露日志，只用于核查，不改变 ITT 分母", "columns": ["exposure_id", "experiment_id", "user_id", "arm", "exposed_at"]},
    {"name": "experiment_outcomes", "description": "合格活跃及负反馈事件，按时间窗口重新计算指标", "columns": ["event_id", "experiment_id", "user_id", "event_name", "event_at", "ingested_at", "schema_version"]},
    {"name": "experiment_coverage", "description": "每个分配用户的采集水位与完整标记", "columns": ["experiment_id", "user_id", "observed_until", "complete"]},
    {"name": "experiment_changelog", "description": "实验配置变更轨迹", "columns": ["change_id", "experiment_id", "changed_at", "field", "old_value", "new_value", "material"]},
]


def metadata() -> dict:
    return {
        "id": "experiments", "name": "实验评审与增长决策", "description": "先审数据、分配和观察窗口，再评估 D7 效应、功效设计与体验围栏。",
        "data_source": SOURCE, "data_range": {"start": START, "end": SNAPSHOT},
        "default_request": {"domain": "experiments", "task": "experiment", "start": START, "end": END, "filters": {"scenario": "healthy_gain"}},
        "metrics": [dict(CONTRACT), {"id": "negative_feedback_24h", "name": "注册后 24 小时负反馈率", "unit": "%", "definition": "有至少一次 negative_feedback 事件的分配用户 / 所有分配用户；[注册时间, 注册时间+24h)；仅完整窗口"}],
        "tables": TABLES, "filters": {"scenario": [dict(item) for item in SCENARIOS]},
        "scenarios": [dict(item) for item in SCENARIOS],
        "examples": [
            {"question": "新用户承接实验能否进入灰度评审？检查 D7 提升、分配质量和负反馈围栏。", "task": "experiment", "filters": {"scenario": "healthy_gain"}},
            {"question": "实验表面正向，但负反馈是否超过预设容忍范围？", "task": "experiment", "filters": {"scenario": "guardrail"}},
            {"question": "生成包含功效设计、质量门槛、效果区间和复查动作的实验决策备忘录。", "task": "report", "filters": {"scenario": "healthy_gain"}},
        ],
    }


def build_database(path: Path) -> None:
    """Create only experiment tables, idempotently, with deterministic Bernoulli draws."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, timeout=60) as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS experiment_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS experiment_registry (
          experiment_id TEXT PRIMARY KEY, start_date TEXT NOT NULL, end_date TEXT NOT NULL,
          snapshot_date TEXT NOT NULL, expected_treatment_share REAL NOT NULL,
          baseline_rate REAL NOT NULL, mde REAL NOT NULL, alpha REAL NOT NULL, power REAL NOT NULL,
          min_business_lift REAL NOT NULL, negative_baseline REAL NOT NULL, negative_margin REAL NOT NULL,
          guardrail_alpha REAL NOT NULL, config_version TEXT NOT NULL, expected_assignment_count INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS experiment_assignments (
          assignment_id INTEGER PRIMARY KEY, experiment_id TEXT NOT NULL, user_id TEXT NOT NULL,
          arm TEXT NOT NULL, registered_at TEXT NOT NULL, assigned_at TEXT NOT NULL, config_version TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS experiment_exposures (
          exposure_id INTEGER PRIMARY KEY, experiment_id TEXT NOT NULL, user_id TEXT NOT NULL,
          arm TEXT NOT NULL, exposed_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS experiment_outcomes (
          event_id INTEGER PRIMARY KEY, experiment_id TEXT NOT NULL, user_id TEXT NOT NULL,
          event_name TEXT NOT NULL, event_at TEXT NOT NULL, ingested_at TEXT NOT NULL, schema_version TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS experiment_coverage (
          experiment_id TEXT NOT NULL, user_id TEXT NOT NULL, observed_until TEXT NOT NULL,
          complete INTEGER NOT NULL, PRIMARY KEY(experiment_id,user_id)
        );
        CREATE TABLE IF NOT EXISTS experiment_changelog (
          change_id INTEGER PRIMARY KEY, experiment_id TEXT NOT NULL, changed_at TEXT NOT NULL,
          field TEXT NOT NULL, old_value TEXT NOT NULL, new_value TEXT NOT NULL, material INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS experiment_assignments_user ON experiment_assignments(experiment_id,user_id);
        CREATE INDEX IF NOT EXISTS experiment_outcomes_user ON experiment_outcomes(experiment_id,user_id,event_name,event_at);
        CREATE INDEX IF NOT EXISTS experiment_exposures_user ON experiment_exposures(experiment_id,user_id);
        """)
        if con.execute("SELECT value FROM experiment_metadata WHERE key='version'").fetchone() == (VERSION,):
            return
        for table in reversed([entry["name"] for entry in TABLES]):
            con.execute(f"DELETE FROM {table}")
        for index, scenario in enumerate(SCENARIOS):
            scenario_id = scenario["value"]
            rng = random.Random(SEED + index)
            count = 240 if scenario_id == "underpowered" else (20000 if scenario_id == "unequal_allocation" else 16000)
            expected_share = .7 if scenario_id == "unequal_allocation" else .5
            actual_share = .7 if scenario_id == "srm" else expected_share
            start, end = date.fromisoformat(scenario["start"]), date.fromisoformat(scenario["end"])
            cutoff = datetime.fromisoformat(SNAPSHOT) + timedelta(days=1)
            con.execute("INSERT INTO experiment_registry VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                scenario_id, start.isoformat(), end.isoformat(), SNAPSHOT, expected_share,
                .28, .025, .05, .8, .01, .04, .015, .025, "onboarding-v1", count))
            assignments, exposures, outcomes, coverage = [], [], [], []
            for user in range(count):
                uid = f"{scenario_id}-{user:06d}"
                assigned = datetime.combine(start + timedelta(days=rng.randrange((end-start).days + 1)), datetime.min.time()) + timedelta(seconds=rng.randrange(86400))
                arm = "treatment" if rng.random() < actual_share else "control"
                version = "onboarding-v2" if scenario_id == "config_change" and assigned.date() >= date(2026, 8, 24) else "onboarding-v1"
                stamp = assigned.isoformat(sep=" ")
                assignments.append((scenario_id, uid, arm, stamp, stamp, version))
                exposed = assigned + timedelta(seconds=rng.randrange(1, 61))
                if rng.random() < .9 and exposed < cutoff:
                    exposures.append((scenario_id, uid, arm, exposed.isoformat(sep=" ")))
                # Draw individual outcomes, retaining both positive and absent outcomes through a coverage manifest.
                retained = rng.random() < (.34 if arm == "treatment" else .28)
                negative = rng.random() < (.085 if scenario_id == "guardrail" and arm == "treatment" else .04)
                activity_day = assigned.date() + timedelta(days=7)
                active_at = datetime.combine(activity_day, datetime.min.time()) + timedelta(seconds=rng.randrange(86400))
                negative_at = assigned + timedelta(seconds=rng.randrange(86400))
                # Non-D7 activity is deliberately present: it must never inflate exact D7.
                next_day = datetime.combine(assigned.date() + timedelta(days=1), datetime.min.time()) + timedelta(hours=12)
                for event, when, exists in (("qualified_activity", active_at, retained), ("negative_feedback", negative_at, negative), ("qualified_activity", next_day, rng.random() < .4)):
                    if exists and when < cutoff:
                        ingested = min(when + timedelta(minutes=2), cutoff - timedelta(seconds=1))
                        outcomes.append((scenario_id, uid, event, when.isoformat(sep=" "), ingested.isoformat(sep=" "), "events-v1"))
                if scenario_id != "data_gap" or user % 100 != 0:
                    coverage.append((scenario_id, uid, cutoff.isoformat(sep=" "), 1))
            con.executemany("INSERT INTO experiment_assignments(experiment_id,user_id,arm,registered_at,assigned_at,config_version) VALUES (?,?,?,?,?,?)", assignments)
            con.executemany("INSERT INTO experiment_exposures(experiment_id,user_id,arm,exposed_at) VALUES (?,?,?,?)", exposures)
            con.executemany("INSERT INTO experiment_outcomes(experiment_id,user_id,event_name,event_at,ingested_at,schema_version) VALUES (?,?,?,?,?,?)", outcomes)
            con.executemany("INSERT INTO experiment_coverage VALUES (?,?,?,?)", coverage)
            if scenario_id == "config_change":
                con.execute("INSERT INTO experiment_changelog(experiment_id,changed_at,field,old_value,new_value,material) VALUES (?,?,?,?,?,?)", (scenario_id, "2026-08-24 00:00:00", "config_version", "onboarding-v1", "onboarding-v2", 1))
        con.execute("INSERT OR REPLACE INTO experiment_metadata VALUES ('version',?)", (VERSION,))
        con.execute("INSERT OR REPLACE INTO experiment_metadata VALUES ('seed',?)", (str(SEED),))


def sample_size_plan(registry: dict) -> dict:
    """Normal-approximation designs; individual power targets, not joint power."""
    p0, difference = registry["baseline_rate"], registry["mde"]
    fraction = registry["expected_treatment_share"]
    alpha, power = registry["alpha"], registry["power"]
    negative, margin = registry["negative_baseline"], registry["negative_margin"]
    guardrail_alpha = registry["guardrail_alpha"]
    values = (p0, difference, fraction, alpha, power, negative, margin, guardrail_alpha, registry["min_business_lift"])
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in values):
        raise ValueError("预注册统计参数必须是有限数值。")
    if not (0 < p0 < p0+difference < 1 and 0 < fraction < 1 and 0 < alpha < .5 and .5 < power < 1 and 0 < negative < 1 and 0 < margin < 1 and 0 < guardrail_alpha < .5 and 0 <= registry["min_business_lift"] < 1):
        raise ValueError("预注册基线、MDE、分配比、显著性或功效参数超出有效范围。")
    ratio = fraction / (1-fraction)
    normal = NormalDist()
    h = 2 * math.asin(math.sqrt(p0+difference)) - 2 * math.asin(math.sqrt(p0))
    primary_control = math.ceil((1 + 1/ratio) * (normal.inv_cdf(1-alpha/2) + normal.inv_cdf(power))**2 / h**2)
    guardrail_control = math.ceil(negative*(1-negative)*(1 + 1/ratio) * (normal.inv_cdf(1-guardrail_alpha) + normal.inv_cdf(power))**2 / margin**2)
    control = max(primary_control, guardrail_control)
    return {
        "control_required": control, "treatment_required": math.ceil(control*ratio),
        "primary_control_required": primary_control, "primary_treatment_required": math.ceil(primary_control*ratio),
        "guardrail_control_required": guardrail_control, "guardrail_treatment_required": math.ceil(guardrail_control*ratio),
        "total_required": control + math.ceil(control*ratio), "allocation_treatment_to_control": ratio,
        "primary_method": "Cohen h 正态近似：nC=(1+1/r)×(z(1−alpha/2)+z(power))²/h²；nT=ceil(r×nC)",
        "guardrail_method": "非劣设计正态近似，假设真实差异为 0：nC=p(1−p)(1+1/r)×(z(1−alphaNI)+z(power))²/margin²",
        "planning_assumptions": "两项各自达到设计功效，不声明联合功效；主要设计检验差异为零，不保证业务区间门槛也有相同功效；样本量取较大需求，不计算事后 observed power。",
        "evidence_ids": ["experiment-registry"],
    }


def wilson_interval(successes: int, total: int, alpha: float = .05) -> tuple[float, float]:
    if not 0 <= successes <= total or total <= 0 or not 0 < alpha < 1:
        raise ValueError("二项样本或显著性参数无效。")
    z = NormalDist().inv_cdf(1-alpha/2)
    p, z2 = successes/total, z*z
    denominator = 1 + z2/total
    center = (p + z2/(2*total))/denominator
    half = z * math.sqrt(p*(1-p)/total + z2/(4*total*total))/denominator
    return max(0.0, center-half), min(1.0, center+half)


def rate_difference(control_success: int, control_n: int, treatment_success: int, treatment_n: int, alpha: float = .05) -> dict:
    """Newcombe hybrid-score CI from independent Wilson intervals; pooled z p-value."""
    l0, u0 = wilson_interval(control_success, control_n, alpha)
    l1, u1 = wilson_interval(treatment_success, treatment_n, alpha)
    p0, p1 = control_success/control_n, treatment_success/treatment_n
    difference = p1-p0
    lower = max(-1.0, difference-math.sqrt((p1-l1)**2+(u0-p0)**2))
    upper = min(1.0, difference+math.sqrt((u1-p1)**2+(p0-l0)**2))
    pooled = (control_success+treatment_success)/(control_n+treatment_n)
    se = math.sqrt(pooled*(1-pooled)*(1/control_n+1/treatment_n))
    p_value = math.erfc(abs(difference/se)/math.sqrt(2)) if se else (1.0 if difference == 0 else 0.0)
    return {"control_rate_pct": p0*100, "treatment_rate_pct": p1*100, "lift_pp": difference*100,
            "relative_lift_pct": difference/p0*100 if p0 else None,
            "ci_low_pp": lower*100, "ci_high_pp": upper*100, "confidence_level": 1-alpha,
            "p_value": p_value, "ci_method": "Newcombe independent Wilson-score difference",
            "p_value_method": "双侧两比例 pooled z；小样本不用于最终放量门槛"}


def srm_test(control_n: int, treatment_n: int, expected_treatment_share: float) -> dict:
    if min(control_n, treatment_n) < 0 or not 0 < expected_treatment_share < 1:
        raise ValueError("SRM 的人数或预期分配比例无效。")
    total = control_n+treatment_n
    expected_control, expected_treatment = total*(1-expected_treatment_share), total*expected_treatment_share
    if not total:
        return {"chi_square": None, "p_value": None, "expected_control": 0, "expected_treatment": 0, "approximation_valid": False}
    chi = (control_n-expected_control)**2/expected_control + (treatment_n-expected_treatment)**2/expected_treatment
    return {"chi_square": chi, "p_value": math.erfc(math.sqrt(chi/2)), "expected_control": expected_control,
            "expected_treatment": expected_treatment, "approximation_valid": min(expected_control, expected_treatment) >= 5}


def _base() -> dict:
    return {"status": "completed", "title": "新用户承接实验评审", "summary": "", "metric_contract": dict(CONTRACT),
            "kpis": [], "tables": [], "charts": [], "findings": [], "evidence": [], "trace": [], "checks": [],
            "limitations": [SOURCE, "随机化与采集合同成立时，ITT 估计该入组人群和观察窗口的平均因果效应；结果不能外推为长期 LTV 或全平台收益。",
                             "SRM 通过不证明不存在所有数据问题；完整性只针对本地来源清单与合同核查。",
                             "固定窗口设计禁止因每日出现显著结果而提前结束；若需连续决策，应另预注册顺序检验。",
                             "负反馈围栏要求差异区间上界低于非劣界值；未发现显著恶化不等于已证明安全。",
                             "长期 Holdout 用于不同的长期或组合效应问题，不是所有有效 A/B 的统一上线前提。"], "suggestions": []}


def _stop(message: str) -> dict:
    output = _base()
    output.update(status="needs_clarification", title="确认实验评审范围", summary=message)
    output["clarification"] = {"question": message, "options": ["使用选定场景的完整预注册窗口", "选择其他实验场景"]}
    output["suggestions"] = output["clarification"]["options"]
    output["trace"] = [{"tool": "validate_request", "status": "needs_clarification", "description": message}]
    return output


def _query(con: sqlite3.Connection, output: dict, evidence_id: str, label: str, sql: str, params: dict) -> list[dict]:
    start = time.perf_counter()
    rows = [dict(row) for row in con.execute(sql, params).fetchall()]
    output["evidence"].append({"id": evidence_id, "label": label, "sql": sql, "parameters": dict(params), "rows": rows, "source": SOURCE, "metric_version": VERSION})
    output["trace"].append({"tool": "query_experiment", "status": "completed", "description": label, "duration_ms": round((time.perf_counter()-start)*1000, 3)})
    return rows


def _check(output: dict, name: str, label: str, passed: bool | None, rule: str, observed: Any, evidence: list[str], blocking: bool = True) -> None:
    output["checks"].append({"id": name, "label": label, "passed": passed, "rule": rule, "observed": observed, "evidence_ids": evidence, "blocking": blocking})


def _decision(output: dict, code: str, label: str, reason: str, action: str) -> dict:
    output["decision"] = {"code": code, "label": label, "reason": reason, "action": action,
                          "gates": {item["id"]: item["passed"] for item in output["checks"]}, "executes_rollout": False}
    output["suggestions"] = [action, "按预注册入组窗口完成观察后复查；新版本和新假设单独登记。"]
    output["findings"].append({"kind": "action", "text": label + "：" + action,
                               "evidence_ids": [item["id"] for item in output["evidence"]]})
    output["tables"].append({"id": "experiment-checks", "title": "实验评审门槛", "columns": ["label", "rule", "observed", "passed"], "rows": output["checks"].copy()})
    output["trace"].append({"tool": "evaluate_experiment", "status": output["status"], "description": f"{label}；{reason}"})
    return output


def _invalid_timestamp_sql(column: str) -> str:
    """Build a plain SQLite predicate that can be replayed without custom functions.

    Text ordering is chronological only for one fixed local timestamp format.
    SQLite accepts T, offsets, date-only values, 24:00 and even nonexistent days;
    parsing alone is not validation. A zero-second round trip normalizes these
    forms, so exact equality plus the shape/year checks rejects them. Identifiers
    here are source-code constants, never request input.
    """
    pattern = "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]"
    return (f"COALESCE((typeof({column})='text' AND length({column})=19 "
            f"AND {column} GLOB '{pattern}' AND substr({column},1,4) BETWEEN '0001' AND '9999' "
            f"AND datetime({column},'+0 seconds')={column}),0)=0")


def _registered_date(value: Any) -> date:
    """Registry dates use the same canonical calendar representation as SQL."""
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("注册表日期必须是有效公历 YYYY-MM-DD，不能使用紧凑日期或 ISO 周日期。")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("注册表日期必须是有效公历 YYYY-MM-DD。")
    return parsed


QUALITY_SQL = f"""WITH a AS (SELECT * FROM experiment_assignments WHERE experiment_id=:experiment_id),
uid AS (SELECT user_id,COUNT(*) AS records,COUNT(DISTINCT arm) AS arms FROM a GROUP BY user_id)
SELECT
 (SELECT COUNT(*) FROM a) AS assignment_records,
 (SELECT COUNT(*) FROM uid) AS assigned_users,
 (SELECT COUNT(*) FROM uid WHERE records>1) AS duplicate_users,
 (SELECT COUNT(*) FROM uid WHERE arms>1) AS cross_arm_users,
 (SELECT COUNT(*) FROM a WHERE arm NOT IN ('control','treatment')) AS unknown_arms,
 (SELECT COUNT(*) FROM a WHERE date(registered_at)<:start OR date(registered_at)>:end
    OR {_invalid_timestamp_sql('registered_at')} OR {_invalid_timestamp_sql('assigned_at')}
    OR assigned_at<>registered_at) AS invalid_registration_or_assignment,
 (SELECT COUNT(*) FROM a WHERE config_version<>:config_version) AS config_mismatches,
 (SELECT COUNT(*) FROM a LEFT JOIN experiment_coverage c
    ON c.experiment_id=a.experiment_id AND c.user_id=a.user_id WHERE c.user_id IS NULL) AS missing_coverage,
 (SELECT COUNT(*) FROM a JOIN experiment_coverage c ON c.experiment_id=a.experiment_id AND c.user_id=a.user_id
    WHERE c.complete<>1 OR c.observed_until<>:cutoff OR {_invalid_timestamp_sql('c.observed_until')}) AS incomplete_coverage,
 (SELECT COUNT(*) FROM experiment_outcomes o LEFT JOIN a ON a.user_id=o.user_id
    WHERE o.experiment_id=:experiment_id AND a.user_id IS NULL) AS orphan_outcomes,
 (SELECT COUNT(*) FROM experiment_outcomes o JOIN a ON a.user_id=o.user_id
    WHERE o.experiment_id=:experiment_id AND (o.schema_version<>'events-v1'
      OR o.event_name NOT IN ('qualified_activity','negative_feedback')
      OR {_invalid_timestamp_sql('o.event_at')} OR {_invalid_timestamp_sql('o.ingested_at')}
      OR o.event_at<a.registered_at OR o.ingested_at<o.event_at
      OR o.event_at>=:cutoff OR o.ingested_at>=:cutoff)) AS invalid_outcomes,
 (SELECT COUNT(*) FROM experiment_exposures e LEFT JOIN a ON a.user_id=e.user_id
    WHERE e.experiment_id=:experiment_id AND (a.user_id IS NULL OR e.arm<>a.arm
      OR {_invalid_timestamp_sql('e.exposed_at')} OR e.exposed_at<a.assigned_at OR e.exposed_at>=:cutoff)) AS invalid_exposures,
 (SELECT COUNT(*) FROM experiment_changelog WHERE experiment_id=:experiment_id
    AND ({_invalid_timestamp_sql('changed_at')})) AS invalid_change_timestamps,
 (SELECT COUNT(*) FROM experiment_changelog WHERE experiment_id=:experiment_id AND material=1
    AND changed_at>=:start AND changed_at<:cutoff) AS material_changes,
 (SELECT COUNT(*) FROM a WHERE datetime(date(registered_at),'+8 days')>:cutoff
    OR datetime(registered_at,'+24 hours')>:cutoff) AS immature_users
"""

GROUP_SQL = """WITH users AS (
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
FROM users GROUP BY arm ORDER BY arm"""


def analyze(request: dict, path: Path) -> dict:
    """Review one complete registered experiment; arbitrary subsetting is rejected."""
    if not isinstance(request, dict):
        return _stop("实验请求必须是结构化对象。")
    if request.get("domain") not in (None, "experiments") or (request.get("task") or "experiment") not in ("experiment", "report"):
        return _stop("本域只接受 domain=experiments 和 task=experiment/report。")
    filters = request.get("filters")
    if filters is None:
        filters = {}
    if not isinstance(filters, dict) or set(filters)-{"scenario"}:
        return _stop("实验只接受 scenario 场景筛选；预注册总体结论不接受事后渠道、端或暴露人群筛选。")
    scenario = filters.get("scenario", "healthy_gain")
    if not isinstance(scenario, str) or scenario not in {item["value"] for item in SCENARIOS}:
        return _stop("scenario 必须是可用实验场景中的一个字符串。")
    if request.get("compare_start") or request.get("compare_end"):
        return _stop("随机实验比较同期分配组，不接受前后对比日期。")
    if bool(request.get("start")) != bool(request.get("end")):
        return _stop("请同时提供 start/end，或同时留空以使用预注册窗口。")
    output = _base()
    if request.get("task") == "report":
        output["title"] = "新用户承接实验决策备忘录"
    with sqlite3.connect(f"file:{Path(path).resolve()}?mode=ro", uri=True, timeout=15) as con:
        con.row_factory = sqlite3.Row
        con.execute("BEGIN")  # All evidence in a report comes from one SQLite snapshot.
        registry_rows = _query(con, output, "experiment-registry", "实验预注册参数与固定窗口", "SELECT * FROM experiment_registry WHERE experiment_id=:experiment_id", {"experiment_id": scenario})
        if not registry_rows:
            output.update(status="invalid_data", summary="未找到对应实验注册记录，无法校验分配与评审规则。")
            return _decision(output, "invalid_data", "数据需修复", output["summary"], "恢复并核对实验注册记录。")
        registry = registry_rows[0]
        try:
            plan = sample_size_plan(registry)
            first = _registered_date(registry["start_date"])
            last = _registered_date(registry["end_date"])
            snapshot = _registered_date(registry["snapshot_date"])
            if snapshot == date.max or last > date.max-timedelta(days=8):
                raise ValueError("预注册日期必须允许表示完整 D7 窗口与次日排他截止时刻。")
            if first > last or first > snapshot or not isinstance(registry["expected_assignment_count"], int) or registry["expected_assignment_count"] < 0:
                raise ValueError("预注册窗口、快照或来源人数清单无效。")
        except (ValueError, TypeError) as exc:
            output.update(status="invalid_data", summary=str(exc))
            return _decision(output, "invalid_data", "数据需修复", str(exc), "修复注册参数；保留版本和变更记录后重新评审。")
        if request.get("start") is not None and request.get("start") != "":
            if request["start"] != registry["start_date"] or request["end"] != registry["end_date"]:
                return _stop(f"固定窗口为 {registry['start_date']} 至 {registry['end_date']}；部分日期只适用于另行登记的探索性分析，不能替代本次总体实验评审。")
        cutoff = datetime.combine(snapshot+timedelta(days=1), datetime.min.time()).isoformat(sep=" ")
        params = {"experiment_id": scenario, "start": registry["start_date"], "end": registry["end_date"], "cutoff": cutoff, "config_version": registry["config_version"]}
        output["metric_contract"].update(snapshot_date=registry["snapshot_date"], data_as_of_exclusive=cutoff, experiment_period=[registry["start_date"], registry["end_date"]])
        output["experiment_contract"] = {**registry, "population": "新注册用户，注册成功后即时随机分配，按分配组 ITT", "design": "单一主指标、单一预注册围栏、固定窗口", "srm_alpha": .001,
                                           "guardrail": "负反馈率越低越好；H0: treatment−control ≥ margin；须单侧置信上界严格小于 margin", "guardrail_window": "[registered_at, registered_at+24h)",
                                           "business_rule": "主要效应区间下界达到预注册最低业务提升；不是只看点估计", "rollout": "只输出人工灰度评审建议，不执行发布"}
        output["plan"] = plan
        quality = _query(con, output, "experiment-quality", "分配、身份、配置、采集覆盖与成熟检查", QUALITY_SQL, params)[0]
        changes = _query(con, output, "experiment-changes", "实验配置变更记录", "SELECT changed_at,field,old_value,new_value,material FROM experiment_changelog WHERE experiment_id=:experiment_id ORDER BY changed_at", params)
        groups = _query(con, output, "experiment-groups", "ITT 分配人数、暴露与成熟窗口结果", GROUP_SQL, params)
        arms = {row["arm"]: row for row in groups}
        n0, n1 = arms.get("control", {}).get("users", 0), arms.get("treatment", {}).get("users", 0)
        srm = srm_test(n0, n1, registry["expected_treatment_share"])
        output["experiment_statistics"] = {"srm": srm, "primary": None, "guardrail": None, "inference_valid": False}
        _check(output, "source_reconciliation", "来源人数对账", quality["assignment_records"] == registry["expected_assignment_count"], "分配日志条数等于源端清单", f"{quality['assignment_records']} / {registry['expected_assignment_count']}", ["experiment-registry", "experiment-quality"])
        _check(output, "identity", "随机单位唯一", quality["duplicate_users"] == quality["cross_arm_users"] == quality["unknown_arms"] == 0,
               "用户不重复、不串组、分组合法", f"重复 {quality['duplicate_users']}；串组 {quality['cross_arm_users']}；未知组 {quality['unknown_arms']}", ["experiment-quality"])
        _check(output, "eligibility", "入组资格与时间", quality["invalid_registration_or_assignment"] == 0,
               "规范本地秒精度时间；注册成功即时分配且处于完整预注册入组窗口", quality["invalid_registration_or_assignment"], ["experiment-quality"])
        _check(output, "configuration", "配置稳定", quality["config_mismatches"] == quality["material_changes"] == quality["invalid_change_timestamps"] == 0,
               "同一冻结配置，变更时间规范，无入组或观察期内实质变更", f"版本不符 {quality['config_mismatches']}；变更 {quality['material_changes']}；时间无效 {quality['invalid_change_timestamps']}", ["experiment-quality", "experiment-changes"])
        _check(output, "collection", "采集覆盖完整", quality["missing_coverage"] == quality["incomplete_coverage"] == 0,
               "所有分配用户均有完整到数清单，水位与注册快照一致", f"缺清单 {quality['missing_coverage']}；未完整 {quality['incomplete_coverage']}", ["experiment-quality"])
        _check(output, "events", "事件与暴露合同", quality["orphan_outcomes"] == quality["invalid_outcomes"] == quality["invalid_exposures"] == 0,
               "事件有分配来源、版本合法、时间为规范本地秒精度且曝光组不串组", f"孤立事件 {quality['orphan_outcomes']}；无效事件 {quality['invalid_outcomes']}；无效曝光 {quality['invalid_exposures']}", ["experiment-quality"])
        _check(output, "srm", "分配比例 SRM", srm["p_value"] >= .001 if srm["approximation_valid"] else None,
               f"对照:处理={1-registry['expected_treatment_share']:.0%}:{registry['expected_treatment_share']:.0%}；卡方 p≥0.001，期望人数均≥5", srm["p_value"], ["experiment-registry", "experiment-groups"])
        _check(output, "maturity", "固定观察窗口成熟", quality["immature_users"] == 0 and registry["end_date"] <= registry["snapshot_date"],
               "全部分配用户已完整观察 D7 与 24h 围栏；入组窗口已结束", quality["immature_users"], ["experiment-quality", "experiment-registry"])
        output["kpis"] = [
            {"id": "assigned_users", "label": "随机分配用户", "value": quality["assigned_users"], "unit": "人", "evidence_ids": ["experiment-quality"]},
            {"id": "immature_users", "label": "尚未成熟用户", "value": quality["immature_users"], "unit": "人", "evidence_ids": ["experiment-quality"]},
            {"id": "required_users", "label": "设计所需总样本", "value": plan["total_required"], "unit": "人", "evidence_ids": ["experiment-registry"]},
            {"id": "srm_p", "label": "SRM p 值", "value": srm["p_value"], "unit": "", "evidence_ids": ["experiment-registry", "experiment-groups"]},
        ]
        output["tables"] = [
            {"id": "experiment-groups", "title": "ITT 人群与观测计数", "columns": ["arm", "users", "mature_users", "exposed_users", "retained_users", "negative_users"], "rows": groups},
            {"id": "experiment-design", "title": "预注册样本规划", "columns": ["metric", "baseline_pct", "threshold_pp", "alpha", "power", "control_required", "treatment_required"], "rows": [
                {"metric": "精确 D7 提升", "baseline_pct": registry["baseline_rate"]*100, "threshold_pp": registry["mde"]*100, "alpha": registry["alpha"], "power": registry["power"], "control_required": plan["primary_control_required"], "treatment_required": plan["primary_treatment_required"]},
                {"metric": "负反馈非劣围栏", "baseline_pct": registry["negative_baseline"]*100, "threshold_pp": registry["negative_margin"]*100, "alpha": registry["guardrail_alpha"], "power": registry["power"], "control_required": plan["guardrail_control_required"], "treatment_required": plan["guardrail_treatment_required"]}]},
            {"id": "experiment-change-log", "title": "配置变更轨迹", "columns": ["changed_at", "field", "old_value", "new_value", "material"], "rows": changes},
        ]
        output["charts"] = [{"id": "experiment-allocation", "title": "分配人数与预注册期望", "type": "bar", "x_key": "group", "y_keys": ["actual_users", "expected_users"], "unit": "人", "evidence_ids": ["experiment-groups", "experiment-registry"], "data": [
            {"group": "对照组", "actual_users": n0, "expected_users": srm["expected_control"]}, {"group": "处理组", "actual_users": n1, "expected_users": srm["expected_treatment"]}]}]
        output["findings"].append({"kind": "fact", "text": f"入组窗口 {registry['start_date']} 至 {registry['end_date']}，数据完整截至 {registry['snapshot_date']}；共 {quality['assigned_users']} 名分配用户，{quality['immature_users']} 名尚未完成观察。", "evidence_ids": ["experiment-registry", "experiment-quality"]})
        failed_quality = [item for item in output["checks"] if item["id"] != "maturity" and item["passed"] is False]
        if failed_quality:
            reason = "；".join(item["label"] for item in failed_quality)
            output.update(status="invalid_data", summary=f"实验数据不满足评审前提：{reason}。人数与原始计数仅供核查，暂停效应结论。")
            return _decision(output, "invalid_data", "数据需修复", reason, "定位分配、身份、配置或采集异常；保留修复记录，按原分配清单回填并重跑。")
        if not output["checks"][-1]["passed"]:
            output.update(status="waiting_for_maturity", summary=f"尚有 {quality['immature_users']} 名用户未完成预注册观察窗口，不能把未观测结果计为 0 或剔除后发布总体结论。")
            return _decision(output, "waiting_for_maturity", "等待成熟", output["summary"], f"等待最后入组用户的 D7 完整结束；最早数据完整日为 {(last+timedelta(days=7)).isoformat()}，补齐后复查。")
        if not n0 or not n1 or not srm["approximation_valid"]:
            output.update(status="insufficient_data", summary="没有足够的两组分配用户进行效应及 SRM 近似检验。")
            return _decision(output, "insufficient_evidence", "证据不足", output["summary"], "核对入组流量；保持预注册目标，在独立批准的后续实验中补充样本。")
        primary = rate_difference(arms["control"]["retained_users"], n0, arms["treatment"]["retained_users"], n1, registry["alpha"])
        guardrail = rate_difference(arms["control"]["negative_users"], n0, arms["treatment"]["negative_users"], n1, 2*registry["guardrail_alpha"])
        guardrail.update(noninferiority_margin_pp=registry["negative_margin"]*100, one_sided_confidence=1-registry["guardrail_alpha"], noninferior=guardrail["ci_high_pp"] < registry["negative_margin"]*100,
                         harm_exceeds_margin=guardrail["ci_low_pp"] >= registry["negative_margin"]*100)
        output["experiment_statistics"].update(primary=primary, guardrail=guardrail, inference_valid=True)
        enough = n0 >= plan["control_required"] and n1 >= plan["treatment_required"]
        _check(output, "planned_sample", "达到设计样本", enough, f"对照≥{plan['control_required']}、处理≥{plan['treatment_required']}；由 MDE/功效和围栏共同规划", f"对照 {n0} / 处理 {n1}", ["experiment-registry", "experiment-groups"])
        _check(output, "primary_effect", "主要指标与业务门槛", primary["ci_low_pp"] >= registry["min_business_lift"]*100,
               f"D7 差异双侧 {(1-registry['alpha'])*100:g}% 区间下界≥{registry['min_business_lift']*100:g} pp", f"[{primary['ci_low_pp']:.3f}, {primary['ci_high_pp']:.3f}] pp", ["experiment-registry", "experiment-groups"])
        _check(output, "negative_feedback", "负反馈非劣围栏", guardrail["noninferior"],
               f"负反馈差异单侧 {(1-registry['guardrail_alpha'])*100:g}% 上界<{registry['negative_margin']*100:g} pp", f"上界 {guardrail['ci_high_pp']:.3f} pp", ["experiment-registry", "experiment-groups"])
        for identifier, label, value, unit in (("experiment_d7_lift_pp", "D7 绝对提升", primary["lift_pp"], "百分点"), ("negative_feedback_lift_pp", "负反馈绝对变化", guardrail["lift_pp"], "百分点")):
            output["kpis"].append({"id": identifier, "label": label, "value": round(value, 4), "unit": unit, "evidence_ids": ["experiment-groups"]})
        effect_rows = [{"metric": label, **{key: round(value, 6) if isinstance(value, float) else value for key, value in stats.items()}}
                       for label, stats in (("精确 D7 留存", primary), ("24h 负反馈", guardrail))]
        output["tables"].append({"id": "experiment-effects", "title": "效应、相对变化与区间", "columns": ["metric", "control_rate_pct", "treatment_rate_pct", "lift_pp", "relative_lift_pct", "ci_low_pp", "ci_high_pp", "p_value"], "rows": effect_rows})
        output["charts"].append({"id": "experiment-outcomes", "title": "ITT 用户结果：留存与负反馈", "type": "bar", "x_key": "group", "y_keys": ["d7_retention_pct", "negative_feedback_pct"], "unit": "%", "evidence_ids": ["experiment-groups"], "data": [
            {"group": "对照组", "d7_retention_pct": primary["control_rate_pct"], "negative_feedback_pct": guardrail["control_rate_pct"]},
            {"group": "处理组", "d7_retention_pct": primary["treatment_rate_pct"], "negative_feedback_pct": guardrail["treatment_rate_pct"]}]})
        fact = f"处理组精确 D7 留存 {primary['treatment_rate_pct']:.2f}%，对照组 {primary['control_rate_pct']:.2f}%；差异 {primary['lift_pp']:+.2f} pp，{primary['confidence_level']*100:g}% 区间 [{primary['ci_low_pp']:.2f}, {primary['ci_high_pp']:.2f}] pp。"
        output["findings"].append({"kind": "fact", "text": fact, "evidence_ids": ["experiment-groups", "experiment-registry"]})
        output["findings"].append({"kind": "fact", "text": f"负反馈差异 {guardrail['lift_pp']:+.2f} pp，非劣评审上界 {guardrail['ci_high_pp']:.2f} pp，预注册容忍界值 {registry['negative_margin']*100:.2f} pp。", "evidence_ids": ["experiment-groups", "experiment-registry"]})
        if guardrail["harm_exceeds_margin"] or primary["ci_high_pp"] < 0:
            code, label = "stop_or_adjust", "建议停止或调整"
            reason = "负反馈恶化已超过预设界值。" if guardrail["harm_exceeds_margin"] else "主要指标区间整体为负。"
            action = "复查体验机制和受影响人群，调整方案后另登记实验；不进入放量。"
        elif not enough:
            code, label, reason = "insufficient_evidence", "证据不足", "未达到预注册 MDE 与围栏所需样本量。"
            action = "报告区间与不确定性；不根据当前 p 值临时改指标、延长实验或宣布成功。按新实验计划补充证据。"
        elif not guardrail["noninferior"]:
            code, label, reason = "insufficient_evidence", "证据不足", "尚未证明负反馈差异低于非劣界值；未显著恶化不等于安全。"
            action = "评估可接受风险与围栏样本规划；保持现有发布范围，形成独立的后续验证计划。"
        elif primary["ci_low_pp"] < registry["min_business_lift"]*100:
            code, label, reason = "insufficient_evidence", "证据不足", "主要效应区间尚未达到预注册最低业务提升要求。"
            action = "保留当前不确定性与收益范围，结合机制证据调整方案，登记后续实验。"
        else:
            code, label, reason = "review_for_gradual_rollout", "满足预设条件，建议人工评审灰度", "质量、成熟、设计样本、业务效应区间与体验非劣围栏均通过。"
            action = "由业务与实验负责人复核适用人群、实施成本和发布风险，再决定灰度范围及回滚阈值；本系统不执行推全。"
        output["summary"] = fact + label + "。" + reason
        return _decision(output, code, label, reason, action)
