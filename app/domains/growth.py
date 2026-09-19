"""Deterministic growth analysis over a reproducible, synthetic SQLite dataset.

All facts are computed from parameterized SQL; no language model generates numbers.
The symmetric decomposition and normal-approximation statistics are implemented
here from their documented formulas, without copying the previous portfolio.
"""
from __future__ import annotations

import math
import random
import sqlite3
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

SEED = 71
DATA_START = "2026-07-06"
SNAPSHOT = "2026-09-06"
MATURE_END = "2026-08-30"
EXPERIMENT_START = "2026-08-17"
EXPERIMENT_END = "2026-08-30"
METRIC_VERSION = "growth.v1.0"
SOURCE = "固定种子 71 的合成增长数据；非真实企业经营结果"
CHANNELS = ("organic", "paid_search", "social", "referral")
DEVICES = ("android", "ios", "web")
LABELS = {"organic": "自然流量", "paid_search": "付费搜索", "social": "社交投放", "referral": "好友推荐", "android": "Android", "ios": "iOS", "web": "网页"}
CONTRACT = {
    "id": "retained_within_next_7_days", "name": "次 7 日内留存率",
    "version": METRIC_VERSION,
    "numerator": "注册后第 1—7 个自然日内，至少有一次活动的成熟队列用户数",
    "denominator": "注册日期 + 7 日不晚于数据快照日的去重注册用户数",
    "grain": "用户", "window": "(注册日, 注册日 + 7 日]", "unit": "%",
    "timezone": "Asia/Shanghai；数据以本地自然日存储",
    "snapshot_date": SNAPSHOT, "latest_mature_cohort": MATURE_END,
    "exclusions": ["注册当日活动", "未完成 7 日观察的队列"],
    "not_equivalent_to": "精确 D7 留存（仅注册后第 7 日活动）",
    "data_source": SOURCE,
}


def metadata() -> dict:
    return {
        "id": "growth", "name": "增长诊断与自动周报", "description": "确认留存口径，查询成熟队列，分解结构和表现，复盘随机实验并交付证据。",
        "data_source": SOURCE, "data_range": {"start": DATA_START, "end": SNAPSHOT},
        "default_request": {"domain": "growth", "task": "diagnose", "start": "2026-08-24", "end": "2026-08-30", "compare_start": "2026-08-17", "compare_end": "2026-08-23", "filters": {}},
        "metrics": [CONTRACT.copy(), {"id": "experiment_lift_pp", "name": "实验次 7 日内留存绝对提升", "unit": "百分点", "definition": "处理组留存率 − 对照组留存率；按注册用户随机分配，按分配组 ITT 分析"}],
        "tables": [
            {"name": "growth_users", "description": "每用户一行的注册、获客维度和随机实验分组", "columns": ["user_id", "signup_date", "channel", "device", "experiment_arm", "incentive_cost", "revenue_7d"]},
            {"name": "growth_activity", "description": "用户自然日活动；同用户同日去重", "columns": ["user_id", "activity_date"]},
        ],
        "filters": {"channel": [{"value": x, "label": LABELS[x]} for x in CHANNELS], "device": [{"value": x, "label": LABELS[x]} for x in DEVICES]},
        "examples": [
            {"question": "比较最近两周已完成观察的新增队列，次 7 日内留存为什么变化？按渠道和设备检查。", "task": "diagnose"},
            {"question": "复盘 8 月 17—30 日的随机增长实验，检查提升、置信区间、SRM 和成本门槛。", "task": "experiment"},
            {"question": "生成增长周报，展示变化、分层证据、验证事项和后续行动。", "task": "report"},
        ],
    }


def build_database(path: Path) -> None:
    """Idempotently create this domain only; leave other domains untouched."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    with sqlite3.connect(path) as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS growth_users (
                user_id INTEGER PRIMARY KEY, signup_date TEXT NOT NULL,
                channel TEXT NOT NULL, device TEXT NOT NULL,
                experiment_arm TEXT,
                incentive_cost REAL NOT NULL, revenue_7d REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS growth_activity (
                user_id INTEGER NOT NULL REFERENCES growth_users(user_id),
                activity_date TEXT NOT NULL, PRIMARY KEY(user_id, activity_date)
            );
            CREATE TABLE IF NOT EXISTS growth_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS growth_users_date ON growth_users(signup_date);
            CREATE INDEX IF NOT EXISTS growth_activity_user_date ON growth_activity(user_id, activity_date);
        """)
        if con.execute("SELECT value FROM growth_metadata WHERE key = 'version'").fetchone() == (METRIC_VERSION,):
            return
        con.execute("DELETE FROM growth_activity")
        con.execute("DELETE FROM growth_users")
        users, activities = [], []
        day = date.fromisoformat(DATA_START)
        snapshot = date.fromisoformat(SNAPSHOT)
        user_id = 0
        while day <= snapshot:
            shifted = day >= date(2026, 8, 24)
            weights = (0.20, 0.47, 0.24, 0.09) if shifted else (0.42, 0.24, 0.17, 0.17)
            for _ in range(145 + rng.randrange(31)):
                user_id += 1
                channel = rng.choices(CHANNELS, weights=weights)[0]
                device = rng.choices(DEVICES, weights=(0.57, 0.30, 0.13) if shifted else (0.43, 0.40, 0.17))[0]
                arm = rng.choice(("control", "treatment")) if EXPERIMENT_START <= day.isoformat() <= EXPERIMENT_END else None
                probability = {"organic": .36, "paid_search": .24, "social": .21, "referral": .42}[channel]
                probability += {"android": -.035, "ios": .035, "web": -.01}[device]
                if shifted and channel == "paid_search" and device == "android":
                    probability -= .065
                if arm == "treatment":
                    probability += .055
                returned = rng.random() < probability
                cost = round({"organic": .0, "paid_search": .75, "social": .5, "referral": .2}[channel] + (.18 if arm == "treatment" else 0), 2)
                revenue = round(rng.uniform(1.5, 6.5), 2) if returned and rng.random() < .55 else 0.0
                users.append((user_id, day.isoformat(), channel, device, arm, cost, revenue))
                activities.append((user_id, day.isoformat()))
                if returned:
                    for offset in rng.sample(range(1, 8), rng.randint(1, 3)):
                        active_day = day + timedelta(days=offset)
                        if active_day <= snapshot:
                            activities.append((user_id, active_day.isoformat()))
            day += timedelta(days=1)
        con.executemany("INSERT INTO growth_users VALUES (?,?,?,?,?,?,?)", users)
        con.executemany("INSERT INTO growth_activity VALUES (?,?)", activities)
        con.executemany("INSERT OR REPLACE INTO growth_metadata VALUES (?,?)", [("version", METRIC_VERSION), ("snapshot", SNAPSHOT), ("seed", str(SEED))])


def _base() -> dict:
    return {"status": "completed", "title": "增长诊断", "summary": "", "metric_contract": CONTRACT.copy(), "kpis": [], "tables": [], "charts": [], "findings": [], "evidence": [], "trace": [], "limitations": [SOURCE, "分层分解是描述性归因，不能证明渠道或设备变化导致留存变化。"], "suggestions": []}


def _stop(status: str, message: str, options: list[str] | None = None) -> dict:
    output = _base()
    output.update(status=status, title="需要确认分析范围" if status == "needs_clarification" else "当前范围不足以分析", summary=message)
    output["trace"] = [{"tool": "validate_request", "status": status, "description": message}]
    output["suggestions"] = options or [f"使用成熟队列 2026-08-24 至 {MATURE_END}，对比 2026-08-17 至 2026-08-23。"]
    if status == "needs_clarification":
        output["clarification"] = {"question": message, "options": output["suggestions"]}
    return output


def _parse_date(value: Any, name: str) -> date:
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError(f"{name} 必须是 YYYY-MM-DD 格式的日期。")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} 不是有效日期。") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{name} 必须是 YYYY-MM-DD 格式的日期。")
    return parsed


def _dates(request: dict, task: str) -> dict:
    start, end = ((EXPERIMENT_START, EXPERIMENT_END) if task == "experiment" else ("2026-08-24", "2026-08-30"))
    explicit = any(request.get(key) not in (None, "") for key in ("start", "end"))
    if explicit:
        if not request.get("start") or not request.get("end"):
            raise ValueError("请同时提供本期开始和结束日期。")
        start, end = request["start"], request["end"]
    first, last = _parse_date(start, "start"), _parse_date(end, "end")
    if first > last:
        raise ValueError("本期开始日期不能晚于结束日期。")
    if (last - first).days > 365:
        raise ValueError("单次分析最多覆盖 366 个自然日。")
    params = {"start": start, "end": end, "snapshot": SNAPSHOT}
    comparison = any(request.get(key) not in (None, "") for key in ("compare_start", "compare_end"))
    if task == "experiment":
        if comparison:
            raise ValueError("实验按同一时段的随机分组比较，不接受前后两期对比日期；请清空对比日期。")
    else:
        if comparison:
            if not request.get("compare_start") or not request.get("compare_end"):
                raise ValueError("请同时提供对比期开始和结束日期。")
            previous_start = _parse_date(request["compare_start"], "compare_start")
            previous_end = _parse_date(request["compare_end"], "compare_end")
        else:
            previous_end = first - timedelta(days=1)
            previous_start = previous_end - (last - first)
        if previous_start > previous_end:
            raise ValueError("对比期开始日期不能晚于结束日期。")
        if not (previous_end < first or previous_start > last):
            raise ValueError("两期日期不能重叠；重叠用户不能作为独立队列比较。")
        if (previous_end - previous_start).days > 365:
            raise ValueError("对比期最多覆盖 366 个自然日。")
        params.update(compare_start=previous_start.isoformat(), compare_end=previous_end.isoformat())
    return params


def _filters(request: dict, params: dict) -> str:
    filters = request.get("filters")
    if filters is None:
        filters = {}
    if not isinstance(filters, dict):
        raise ValueError("filters 必须是渠道或设备筛选对象。")
    fragments = []
    for field, value in filters.items():
        if field not in ("channel", "device"):
            raise ValueError(f"不支持筛选字段 {field}；允许 channel、device。")
        values = value if isinstance(value, list) else [value]
        allowed = CHANNELS if field == "channel" else DEVICES
        if not values or any(not isinstance(item, str) or item not in allowed for item in values):
            raise ValueError(f"{field} 筛选值无效；允许 {', '.join(allowed)}。")
        placeholders = []
        for index, item in enumerate(dict.fromkeys(values)):
            key = f"filter_{field}_{index}"
            params[key] = item
            placeholders.append(":" + key)
        fragments.append(f" AND u.{field} IN ({','.join(placeholders)})")
    return "".join(fragments)


def _cohort_sql(filters: str, comparison: bool = True) -> str:
    periods = "SELECT 'current' AS period, :start AS start_date, :end AS end_date"
    if comparison:
        periods += " UNION ALL SELECT 'previous', :compare_start, :compare_end"
    return f"""WITH periods AS ({periods}), cohort AS (
        SELECT p.period, u.user_id, u.signup_date, u.channel, u.device,
            u.experiment_arm, u.incentive_cost, u.revenue_7d,
            EXISTS(SELECT 1 FROM growth_activity a
                WHERE a.user_id = u.user_id
                  AND a.activity_date > u.signup_date
                  AND a.activity_date <= date(u.signup_date, '+7 days')) AS retained
        FROM growth_users u JOIN periods p
          ON u.signup_date BETWEEN p.start_date AND p.end_date
        WHERE date(u.signup_date, '+7 days') <= :snapshot{filters}
    ) """


def _query(con: sqlite3.Connection, output: dict, evidence_id: str, label: str, sql: str, params: dict) -> list[dict]:
    begin = time.perf_counter()
    rows = [dict(row) for row in con.execute(sql, params).fetchall()]
    output["evidence"].append({"id": evidence_id, "label": label, "sql": sql, "parameters": dict(params), "rows": rows, "source": SOURCE, "metric_version": METRIC_VERSION})
    output["trace"].append({"tool": "query_metric", "status": "completed", "description": label, "duration_ms": round((time.perf_counter() - begin) * 1000, 2)})
    return rows


def _round(value: float, digits: int = 3) -> float:
    return round(value, digits)


def _rate(row: dict) -> float:
    return row["retained_users"] / row["users"] if row["users"] else 0.0


def symmetric_decomposition(previous: list[dict], current: list[dict], keys: tuple[str, ...] = ("channel", "device")) -> list[dict]:
    """Exact two-factor symmetric decomposition in percentage points.

    For strata absent in one period, copy the observed rate to the absent period:
    its change is entirely mix, rather than an invented unobserved performance.
    """
    old = {tuple(row[key] for key in keys): row for row in previous}
    new = {tuple(row[key] for key in keys): row for row in current}
    n0, n1 = sum(row["users"] for row in previous), sum(row["users"] for row in current)
    if not n0 or not n1:
        return []
    result = []
    for group in sorted(set(old) | set(new)):
        before, after = old.get(group), new.get(group)
        p0 = before["users"] / n0 if before else 0.0
        p1 = after["users"] / n1 if after else 0.0
        r0 = _rate(before or after)
        r1 = _rate(after or before)
        mix = (p1 - p0) * (r1 + r0) / 2 * 100
        performance = (r1 - r0) * (p1 + p0) / 2 * 100
        result.append({**dict(zip(keys, group)), "segment": " / ".join(LABELS.get(x, x) for x in group), "previous_users": before["users"] if before else 0, "current_users": after["users"] if after else 0, "previous_share_pct": p0 * 100, "current_share_pct": p1 * 100, "previous_rate_pct": r0 * 100 if before else None, "current_rate_pct": r1 * 100 if after else None, "mix_pp": mix, "performance_pp": performance, "total_pp": mix + performance, "new_or_lost": not (before and after)})
    return sorted(result, key=lambda row: row["total_pp"])


def _diagnose(con: sqlite3.Connection, params: dict, filters: str, task: str) -> dict:
    output = _base()
    output["title"] = "增长自动周报" if task == "report" else "增长留存诊断"
    output["metric_contract"].update(current_period=[params["start"], params["end"]], previous_period=[params["compare_start"], params["compare_end"]])
    cte = _cohort_sql(filters)
    totals = _query(con, output, "growth-totals", "两期成熟用户与留存人数", cte + "SELECT period, COUNT(*) AS users, SUM(retained) AS retained_users FROM cohort GROUP BY period", params)
    by_period = {row["period"]: row for row in totals}
    if not all(period in by_period for period in ("current", "previous")):
        output.update(status="insufficient_data", summary="当前筛选下至少一期没有成熟注册用户，无法比较或分解。")
        output["suggestions"] = ["检查日期是否处于数据范围内，或者移除渠道、设备筛选。"]
        return output
    current, previous = by_period["current"], by_period["previous"]
    r0, r1 = _rate(previous), _rate(current)
    delta = (r1 - r0) * 100
    strata = _query(con, output, "growth-strata", "两期渠道 × 设备成熟留存", cte + "SELECT period, channel, device, COUNT(*) AS users, SUM(retained) AS retained_users FROM cohort GROUP BY period, channel, device ORDER BY period, channel, device", params)
    contributions = symmetric_decomposition([row for row in strata if row["period"] == "previous"], [row for row in strata if row["period"] == "current"])
    mix = sum(row["mix_pp"] for row in contributions)
    performance = sum(row["performance_pp"] for row in contributions)
    daily = _query(con, output, "growth-daily", "按注册日的成熟队列趋势", cte + "SELECT period, signup_date, COUNT(*) AS users, SUM(retained) AS retained_users, ROUND(100.0 * SUM(retained) / COUNT(*), 4) AS retention_pct FROM cohort GROUP BY period, signup_date ORDER BY signup_date", params)
    breakdown = _query(con, output, "growth-dimensions", "渠道及设备单维留存对比", cte + "SELECT period, 'channel' AS dimension, channel AS segment, COUNT(*) AS users, SUM(retained) AS retained_users FROM cohort GROUP BY period, channel UNION ALL SELECT period, 'device', device, COUNT(*), SUM(retained) FROM cohort GROUP BY period, device", params)
    output["kpis"] = [
        {"id": "retention_pct", "label": "本期次 7 日内留存", "value": _round(r1 * 100), "previous": _round(r0 * 100), "delta": _round(delta), "unit": "%"},
        {"id": "mature_users", "label": "本期成熟用户", "value": current["users"], "previous": previous["users"], "delta": current["users"] - previous["users"], "unit": "人"},
        {"id": "mix_pp", "label": "结构变化贡献", "value": _round(mix), "unit": "百分点"},
        {"id": "performance_pp", "label": "组内表现贡献", "value": _round(performance), "unit": "百分点"},
    ]
    output["summary"] = f"{params['start']} 至 {params['end']} 的次 7 日内留存为 {r1 * 100:.2f}%（{current['retained_users']}/{current['users']}），对比 {params['compare_start']} 至 {params['compare_end']} 的 {r0 * 100:.2f}%，变化 {delta:+.2f} 个百分点。对称分解中结构贡献 {mix:+.2f}、组内表现贡献 {performance:+.2f} 个百分点。"
    grouped = {(row["dimension"], row["segment"]): {} for row in breakdown}
    for row in breakdown:
        grouped[(row["dimension"], row["segment"])][row["period"]] = _rate(row) * 100
    dimension_rows = [{"dimension": dimension, "segment": LABELS.get(segment, segment), "previous_pct": values.get("previous"), "current_pct": values.get("current")} for (dimension, segment), values in grouped.items()]
    output["tables"] = [
        {"id": "periods", "title": "两期成熟队列", "columns": ["period", "users", "retained_users", "retention_pct"], "rows": [{**row, "retention_pct": _round(_rate(row) * 100)} for row in totals]},
        {"id": "decomposition", "title": "渠道 × 设备的对称分解（百分点）", "columns": ["segment", "previous_users", "current_users", "previous_rate_pct", "current_rate_pct", "mix_pp", "performance_pp", "total_pp"], "rows": [{key: _round(value) if isinstance(value, float) else value for key, value in row.items()} for row in contributions]},
    ]
    output["charts"] = [
        {"id": "trend", "title": "成熟队列的次 7 日内留存趋势", "type": "line", "x_key": "signup_date", "y_keys": ["retention_pct"], "unit": "%", "data": daily},
        {"id": "contribution", "title": "留存变化来源", "type": "bar", "x_key": "component", "y_keys": ["contribution_pp"], "unit": "百分点", "data": [{"component": "结构变化", "contribution_pp": _round(mix)}, {"component": "组内表现", "contribution_pp": _round(performance)}]},
        {"id": "channel", "title": "分渠道留存率", "type": "bar", "x_key": "segment", "y_keys": ["previous_pct", "current_pct"], "unit": "%", "data": [row for row in dimension_rows if row["dimension"] == "channel"]},
        {"id": "device", "title": "分设备留存率", "type": "bar", "x_key": "segment", "y_keys": ["previous_pct", "current_pct"], "unit": "%", "data": [row for row in dimension_rows if row["dimension"] == "device"]},
    ]
    most_material = max(contributions, key=lambda row: abs(row["total_pp"]))
    output["findings"] = [
        {"kind": "fact", "text": output["summary"], "evidence_ids": ["growth-totals", "growth-strata"]},
        {"kind": "fact", "text": f"按渠道 × 设备共同分层，绝对贡献最大的分层是「{most_material['segment']}」，贡献 {most_material['total_pp']:+.2f} 个百分点；这只是总体变化的算术分解。", "evidence_ids": ["growth-strata"]},
        {"kind": "hypothesis", "text": "验证事项包括投放记录、版本变更与产品路径；当前分层计数只能分解变化，不能确定原因。", "evidence_ids": ["growth-strata", "growth-dimensions"]},
        {"kind": "action", "text": f"先核对「{most_material['segment']}」的获客来源和产品路径，再对候选改进设定随机实验、次 7 日内留存主指标及成本护栏。", "evidence_ids": ["growth-strata"]},
    ]
    output["trace"].append({"tool": "decompose_change", "status": "completed", "description": f"结构 + 表现 = {mix + performance:+.6f} pp；与总体变化的误差 {abs(mix + performance - delta):.9f} pp。"})
    if (date.fromisoformat(params["end"]) - date.fromisoformat(params["start"])) != (date.fromisoformat(params["compare_end"]) - date.fromisoformat(params["compare_start"])):
        output["limitations"].append("两期天数不同；人数差不具备等时长比较条件，需另核对星期构成。留存率仅作描述性比较。")
    if min(current["users"], previous["users"]) < 200:
        output["limitations"].append("至少一期样本少于 200 人；当前结果是描述性比较，不足以稳定判断趋势。")
    if any(row["new_or_lost"] for row in contributions):
        output["limitations"].append("某分层在一期缺失：将该分层观察到的留存率用于缺失期，仅作分解约定，其贡献全计入结构项，未估计不存在的用户表现。")
    output["limitations"].append("渠道和设备分层表存在交叉，不能相加；总变化仅由渠道 × 设备联合分层计算。")
    output["suggestions"] = ["复盘同期随机实验，检查提升是否通过统计与业务门槛。", "更换一个渠道或设备筛选，检查变化是否仍然成立。"]
    if task == "report":
        output["trace"].append({"tool": "render_report", "status": "completed", "description": "报告包含指标口径、四张图表、核验事实、验证事项、后续行动及 SQL 证据。"})
    return output


def _experiment(con: sqlite3.Connection, params: dict, filters: str) -> dict:
    output = _base()
    output["title"] = "增长随机实验复盘"
    output["metric_contract"].update(experiment_period=[params["start"], params["end"]], allocation="注册用户随机 1:1，按分配组进行 ITT 分析", srm_alpha=0.01, min_lift_pp=1.5, max_incremental_cost_per_user=0.35, currency="CNY")
    cte = _cohort_sql(filters, comparison=False)
    groups = _query(con, output, "growth-experiment", "同期随机实验分组、留存与成本", cte + "SELECT experiment_arm AS arm, COUNT(*) AS users, SUM(retained) AS retained_users, AVG(incentive_cost) AS cost_per_user, AVG(revenue_7d) AS revenue_per_user FROM cohort WHERE experiment_arm IS NOT NULL GROUP BY experiment_arm ORDER BY experiment_arm", params)
    arms = {row["arm"]: row for row in groups}
    if not all(arm in arms for arm in ("control", "treatment")):
        output.update(status="insufficient_data", summary="筛选时段内没有同时包含处理组和对照组的成熟实验数据。")
        output["suggestions"] = [f"使用实验注册日期 {EXPERIMENT_START} 至 {EXPERIMENT_END}，或放宽筛选。"]
        return output
    control, treatment = arms["control"], arms["treatment"]
    n0, n1 = control["users"], treatment["users"]
    r0, r1 = _rate(control), _rate(treatment)
    lift = r1 - r0
    se = math.sqrt(r0 * (1 - r0) / n0 + r1 * (1 - r1) / n1)
    low, high = max(-1.0, lift - 1.959963984540054 * se), min(1.0, lift + 1.959963984540054 * se)
    pooled = (control["retained_users"] + treatment["retained_users"]) / (n0 + n1)
    pooled_se = math.sqrt(pooled * (1 - pooled) * (1 / n0 + 1 / n1))
    p_value = math.erfc(abs(lift / pooled_se) / math.sqrt(2)) if pooled_se else (1.0 if lift == 0 else 0.0)
    expected = (n0 + n1) / 2
    chi_square = (n0 - expected) ** 2 / expected + (n1 - expected) ** 2 / expected
    srm_p = math.erfc(math.sqrt(chi_square / 2))
    incremental_cost = treatment["cost_per_user"] - control["cost_per_user"]
    incremental_revenue = treatment["revenue_per_user"] - control["revenue_per_user"]
    enough = min(n0, n1) >= 200 and min(control["retained_users"], treatment["retained_users"], n0 - control["retained_users"], n1 - treatment["retained_users"]) >= 10
    passes = {"sample_size": enough, "srm": srm_p >= 0.01, "statistical": low > 0, "business_lift": lift >= .015, "cost": incremental_cost <= .35}
    decision = "进入人工小流量评审" if all(passes.values()) else "不扩大；先处理未通过的门槛"
    output["kpis"] = [
        {"id": "experiment_lift_pp", "label": "实验绝对提升", "value": _round(lift * 100), "unit": "百分点"},
        {"id": "treatment_retention", "label": "处理组留存", "value": _round(r1 * 100), "previous": _round(r0 * 100), "delta": _round(lift * 100), "unit": "%"},
        {"id": "srm_p", "label": "SRM p 值", "value": round(srm_p, 4), "unit": ""},
        {"id": "incremental_cost", "label": "每用户增量成本", "value": _round(incremental_cost), "unit": "元"},
    ]
    statistics = {"control_users": n0, "treatment_users": n1, "control_rate_pct": r0 * 100, "treatment_rate_pct": r1 * 100, "lift_pp": lift * 100, "ci95_low_pp": low * 100, "ci95_high_pp": high * 100, "p_value": p_value, "srm_chi_square": chi_square, "srm_p_value": srm_p, "incremental_cost_per_user": incremental_cost, "incremental_revenue_per_user": incremental_revenue}
    output["experiment_statistics"] = statistics
    output["decision"] = {"label": decision, "gates": passes}
    output["summary"] = f"处理组留存 {r1 * 100:.2f}%（{treatment['retained_users']}/{n1}），对照组 {r0 * 100:.2f}%（{control['retained_users']}/{n0}），绝对提升 {lift * 100:+.2f} 个百分点，95% 置信区间 [{low * 100:.2f}, {high * 100:.2f}]。{decision}。"
    gate_rows = [
        {"gate": "样本及正态近似前提", "rule": "每组 ≥ 200 人，成功/失败均 ≥ 10", "observed": f"对照 {n0} / 处理 {n1}", "passed": enough},
        {"gate": "样本比例失衡 SRM", "rule": "1:1 分配检验 p ≥ 0.01", "observed": f"p = {srm_p:.6f}", "passed": passes["srm"]},
        {"gate": "统计提升", "rule": "绝对提升 95% CI 下界 > 0 pp", "observed": f"[{low * 100:.3f}, {high * 100:.3f}] pp", "passed": passes["statistical"]},
        {"gate": "业务提升", "rule": "点估计 ≥ 1.5 pp（预设演示门槛）", "observed": f"{lift * 100:.3f} pp", "passed": passes["business_lift"]},
        {"gate": "成本护栏", "rule": "增量激励成本 ≤ 0.35 元/用户", "observed": f"{incremental_cost:.3f} 元/用户", "passed": passes["cost"]},
    ]
    output["tables"] = [
        {"id": "experiment-groups", "title": "随机实验两组结果", "columns": ["arm", "users", "retained_users", "retention_pct", "cost_per_user", "revenue_per_user"], "rows": [{**row, "retention_pct": _round(_rate(row) * 100), "cost_per_user": _round(row["cost_per_user"]), "revenue_per_user": _round(row["revenue_per_user"])} for row in groups]},
        {"id": "experiment-gates", "title": "统计与业务决策门槛", "columns": ["gate", "rule", "observed", "passed"], "rows": gate_rows},
        {"id": "experiment-statistics", "title": "绝对提升与 95% 置信区间", "columns": ["lift_pp", "ci95_low_pp", "ci95_high_pp", "p_value", "srm_p_value"], "rows": [{key: _round(value, 6) for key, value in statistics.items()}]},
    ]
    output["charts"] = [
        {"id": "experiment-retention", "title": "同期随机分组留存", "type": "bar", "x_key": "group", "y_keys": ["retention_pct"], "unit": "%", "data": [{"group": "对照组", "retention_pct": _round(r0 * 100)}, {"group": "处理组", "retention_pct": _round(r1 * 100)}]},
        {"id": "experiment-economics", "title": "每用户激励成本与 7 日收入", "type": "bar", "x_key": "group", "y_keys": ["cost_per_user", "revenue_per_user"], "unit": "元", "data": [{"group": "对照组" if row["arm"] == "control" else "处理组", "cost_per_user": _round(row["cost_per_user"]), "revenue_per_user": _round(row["revenue_per_user"])} for row in groups]},
    ]
    output["findings"] = [
        {"kind": "fact", "text": output["summary"], "evidence_ids": ["growth-experiment"]},
        {"kind": "fact", "text": f"样本分配 SRM p={srm_p:.4f}；每用户增量成本 {incremental_cost:.3f} 元，描述性 7 日增量收入 {incremental_revenue:.3f} 元。收入未做显著性检验，不能据此断言盈利。", "evidence_ids": ["growth-experiment"]},
        {"kind": "action", "text": f"{decision}。在真实业务应用前重新预注册最小可检测效应、样本量、成本与长期价值护栏；本演示门槛不替代业务审批。", "evidence_ids": ["growth-experiment"]},
    ]
    output["limitations"] = [SOURCE, "双侧两比例 z 检验；95% CI 使用未合并标准误的正态近似。小样本或极端概率时不据此放量。", "SRM 使用预设 1:1 分配的卡方检验（1 自由度）；p≥0.01 不是随机化成功的充分证明。", "收入仅覆盖 7 日且不含完整成本；不是 ROI、LTV 或利润。", "点估计超过 1.5 pp 不代表有 95% 把握超过业务门槛。", "模拟随机分配结果仅适用于该样本与观察窗口，不代表真实经营收益。"]
    if filters:
        output["limitations"].append("当前是筛选后的探索性子组实验分析，未做多重比较校正；不能替代预注册的总体实验结论。")
    if params["start"] != EXPERIMENT_START or params["end"] != EXPERIMENT_END:
        output["limitations"].append("当前分析覆盖实验的部分日期或包含非实验日期：仅纳入有随机分组的用户，非实验用户不进入实验分母。")
    if not enough:
        output["status"] = "insufficient_data"
        output["summary"] = "样本未满足预设最小门槛；以下统计只供核查，不支持放量决策。" + output["summary"]
    output["trace"].append({"tool": "evaluate_experiment", "status": "completed", "description": "已计算两比例检验、95% CI、SRM 与五项门槛；所有输入来自 growth-experiment。"})
    output["suggestions"] = ["与无筛选的完整实验窗口结果比较。", "把真实业务的成本、最小可检测效应和长期护栏替换为预注册规则。"]
    return output


def analyze(request: dict, db_path: Path) -> dict:
    if not isinstance(request, dict):
        return _stop("needs_clarification", "分析请求必须是结构化对象。")
    task = request.get("task") or "diagnose"
    if task not in ("diagnose", "experiment", "report"):
        return _stop("needs_clarification", f"增长场景不支持任务 {task}。", ["留存变化诊断", "随机实验复盘", "增长周报"])
    try:
        params = _dates(request, task)
        filters = _filters(request, params)
    except (ValueError, OverflowError) as exc:
        return _stop("needs_clarification", str(exc))
    if any(params[key] > MATURE_END for key in ("end", "compare_end") if key in params):
        return _stop("insufficient_data", f"请求包含未完成 7 日观察或未来日期。快照为 {SNAPSHOT}，成熟注册队列最晚到 {MATURE_END}；不混入未成熟用户。")
    if any(params[key] < DATA_START for key in ("start", "compare_start") if key in params):
        return _stop("insufficient_data", f"请求包含数据覆盖之前的日期。数据从 {DATA_START} 开始，不能以部分覆盖冒充完整期间。")
    if not Path(db_path).exists():
        return _stop("insufficient_data", "增长数据文件尚未初始化，请先运行数据构建。")
    with sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True) as con:
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA query_only = ON")
        return _experiment(con, params, filters) if task == "experiment" else _diagnose(con, params, filters, task)
