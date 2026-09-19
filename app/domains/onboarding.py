"""Evidence-first onboarding diagnosis from reproducible anonymous event data.

Metric semantics live in onboarding_metrics.json. All displayed business numbers
come from parameterized SQLite queries or explicit arithmetic over those results.
The three snapshots share events: arrival timestamps, source manifests, and a
continuous partition watermark determine what is actually available in each one.
"""
from __future__ import annotations

import copy
import hashlib
import json
import random
import re
import sqlite3
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .growth import symmetric_decomposition

REGISTRY_PATH = Path(__file__).resolve().parents[1] / "data" / "onboarding_metrics.json"
REGISTRY = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
METRICS = {item["id"]: item for item in REGISTRY["metrics"]}
VERSION = REGISTRY["version"]
SOURCE = REGISTRY["data_source"]
SEED = 710919
DATA_START, DATA_END = "2026-06-01", "2026-09-18"
CHANNELS = ("organic", "paid_search", "social", "referral")
DEVICES = ("android", "ios", "web")
APP_VERSIONS = ("1.8.0", "1.9.0")
LABELS = {"organic": "自然流量", "paid_search": "付费搜索", "social": "社交投放", "referral": "好友推荐", "android": "Android", "ios": "iOS", "web": "网页"}
MAIN_METRICS = ("new_user_retention_d1", "new_user_retention_d7", "return_within_days_1_7", "activated_24h")
SCENARIOS = {
    "business_drop": {"label": "完整数据：新用户留存诊断", "as_of": "2026-09-19 08:00:00"},
    "late_data": {"label": "延迟快照：先检查数据质量", "as_of": "2026-09-07 08:00:00"},
    "recovered": {"label": "回填快照：数据完整后重算", "as_of": "2026-09-08 12:00:00"},
}
DEFAULT_DATES = {"start": "2026-08-24", "end": "2026-08-30", "compare_start": "2026-08-17", "compare_end": "2026-08-23"}
EVENT_COLUMNS = ["event_id", "user_id", "event_name", "event_time", "ingested_at", "event_date", "channel", "device", "app_version", "batch_id", "schema_version", "request_id", "duration_seconds"]


def _contract(metric_id: str) -> dict:
    return {**copy.deepcopy(METRICS[metric_id]), "version": VERSION, "timezone": REGISTRY["timezone"], "data_source": SOURCE, "dimensions": list(REGISTRY["allowed_dimensions"])}


def metadata() -> dict:
    return {
        "id": "onboarding", "name": "新用户增长与留存决策", "description": "基于事件查询核对留存变化、数据完整性与用户路径，形成包含证据和验证事项的决策备忘录。",
        "data_source": SOURCE, "data_range": {"start": DATA_START, "end": DATA_END},
        "default_request": {"domain": "onboarding", "task": "diagnose", **DEFAULT_DATES, "filters": {"metric": "new_user_retention_d7", "scenario": "business_drop"}},
        "metrics": [_contract(key) for key in METRICS],
        "filters": {
            "channel": [{"value": x, "label": LABELS[x]} for x in CHANNELS],
            "device": [{"value": x, "label": LABELS[x]} for x in DEVICES],
            "app_version": [{"value": x, "label": x} for x in APP_VERSIONS],
            "metric": [{"value": x, "label": METRICS[x]["name"]} for x in MAIN_METRICS],
            "scenario": [{"value": x, "label": value["label"]} for x, value in SCENARIOS.items()],
        },
        "scenarios": copy.deepcopy(SCENARIOS), "funnel_contract": copy.deepcopy(REGISTRY["funnel"]),
        "tables": [
            {"name": "onboarding_users", "description": "稳定匿名 UID 的注册 cohort；每用户一行，不跨设备合并", "columns": ["user_id", "signup_at", "signup_date", "channel", "device", "app_version"]},
            {"name": "onboarding_events", "description": "去重后的产品事件，含源端事件时间与入库时间；查询必须带 ingested_at 截止条件", "columns": EVENT_COLUMNS},
            {"name": "onboarding_ingest_batches", "description": "源端日 × 设备批次清单，用于可见事件计数校验与连续水位；不含诊断答案", "columns": ["batch_id", "event_date", "device", "expected_events", "manifest_available_at"]},
            {"name": "onboarding_changes", "description": "版本和投放变更日志，供诊断检索；同期变更不等于因果证据", "columns": ["change_id", "change_at", "device", "app_version", "change_type", "description"]},
            {"name": "onboarding_snapshots", "description": "演示快照的可见时间截止，三种场景查询同一份事件", "columns": ["scenario", "as_of"]},
        ],
        "examples": [
            {"question": "最近两个成熟注册周的精确 D7 为什么变化？结合渠道、端、版本与注册后漏斗，给出下一步验证。", "task": "diagnose"},
            {"question": "检查注册后 24 小时有序漏斗，定位本期最大的转化损失。", "task": "funnel"},
            {"question": "检查延迟快照的留存数据质量，列出批次缺口与恢复条件。", "task": "quality", "filters": {"scenario": "late_data"}},
            {"question": "生成新用户增长决策备忘录，列出核验事实、验证事项、后续行动及复查条件。", "task": "report"},
        ],
    }


def _stamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def build_database(path: Path) -> None:
    """Create only this domain, once per registry/generator version."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    signature = VERSION + ":generator.3:" + hashlib.sha256(REGISTRY_PATH.read_bytes()).hexdigest()[:12]
    with sqlite3.connect(path, timeout=60) as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS onboarding_users (
          user_id TEXT PRIMARY KEY, signup_at TEXT NOT NULL, signup_date TEXT NOT NULL,
          channel TEXT NOT NULL, device TEXT NOT NULL, app_version TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS onboarding_events (
          event_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES onboarding_users(user_id),
          event_name TEXT NOT NULL, event_time TEXT NOT NULL, ingested_at TEXT NOT NULL,
          event_date TEXT NOT NULL, channel TEXT NOT NULL, device TEXT NOT NULL,
          app_version TEXT NOT NULL, batch_id TEXT NOT NULL,
          schema_version TEXT NOT NULL, request_id TEXT, duration_seconds INTEGER);
        CREATE TABLE IF NOT EXISTS onboarding_ingest_batches (
          batch_id TEXT PRIMARY KEY, event_date TEXT NOT NULL, device TEXT NOT NULL,
          expected_events INTEGER NOT NULL, manifest_available_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS onboarding_changes (
          change_id TEXT PRIMARY KEY, change_at TEXT NOT NULL, device TEXT,
          app_version TEXT, change_type TEXT NOT NULL, description TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS onboarding_snapshots (scenario TEXT PRIMARY KEY, as_of TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS onboarding_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS onboarding_users_signup ON onboarding_users(signup_date, channel, device);
        CREATE INDEX IF NOT EXISTS onboarding_events_user_name ON onboarding_events(user_id, event_name, event_time, ingested_at);
        CREATE INDEX IF NOT EXISTS onboarding_events_batch ON onboarding_events(batch_id, ingested_at);
        CREATE INDEX IF NOT EXISTS onboarding_events_day ON onboarding_events(event_date, device, ingested_at);
        """)
        if con.execute("SELECT value FROM onboarding_metadata WHERE key='signature'").fetchone() == (signature,):
            return
        for table in ("onboarding_events", "onboarding_users", "onboarding_ingest_batches", "onboarding_changes", "onboarding_snapshots", "onboarding_metadata"):
            con.execute("DELETE FROM " + table)
        rng = random.Random(SEED)
        source_end = datetime.fromisoformat(DATA_END) + timedelta(days=1)
        users, events = [], []
        batch_counts: dict[tuple[str, str], int] = {}
        uid_counter = 0

        def add_event(uid: str, name: str, at: datetime, channel: str, device: str, version: str, request_id: str | None = None, duration: int | None = None) -> None:
            if at >= source_end:
                return
            event_day = at.date().isoformat()
            arrived = at + timedelta(seconds=rng.randrange(30, 600))
            # Arrival behavior belongs to raw data generation, never a diagnosis label in the schema.
            if device == "android" and "2026-09-04" <= event_day <= "2026-09-06":
                arrived = datetime(2026, 9, 8, 10) + timedelta(seconds=rng.randrange(0, 3600))
            batch = event_day + ":" + device
            batch_counts[(event_day, device)] = batch_counts.get((event_day, device), 0) + 1
            events.append((f"e{len(events)+1:08d}", uid, name, _stamp(at), _stamp(arrived), event_day, channel, device, version, batch, "1.0", request_id, duration))

        day = date.fromisoformat(DATA_START)
        while day.isoformat() <= DATA_END:
            shifted = day >= date(2026, 8, 24)
            channel_weights = (.23, .45, .24, .08) if shifted else (.45, .22, .20, .13)
            device_weights = (.58, .30, .12) if shifted else (.45, .40, .15)
            for _ in range(110 + rng.randrange(31)):
                uid_counter += 1
                uid = f"u{uid_counter:06d}"
                channel = rng.choices(CHANNELS, channel_weights)[0]
                device = rng.choices(DEVICES, device_weights)[0]
                new_version_share = .88 if shifted else (.18 if day >= date(2026, 8, 17) else 0)
                version = "1.9.0" if device == "android" and rng.random() < new_version_share else "1.8.0"
                at = datetime.combine(day, datetime.min.time()) + timedelta(seconds=rng.randrange(86400))
                users.append((uid, _stamp(at), day.isoformat(), channel, device, version))
                add_event(uid, "signup", at, channel, device, version)
                progressed = rng.random() < (.88 if version == "1.9.0" else .93)
                feed_ok = False
                activated = False
                if progressed:
                    add_event(uid, "onboarding_started", at + timedelta(seconds=30), channel, device, version)
                    complete = at + timedelta(minutes=rng.randrange(2, 45))
                    if rng.random() < .035:
                        complete += timedelta(hours=25)  # Conversion outside 24 h must not count.
                    if rng.random() < .94:
                        add_event(uid, "onboarding_completed", complete, channel, device, version)
                        requested = complete + timedelta(seconds=20)
                        rid = uid + ":feed:1"
                        add_event(uid, "feed_requested", requested, channel, device, version, rid)
                        feed_ok = rng.random() < (.57 if version == "1.9.0" else .94)
                        feed_at = requested + timedelta(seconds=rng.randrange(2, 16))
                        add_event(uid, "first_feed_success" if feed_ok else "first_feed_failure", feed_at, channel, device, version, rid)
                        if feed_ok:
                            duration = rng.randrange(61, 210) if rng.random() < .74 else rng.randrange(5, 59)
                            consumed = feed_at + timedelta(seconds=duration)
                            add_event(uid, "content_consumed", consumed, channel, device, version, duration=duration)
                            activated = duration >= REGISTRY["activation_duration_seconds"] and consumed < at + timedelta(hours=24)
                        if rng.random() < (.10 if version == "1.9.0" else .035):
                            add_event(uid, "negative_feedback", feed_at + timedelta(minutes=1), channel, device, version)
                propensity = {"organic": .61, "paid_search": .46, "social": .41, "referral": .68}[channel]
                propensity += .11 if activated else -.035
                propensity += {"android": -.01, "ios": .02, "web": -.01}[device]
                if version == "1.9.0" and not feed_ok:
                    propensity -= .12
                returning = rng.random() < max(.05, min(.95, propensity))
                if returning:
                    for offset in range(1, 31):
                        chance = {1: .65, 2: .47, 3: .40, 4: .35, 5: .33, 6: .30, 7: .45}.get(offset, .14)
                        if rng.random() < chance:
                            active_at = datetime.combine(day + timedelta(days=offset), datetime.min.time()) + timedelta(seconds=rng.randrange(86400))
                            add_event(uid, "app_active", active_at, channel, device, version)
            day += timedelta(days=1)
        con.executemany("INSERT INTO onboarding_users VALUES (?,?,?,?,?,?)", users)
        con.executemany("INSERT INTO onboarding_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", events)
        batches = []
        day = date.fromisoformat(DATA_START)
        while day.isoformat() <= DATA_END:
            for device in DEVICES:
                batches.append((day.isoformat() + ":" + device, day.isoformat(), device, batch_counts.get((day.isoformat(), device), 0), _stamp(datetime.combine(day + timedelta(days=1), datetime.min.time()) + timedelta(hours=1))))
            day += timedelta(days=1)
        con.executemany("INSERT INTO onboarding_ingest_batches VALUES (?,?,?,?,?)", batches)
        con.executemany("INSERT INTO onboarding_snapshots VALUES (?,?)", [(key, value["as_of"]) for key, value in SCENARIOS.items()])
        con.executemany("INSERT INTO onboarding_changes VALUES (?,?,?,?,?,?)", [
            ("rel-0817", "2026-08-17 00:00:00", "android", "1.9.0", "release", "Android 1.9.0 开始分阶段发布，调整新用户引导与首屏推荐接口。"),
            ("rel-0824", "2026-08-24 00:00:00", "android", "1.9.0", "release", "Android 1.9.0 扩大发布覆盖；需要结合版本、端和用户结构评估效果。"),
            ("acq-0824", "2026-08-24 00:00:00", None, None, "acquisition", "获客预算分配调整，提高付费搜索与社交渠道的配置比例。"),
            ("ops-0904", "2026-09-04 00:00:00", "android", None, "pipeline", "Android 事件导入队列维护，运行状态以源端批次清单和到达记录为准。"),
        ])
        con.executemany("INSERT INTO onboarding_metadata VALUES (?,?)", [("signature", signature), ("version", VERSION), ("seed", str(SEED)), ("timezone", REGISTRY["timezone"])])


def _base(metric_id: str = "new_user_retention_d7") -> dict:
    return {"status": "completed", "title": "新用户增长诊断", "summary": "", "metric_contract": _contract(metric_id), "kpis": [], "tables": [], "charts": [], "findings": [], "evidence": [], "trace": [], "limitations": [SOURCE, "渠道、端、版本与漏斗的拆解是描述性证据；版本同期变化不能直接证明因果。", "身份范围限定为稳定匿名 UID，不跨设备合并。"], "suggestions": [], "plan": [], "hypotheses": []}


def _stop(status: str, message: str) -> dict:
    out = _base()
    out.update(status=status, title="需要确认分析范围" if status == "needs_clarification" else "当前范围不足以分析", summary=message)
    out["trace"] = [{"tool": "validate_request", "status": status, "description": message}]
    out["suggestions"] = ["使用 2026-08-24—08-30 对比 08-17—08-23，选择精确 D7 与完整数据场景。"]
    if status == "needs_clarification":
        out["clarification"] = {"question": message, "options": out["suggestions"]}
    return out


def _date(value: Any, label: str) -> date:
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError(f"{label} 必须是 YYYY-MM-DD 格式。")
    try:
        result = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} 不是有效日期。") from exc
    if result.isoformat() != value:
        raise ValueError(f"{label} 必须是 YYYY-MM-DD 格式。")
    return result


def _validate(request: dict) -> tuple[dict, str, str, str]:
    if not isinstance(request, dict):
        raise ValueError("请求必须是分析参数对象。")
    task = request.get("task") or "diagnose"
    if task not in ("diagnose", "funnel", "report", "quality"):
        raise ValueError("新用户域支持 diagnose、funnel、report、quality；实验评审请使用实验域。")
    for pair in (("start", "end"), ("compare_start", "compare_end")):
        if bool(request.get(pair[0])) != bool(request.get(pair[1])):
            raise ValueError("开始日期和结束日期必须成对提供。")
    start, end = (_date(request.get(key) or DEFAULT_DATES[key], key) for key in ("start", "end"))
    if request.get("compare_start"):
        old_start, old_end = (_date(request[key], key) for key in ("compare_start", "compare_end"))
    else:
        try:
            old_end = start - timedelta(days=1)
            old_start = old_end - (end - start)
        except OverflowError as exc:
            raise ValueError("默认对比期超出可表示日期范围；请提供有效的当前期和对比期。") from exc
    if start > end or old_start > old_end:
        raise ValueError("开始日期不能晚于结束日期。")
    if not (old_end < start or old_start > end):
        raise ValueError("两期 cohort 不能重叠。")
    if max((end-start).days, (old_end-old_start).days) > 365:
        raise ValueError("每期最多 366 个自然日。")
    filters = request.get("filters") if request.get("filters") is not None else {}
    if not isinstance(filters, dict):
        raise ValueError("filters 必须是筛选对象。")
    allowed = {"channel": CHANNELS, "device": DEVICES, "app_version": APP_VERSIONS}
    if set(filters) - set(allowed) - {"metric", "scenario"}:
        raise ValueError("仅支持 channel、device、app_version、metric、scenario；不支持个人标识或任意 SQL 筛选。")
    question = request.get("question") if request.get("question") is not None else ""
    if not isinstance(question, str):
        raise ValueError("question 必须是文本。")
    mentioned, excluded = set(), set()
    patterns = {
        "new_user_retention_d1": r"(?<![A-Za-z0-9])D\s*1(?![0-9])|精确第[一1]日|精确次日留存",
        "new_user_retention_d7": r"(?<![A-Za-z0-9])D\s*7(?![0-9])|精确第[七7]日",
        "return_within_days_1_7": r"[1一][—–\-至到][7七]\s*[天日]|[7七]\s*[天日]内(?:任意)?(?:回访|留存)|次[7七]日内",
        "activated_24h": r"24\s*(?:小时|h)[^，,。;；]*?(?:激活|有序漏斗)",
    }
    # A nearby explicit exclusion is not a request for that metric. This is a
    # bounded demo-language rule, not a claim to parse unrestricted language.
    negation = re.compile(r"(?:不是|而非|不要(?:分析|计算|使用|看|用)?|不(?:分析|计算|使用|看|用)|别(?:分析|计算|看|用)|排除)\s*(?:(?:精确|注册后|新用户|用户|有序|窗口|指标|口径|次|第|的)\s*)*$")
    for identifier, pattern in patterns.items():
        for match in re.finditer(pattern, question, re.I):
            clause_prefix = re.split(r"[，,。;；]", question[:match.start()])[-1]
            (excluded if negation.search(clause_prefix) else mentioned).add(identifier)
    if len(mentioned) > 1 and re.search(r"还是|或者|哪个口径|二选一", question):
        raise ValueError("问题同时提出多个待选口径，请先选择精确留存、窗口回访或 24 小时激活中的主要指标。")
    explicit_metric = filters.get("metric")
    if explicit_metric is not None and not isinstance(explicit_metric, str):
        raise ValueError("metric 必须是一个指标 ID 文本。")
    if explicit_metric and (explicit_metric in excluded or mentioned and explicit_metric not in mentioned):
        raise ValueError("问题中明确的指标与 metric 筛选不一致，请先统一精确留存、窗口回访或 24 小时激活口径。")
    if not explicit_metric and excluded and not mentioned:
        raise ValueError("问题排除了一个或多个口径，但未确定主要指标；请选择精确留存、窗口回访或 24 小时激活。")
    metric = explicit_metric or (next(iter(mentioned)) if len(mentioned) == 1 else ("activated_24h" if task == "funnel" else "new_user_retention_d7"))
    if metric in excluded:
        raise ValueError("候选主要指标与问题中的排除口径冲突，请先明确本次采用的指标。")
    scenario = filters.get("scenario") or "business_drop"
    if not isinstance(metric, str) or metric not in MAIN_METRICS:
        raise ValueError("metric 必须选择精确 D1、精确 D7、次 1—7 日回访或 24 小时有序激活的指标 ID。")
    if not isinstance(scenario, str) or scenario not in SCENARIOS:
        raise ValueError("scenario 必须是 business_drop、late_data 或 recovered。")
    params = {"start": start.isoformat(), "end": end.isoformat(), "compare_start": old_start.isoformat(), "compare_end": old_end.isoformat(), "as_of": SCENARIOS[scenario]["as_of"], "activation_seconds": REGISTRY["activation_duration_seconds"]}
    fragments = []
    for field, values in allowed.items():
        if field not in filters:
            continue
        selected = filters[field] if isinstance(filters[field], list) else [filters[field]]
        if not selected or any(not isinstance(item, str) or item not in values for item in selected):
            raise ValueError(f"{field} 筛选无效；允许 {', '.join(values)}。")
        keys = []
        for index, item in enumerate(dict.fromkeys(selected)):
            key = f"filter_{field}_{index}"
            params[key] = item
            keys.append(":" + key)
        fragments.append(f" AND u.{field} IN ({','.join(keys)})")
    return params, "".join(fragments), task, metric


def _query(con: sqlite3.Connection, out: dict, identifier: str, label: str, sql: str, params: dict) -> list[dict]:
    began = time.perf_counter()
    rows = [dict(row) for row in con.execute(sql, params)]
    out["evidence"].append({"id": identifier, "label": label, "sql": sql, "parameters": dict(params), "rows": rows, "source": SOURCE, "metric_version": VERSION, "data_as_of": params.get("as_of")})
    out["trace"].append({"tool": "query_metric", "status": "completed", "description": label, "duration_ms": round(1000 * (time.perf_counter()-began), 2)})
    return rows


def _cohort_start(filters: str) -> str:
    return f"""WITH periods AS (
      SELECT 'current' AS period, :start AS start_date, :end AS end_date
      UNION ALL SELECT 'previous', :compare_start, :compare_end
    ), users AS (
      SELECT p.period, u.* FROM onboarding_users u JOIN periods p
        ON u.signup_date BETWEEN p.start_date AND p.end_date
      WHERE u.signup_at < :as_of{filters}
    ) """


def _cohort_sql(filters: str) -> str:
    return _cohort_start(filters).rstrip() + """, requests AS (
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
    ) """


def _rate(row: dict, column: str = "successes", denominator: str = "users") -> float | None:
    return 100 * row[column] / row[denominator] if row[denominator] and row[column] is not None else None


def _r(value: float | None, precision: int = 3) -> float | None:
    return None if value is None else round(value, precision)


def _required_end(metric_id: str, cohort_end: str, latest_signup: str) -> str:
    rule = METRICS[metric_id]["maturity"]
    if rule["type"] == "hours":
        return _stamp(datetime.fromisoformat(latest_signup) + timedelta(hours=rule["hours"]))
    return _stamp(datetime.fromisoformat(cohort_end) + timedelta(days=rule["days"]+1))


def _quality(con: sqlite3.Connection, out: dict, params: dict, filters: str, metric_id: str) -> dict:
    cohort = _query(con, out, "onboarding-cohort-scope", "注册 cohort 范围、人数与最晚注册时间", _cohort_start(filters) + "SELECT period, COUNT(*) AS users, MIN(signup_date) AS first_signup_date, MAX(signup_date) AS last_signup_date, MAX(signup_at) AS latest_signup_at FROM users GROUP BY period ORDER BY period", params)
    relevant_devices = _query(con, out, "onboarding-cohort-devices", "当前筛选实际涉及的设备分区", _cohort_start(filters) + "SELECT DISTINCT device FROM users ORDER BY device", params)
    if len(cohort) != 2:
        return {"status": "insufficient_data", "as_of": params["as_of"], "checks": [], "affected_metrics": [metric_id], "message": "当前筛选下至少一期没有注册用户；不能比较或把空队列记作 0%。"}
    requested_end = max(params["end"], params["compare_end"])
    required = _required_end(metric_id, requested_end, max(row["latest_signup_at"] for row in cohort))
    # The funnel is returned alongside the main result, so it must also be mature.
    funnel_required = _required_end("activated_24h", requested_end, max(row["latest_signup_at"] for row in cohort))
    required = max(required, funnel_required)
    devices = [row["device"] for row in relevant_devices]
    batch_params = dict(params, batch_start=DATA_START, batch_end=min(DATA_END, (datetime.fromisoformat(params["as_of"])-timedelta(days=1)).date().isoformat()))
    placeholders = []
    for i, device in enumerate(devices):
        batch_params[f"quality_device_{i}"] = device
        placeholders.append(f":quality_device_{i}")
    device_clause = ",".join(placeholders)
    batch_sql = f"""SELECT b.event_date,b.device,b.expected_events,COUNT(e.event_id) AS observed_events,
      MAX(e.ingested_at) AS latest_arrival
      FROM onboarding_ingest_batches b LEFT JOIN onboarding_events e
        ON e.batch_id=b.batch_id AND e.ingested_at<=:as_of
      WHERE b.event_date BETWEEN :batch_start AND :batch_end
        AND b.manifest_available_at<=:as_of AND b.device IN ({device_clause})
      GROUP BY b.batch_id ORDER BY b.event_date,b.device"""
    batches = _query(con, out, "onboarding-batch-watermark", "源端批次清单与快照可见事件，计算连续设备水位", batch_sql, batch_params)
    watermarks = {}
    for device in devices:
        indexed = {row["event_date"]: row for row in batches if row["device"] == device}
        cursor = date.fromisoformat(DATA_START)
        last_day = date.fromisoformat(batch_params["batch_end"])
        while cursor <= last_day:
            row = indexed.get(cursor.isoformat())
            if row is None or row["expected_events"] != row["observed_events"]:
                break
            cursor += timedelta(days=1)
        watermarks[device] = cursor.isoformat() + " 00:00:00"
    watermark = min(watermarks.values())
    observation_mature = required <= params["as_of"]
    watermark_ok = required <= watermark
    relevant_start = min(params["start"], params["compare_start"])
    relevant_end = (datetime.fromisoformat(required)-timedelta(seconds=1)).date().isoformat()
    affected_batches = [row for row in batches if relevant_start <= row["event_date"] <= relevant_end and row["observed_events"] != row["expected_events"]]
    validation_cache = {}

    def validate_window(boundary: str, evidence_id: str) -> dict:
        # Side metrics have different observed event windows. A short-window pass
        # cannot authorize a longer-window metric, even when both are mature.
        window_end = (datetime.fromisoformat(boundary)-timedelta(seconds=1)).date().isoformat()
        if window_end in validation_cache:
            return validation_cache[window_end]
        validation_params = dict(batch_params, relevant_start=relevant_start,
                                 relevant_end=window_end)
        supported = REGISTRY["accepted_event_schema_versions"]
        for i, version in enumerate(supported):
            validation_params[f"schema_{i}"] = version
        schema_slots = ",".join(f":schema_{i}" for i in range(len(supported)))
        rows = _query(con, out, evidence_id, "窗口内事件版本、时间/日期、用户归属与批次一致性", f"""SELECT COUNT(*) AS visible_events,
          COALESCE(SUM(CASE WHEN e.schema_version NOT IN ({schema_slots}) THEN 1 ELSE 0 END),0) AS unsupported_schema_events,
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
            AND (u.device IN ({device_clause}) OR e.device IN ({device_clause})
              OR b.device IN ({device_clause}))
            AND e.ingested_at<=:as_of""", validation_params)
        validation_cache[window_end] = {**rows[0], "evidence_id": evidence_id}
        return validation_cache[window_end]

    validation = validate_window(required, "onboarding-event-validation")
    schema_ok = validation["unsupported_schema_events"] == 0
    relationship_ok = validation["invalid_event_relationships"] == 0 and validation["duplicate_event_ids"] == 0
    status = "passed" if observation_mature and watermark_ok and schema_ok and relationship_ok else ("insufficient_data" if not observation_mature else "blocked")
    checks = [
        {"id": "observation_mature", "name": "完整观察窗口", "status": "passed" if observation_mature else "blocked", "observed": params["as_of"], "expected": required, "detail": "快照时间必须覆盖完整自然日或实际注册时间 + 24 小时；不得删除未成熟用户后沿用原请求结论。", "evidence_ids": ["onboarding-cohort-scope"]},
        {"id": "continuous_watermark", "name": "连续数据水位", "status": "passed" if watermark_ok else "blocked", "observed": watermark, "expected": required, "detail": "水位为所有相关设备分区已完整到达事件时间的排他上界；缺一日不能跳过。", "evidence_ids": ["onboarding-batch-watermark"]},
        {"id": "source_manifest", "name": "源端清单计数", "status": "passed" if not affected_batches and watermark_ok else "blocked", "observed": len(affected_batches), "expected": 0, "detail": "按已知源端批次 expected_events 比较已到达去重事件；缺少清单也无法通过连续水位。", "evidence_ids": ["onboarding-batch-watermark"]},
        {"id": "schema_version", "name": "事件版本兼容", "status": "passed" if schema_ok else "blocked", "observed": validation["unsupported_schema_events"], "expected": 0, "detail": "只接受版本化指标合同支持的埋点 schema。", "evidence_ids": ["onboarding-event-validation"]},
        {"id": "event_integrity", "name": "事件关系与幂等性", "status": "passed" if relationship_ok else "blocked", "observed": validation["invalid_event_relationships"] + validation["duplicate_event_ids"], "expected": 0, "detail": "检查匿名用户归属、事件时间/自然日、批次日期/设备、事件先后与 event_id 唯一性。", "evidence_ids": ["onboarding-event-validation"]},
    ]
    per_metric = []
    latest_signup = max(row["latest_signup_at"] for row in cohort)
    for identifier in MAIN_METRICS:
        boundary = _required_end(identifier, requested_end, latest_signup)
        metric_validation = validate_window(boundary, "onboarding-event-validation-" + identifier)
        metric_schema_ok = metric_validation["unsupported_schema_events"] == 0
        metric_integrity_ok = metric_validation["invalid_event_relationships"] == 0 and metric_validation["duplicate_event_ids"] == 0
        per_metric.append({"metric_id": identifier, "metric": METRICS[identifier]["name"],
                           "required_until": boundary, "mature": boundary <= params["as_of"],
                           "watermark_complete": boundary <= watermark,
                           "schema_valid": metric_schema_ok, "event_integrity_valid": metric_integrity_ok,
                           "unsupported_schema_events": metric_validation["unsupported_schema_events"],
                           "invalid_event_relationships": metric_validation["invalid_event_relationships"],
                           "evidence_ids": [metric_validation["evidence_id"], "onboarding-batch-watermark"],
                           "available": boundary <= min(watermark, params["as_of"]) and metric_schema_ok and metric_integrity_ok})
    message = "所选主指标及有序漏斗质量检查通过；旁路指标按各自窗口单独判断可用性。" if status == "passed" else ("观察窗口尚未完整结束；未成熟值不记作 0。" if status == "insufficient_data" else "相关事件分区不完整或口径校验失败，暂停受影响业务结论，先完成回填与重算。")
    return {"status": status, "as_of": params["as_of"], "watermark": watermark, "watermarks_by_device": watermarks, "required_until": required, "checks": checks, "affected_batches": affected_batches, "affected_metrics": [row["metric_id"] for row in per_metric if not row["available"]], "metric_availability": per_metric, "message": message, "cohorts": cohort, "provenance": "源端日 × 设备批次清单 + 可见 ingested_at；质量门禁按相关设备分区保守检查，不证明未知源端漏数不存在。"}


def analyze(request: dict, db_path: Path) -> dict:
    try:
        params, filters, task, metric_id = _validate(request)
    except (ValueError, TypeError) as exc:
        return _stop("needs_clarification", str(exc))
    if min(params["start"], params["compare_start"]) < DATA_START or max(params["end"], params["compare_end"]) > DATA_END:
        return _stop("insufficient_data", f"完整请求必须落在注册数据 {DATA_START} 至 {DATA_END} 内，不能静默截断范围。")
    out = _base(metric_id)
    out["title"] = {"diagnose": "新用户留存诊断", "funnel": "注册后 24 小时有序漏斗", "quality": "增长数据质量检查", "report": "新用户增长决策备忘录"}[task]
    out["metric_contract"].update(current_period=[params["start"], params["end"]], previous_period=[params["compare_start"], params["compare_end"]], data_as_of=params["as_of"])
    out["plan"] = [
        {"step": 1, "tool": "get_metric_contract", "purpose": "冻结指标、cohort、时区和完整观察窗口", "status": "completed"},
        {"step": 2, "tool": "check_data_quality", "purpose": "验证实际到达批次、连续水位和事件版本", "status": "pending"},
        {"step": 3, "tool": "query_cohort_metrics", "purpose": "用同一 cohort 计算精确留存和有序漏斗", "status": "pending"},
        {"step": 4, "tool": "decompose_change", "purpose": "区分结构变化、分层表现与版本关联", "status": "pending"},
        {"step": 5, "tool": "build_evidence_report", "purpose": "汇总证据、验证事项、行动和复查条件", "status": "pending"},
    ]
    with sqlite3.connect(f"file:{Path(db_path).resolve()}?mode=ro", uri=True, timeout=30) as con:
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA query_only=ON")
        quality = _quality(con, out, params, filters, metric_id)
        out["data_quality"] = quality
        out["plan"][1]["status"] = "completed" if quality["status"] == "passed" else "blocked"
        out["metric_contract"]["watermark"] = quality.get("watermark")
        out["tables"].append({"id": "quality-checks", "title": "数据可用性门禁", "columns": ["name", "status", "observed", "expected", "detail"], "rows": quality["checks"]})
        if quality.get("metric_availability"):
            out["tables"].append({"id": "metric-maturity", "title": "不同指标分别判断成熟与可用性", "columns": ["metric", "required_until", "mature", "watermark_complete", "schema_valid", "event_integrity_valid", "available"], "rows": quality["metric_availability"]})
        if quality["status"] != "passed":
            out["status"] = "insufficient_data" if quality["status"] == "insufficient_data" else "data_quality_blocked"
            out["summary"] = quality["message"]
            out["decision"] = {"status": "wait_for_maturity" if out["status"] == "insufficient_data" else "repair_data", "label": "等待完整观察窗口" if out["status"] == "insufficient_data" else "先修复数据，暂停经营判断", "actions": ["核对相关源端批次清单与导入日志。", "保持原 cohort 和指标口径，回填后重新执行同一查询。"], "review_trigger": quality.get("required_until", "两期均有完整 cohort")}
            refs = [e["id"] for e in out["evidence"]]
            out["findings"] = [{"kind": "fact", "text": out["summary"], "evidence_ids": refs}, {"kind": "action", "text": "没有通过门禁的留存值不显示为 0，也不支持调整获客预算或产品放量。", "evidence_ids": refs}]
            if quality.get("affected_batches"):
                out["tables"].append({"id": "incomplete-batches", "title": "需要回填的分区", "columns": ["event_date", "device", "expected_events", "observed_events", "latest_arrival"], "rows": quality["affected_batches"]})
            out["suggestions"] = ["在回填快照 recovered 中保持原分析日期，核对水位和批次完整性后重算；数据可用不等于留存回升。", "如分析较早 cohort 或已完成的 D1，请更换指标后重新进行质量检查。"]
            return out
        if task == "quality":
            out["summary"] = quality["message"] + f" 当前连续水位 {quality['watermark']}，查询快照 {quality['as_of']}。"
            out["findings"] = [{"kind": "fact", "text": out["summary"], "evidence_ids": ["onboarding-batch-watermark", "onboarding-event-validation", "onboarding-cohort-scope"]}]
            out["decision"] = {"status": "data_ready", "label": "可进入业务分析", "actions": ["保持该快照，执行留存与漏斗诊断。"], "review_trigger": "新增批次、口径变更或下一观察日"}
            out["suggestions"] = ["执行 diagnose 或 report，检查业务变化与下一步。"]
            return out
        _diagnose(con, out, params, filters, metric_id, task)
    return out


def _diagnose(con: sqlite3.Connection, out: dict, params: dict, filters: str, metric_id: str, task: str) -> None:
    column = METRICS[metric_id]["calculation"]["success_column"]
    cte = _cohort_sql(filters)
    quality_ready = {row["metric_id"]: row["available"] for row in out["data_quality"]["metric_availability"]}
    sums = {"d1": "SUM(d1)" if quality_ready["new_user_retention_d1"] else "NULL",
            "d7": "SUM(d7)" if quality_ready["new_user_retention_d7"] else "NULL",
            "within7": "SUM(within7)" if quality_ready["return_within_days_1_7"] else "NULL"}
    totals = _query(con, out, "onboarding-totals", "两期 cohort 指标；未成熟或缺数的旁路指标保持 NULL", cte + f"""SELECT period,COUNT(*) AS users,
      SUM(registered) AS registered,SUM(onboarded) AS onboarded,SUM(feed_success) AS feed_success,
      SUM(activated) AS activated,{sums["d1"]} AS d1,{sums["d7"]} AS d7,{sums["within7"]} AS within7,
      SUM(feed_requested) AS feed_requested,
      CASE WHEN SUM(feed_result_unresolved)=0 THEN COALESCE(SUM(feed_failed),0) ELSE NULL END AS feed_failed,
      SUM(feed_result_unresolved) AS feed_result_unresolved,
      SUM(negative_feedback) AS negative_feedback FROM cohort GROUP BY period ORDER BY period""", params)
    periods = {row["period"]: row for row in totals}
    previous, current = periods["previous"], periods["current"]
    r0, r1 = _rate(previous, column), _rate(current, column)
    delta = r1-r0
    strata = _query(con, out, "onboarding-strata", "渠道 × 端的两期联合分层", cte + f"SELECT period,channel,device,COUNT(*) AS users,SUM({column}) AS retained_users FROM cohort GROUP BY period,channel,device ORDER BY period,channel,device", params)
    decomposition = symmetric_decomposition([row for row in strata if row["period"] == "previous"], [row for row in strata if row["period"] == "current"])
    mix = sum(row["mix_pp"] for row in decomposition)
    performance = sum(row["performance_pp"] for row in decomposition)
    daily = _query(con, out, "onboarding-daily", "按注册 cohort 日计算的主指标趋势", cte + f"SELECT period,signup_date,COUNT(*) AS users,SUM({column}) AS successes,100.0*SUM({column})/COUNT(*) AS metric_pct FROM cohort GROUP BY period,signup_date ORDER BY signup_date", params)
    slices = _query(con, out, "onboarding-version-slices", "端 × 版本的留存、漏斗和首次请求失败", cte + f"""SELECT period,device,app_version,COUNT(*) AS users,SUM({column}) AS successes,
      SUM(onboarded) AS onboarded,SUM(feed_success) AS feed_success,SUM(activated) AS activated,
      SUM(feed_requested) AS feed_requested,
      CASE WHEN SUM(feed_result_unresolved)=0 THEN COALESCE(SUM(feed_failed),0) ELSE NULL END AS feed_failed,
      SUM(feed_result_unresolved) AS feed_result_unresolved,SUM(negative_feedback) AS negative_feedback
      FROM cohort GROUP BY period,device,app_version ORDER BY period,device,app_version""", params)
    active_event_names = METRICS["daily_active_users"]["calculation"]["events"]
    active_params = dict(params)
    for i, name in enumerate(active_event_names):
        active_params[f"active_event_{i}"] = name
    active_slots = ",".join(f":active_event_{i}" for i in range(len(active_event_names)))
    daily_active = _query(con, out, "onboarding-daily-active", "日活跃背景：全注册样本中每天的合格事件去重用户，不跨日相加", f"""SELECT e.event_date,
      COUNT(DISTINCT e.user_id) AS active_users FROM onboarding_events e
      JOIN onboarding_users u ON u.user_id=e.user_id
      WHERE e.event_name IN ({active_slots}) AND e.ingested_at<=:as_of
        AND (e.event_date BETWEEN :start AND :end OR e.event_date BETWEEN :compare_start AND :compare_end)
        {filters} GROUP BY e.event_date ORDER BY e.event_date""", active_params)
    changes = _query(con, out, "onboarding-change-log", "分析时段附近的可见发布与获客变更", "SELECT change_id,change_at,device,app_version,change_type,description FROM onboarding_changes WHERE change_at>=datetime(:compare_start,'-1 day') AND change_at<datetime(:end,'+2 days') AND change_at<=:as_of ORDER BY change_at,change_id", params)
    metric_rows = []
    for identifier in MAIN_METRICS:
        key = METRICS[identifier]["calculation"]["success_column"]
        available = quality_ready[identifier]
        before = _rate(previous, key) if available else None
        after = _rate(current, key) if available else None
        metric_rows.append({"metric_id": identifier, "metric": METRICS[identifier]["name"], "previous_users": previous["users"], "current_users": current["users"], "previous_successes": previous[key] if available else None, "current_successes": current[key] if available else None, "previous_pct": _r(before), "current_pct": _r(after), "delta_pp": _r(after-before) if available else None, "status": "available" if available else "not_available"})
    out["summary"] = f"本期 {METRICS[metric_id]['name']} {r1:.2f}%（{current[column]}/{current['users']}），对比期 {r0:.2f}%（{previous[column]}/{previous['users']}），变化 {delta:+.2f} 个百分点。渠道 × 端对称分解中，结构贡献 {mix:+.2f}、组内表现贡献 {performance:+.2f} 个百分点；质量检查已通过。"
    out["kpis"] = [
        {"id": metric_id, "label": METRICS[metric_id]["name"], "value": _r(r1), "previous": _r(r0), "delta": _r(delta), "unit": "%"},
        {"id": "new_registered_users", "label": "本期成熟注册用户", "value": current["users"], "previous": previous["users"], "delta": current["users"]-previous["users"], "unit": "人"},
        {"id": "mix_pp", "label": "结构变化贡献", "value": _r(mix), "unit": "百分点"},
        {"id": "performance_pp", "label": "组内表现贡献", "value": _r(performance), "unit": "百分点"},
    ]
    out["tables"].extend([
        {"id": "cohort-metrics", "title": "相同 cohort，不同留存窗口分别计算", "columns": ["metric", "previous_users", "current_users", "previous_successes", "current_successes", "previous_pct", "current_pct", "delta_pp", "status"], "rows": metric_rows},
        {"id": "onboarding-decomposition", "title": "渠道 × 端对称分解（百分点）", "columns": ["segment", "previous_users", "current_users", "previous_rate_pct", "current_rate_pct", "mix_pp", "performance_pp", "total_pp"], "rows": [{key: _r(value) if isinstance(value, float) else value for key,value in row.items()} for row in decomposition]},
    ])
    version_rows = [{**row, "segment": LABELS[row["device"]] + " / " + row["app_version"], "metric_pct": _r(_rate(row)), "activation_pct": _r(_rate(row, "activated")), "first_feed_failure_pct": _r(_rate(row, "feed_failed", "feed_requested")), "negative_feedback_pct": _r(_rate(row, "negative_feedback"))} for row in slices]
    out["tables"].extend([
        {"id": "version-slices", "title": "版本关联与体验围栏", "columns": ["period", "segment", "users", "metric_pct", "activation_pct", "first_feed_failure_pct", "feed_result_unresolved", "negative_feedback_pct"], "rows": version_rows},
        {"id": "change-log", "title": "同期变更记录", "columns": ["change_at", "device", "app_version", "change_type", "description"], "rows": changes},
    ])
    funnel_steps = []
    for index, step in enumerate(REGISTRY["funnel"]["steps"]):
        key = step["id"]
        prev_key = REGISTRY["funnel"]["steps"][max(0,index-1)]["id"]
        after_step = _rate(current, key, prev_key) if index else 100.0
        before_step = _rate(previous, key, prev_key) if index else 100.0
        funnel_steps.append({"step": step["name"], "step_id": key, "previous_users": previous[key], "current_users": current[key], "previous_cohort_pct": _r(_rate(previous, key)), "current_cohort_pct": _r(_rate(current, key)), "previous_step_pct": _r(before_step), "current_step_pct": _r(after_step), "step_delta_pp": _r(after_step-before_step) if after_step is not None and before_step is not None else None, "current_lost_users": current[prev_key]-current[key] if index else 0})
    loss_step = max(funnel_steps[1:], key=lambda row: row["current_lost_users"])
    worsened = min((row for row in funnel_steps[1:] if row["step_delta_pp"] is not None), key=lambda row: row["step_delta_pp"], default=None)
    out["funnel"] = {"window": REGISTRY["funnel"]["interval"], "maturity": "实际 signup_at + 24h 已被连续数据水位覆盖", "ordering": REGISTRY["funnel"]["ordering"], "steps": funnel_steps, "largest_drop": loss_step, "largest_deterioration": worsened, "evidence_ids": ["onboarding-totals"]}
    out["tables"].append({"id": "ordered-funnel", "title": "注册后 24 小时有序漏斗", "columns": ["step", "previous_users", "current_users", "previous_cohort_pct", "current_cohort_pct", "previous_step_pct", "current_step_pct", "step_delta_pp", "current_lost_users"], "rows": funnel_steps})
    out["charts"] = [
        {"id": "onboarding-dau", "title": "日活跃背景（全注册样本，逐日去重）", "type": "line", "x_key": "event_date", "y_keys": ["active_users"], "unit": "人", "data": daily_active},
        {"id": "onboarding-trend", "title": METRICS[metric_id]["name"] + "：成熟 cohort 趋势", "type": "line", "x_key": "signup_date", "y_keys": ["metric_pct"], "unit": "%", "data": daily},
        {"id": "onboarding-contribution", "title": "总体变化的算术分解", "type": "bar", "x_key": "component", "y_keys": ["contribution_pp"], "unit": "百分点", "data": [{"component": "结构变化", "contribution_pp": _r(mix)}, {"component": "组内表现", "contribution_pp": _r(performance)}]},
        {"id": "onboarding-funnel", "title": "同 cohort 的 24 小时路径", "type": "bar", "x_key": "step", "y_keys": ["previous_cohort_pct", "current_cohort_pct"], "unit": "%", "data": funnel_steps},
        {"id": "onboarding-versions", "title": "本期端 × 版本主指标", "type": "bar", "x_key": "segment", "y_keys": ["metric_pct", "activation_pct"], "unit": "%", "data": [row for row in version_rows if row["period"] == "current"]},
    ]
    most_material = max(decomposition, key=lambda row: abs(row["total_pp"]))
    quality_ids = ["onboarding-batch-watermark", "onboarding-event-validation"]
    out["findings"] = [
        {"kind": "fact", "text": out["summary"], "evidence_ids": ["onboarding-totals", "onboarding-strata", *quality_ids]},
        {"kind": "fact", "text": f"绝对贡献最大的联合分层为 {most_material['segment']}，算术贡献 {most_material['total_pp']:+.2f} pp；不能把渠道和设备单独分解再相加。", "evidence_ids": ["onboarding-strata"]},
        {"kind": "fact", "text": f"本期有序漏斗在「{loss_step['step']}」这一步流失人数最多：{loss_step['current_lost_users']} 人。人数损失与环节转化率变化需要分别观察。", "evidence_ids": ["onboarding-totals"]},
    ]
    if worsened:
        out["findings"].append({"kind": "fact", "text": f"相对前期，环节转化率变化最小的步骤为「{worsened['step']}」，变化 {worsened['step_delta_pp']:+.3f} pp。", "evidence_ids": ["onboarding-totals"]})
    current_versions = [row for row in version_rows if row["period"] == "current" and row["first_feed_failure_pct"] is not None]
    focus_version = max(current_versions, key=lambda row: row["first_feed_failure_pct"], default={"segment": "当前筛选的人群"})["segment"]
    out["hypotheses"] = [
        {"id": "mix", "title": "验证事项：核对获客结构与组内变化", "status": "descriptive_support" if abs(mix) >= .1 else "limited_support", "supporting_evidence_ids": ["onboarding-strata", "onboarding-change-log"], "observation": f"对称分解的结构项为 {mix:+.3f} pp。", "counter_evidence": f"联合分层的组内表现项为 {performance:+.3f} pp；总体变化包含结构项和组内表现项，不能全部归入结构项。", "next_test": "对比预算和渠道质量记录，并以固定渠道 × 端权重追踪后续成熟 cohort；不将重新加权当作因果估计。"},
        {"id": "experience", "title": "验证事项：核对首屏路径与回访的关系", "status": "needs_validation", "supporting_evidence_ids": ["onboarding-version-slices", "onboarding-totals", "onboarding-change-log"], "observation": f"本期激活 {_rate(current,'activated'):.2f}%，前期 {_rate(previous,'activated'):.2f}%；端与版本切片使用相同注册队列。", "counter_evidence": "版本未随机分配，且发布与渠道结构同期变化；现有结果未识别各因素的独立因果效应。", "next_test": f"优先核对当前筛选下「{focus_version}」的首屏请求错误与性能日志，预注册候选路径修复实验；D7 为主要结果，24h 激活为早期信号，负反馈与性能为围栏。"},
        {"id": "ingestion", "title": "验证事项：核对到数缺口", "status": "not_supported_in_scope", "supporting_evidence_ids": quality_ids, "observation": "本次主指标与有序漏斗涉及的连续水位、源端清单及事件版本通过检查；旁路指标独立判断。", "counter_evidence": "现有已知批次未发现缺口；源端清单自身未知漏报仍不在可验证范围内。", "next_test": "下一批次继续核对源端计数、到达时间和 schema；新分区不能沿用旧快照的通过状态。"},
    ]
    out["findings"].extend([
        {"kind": "hypothesis", "text": "验证事项包括投放来源、产品路径和源端完整性；版本与留存的同期关联不构成因果结论，需通过随机实验或补充记录核验。", "evidence_ids": ["onboarding-strata", "onboarding-version-slices", "onboarding-change-log", *quality_ids]},
        {"kind": "action", "text": f"复核 {most_material['segment']} 的来源和人群构成，并核对「{focus_version}」的首屏请求日志；保持原指标口径，以独立预注册实验评审候选干预。", "evidence_ids": ["onboarding-strata", "onboarding-totals", "onboarding-version-slices"]},
    ])
    out["decision"] = {"status": "investigate_then_experiment", "label": "核查用户路径，登记干预验证" if delta < 0 else "保持观察，验证变化是否可复现", "actions": [f"复核 {most_material['segment']} 的来源、端与版本关联。", f"检查「{loss_step['step']}」路径的首屏请求和用户反馈。", "预注册候选干预、D7 主要结果、样本量与负反馈/性能围栏；完成观察后评审效应。"], "review_trigger": "下一批完整成熟 cohort；如进入实验，等待预注册观察窗口与样本条件", "owner": "待分配", "evidence_ids": ["onboarding-strata", "onboarding-version-slices", "onboarding-totals"]}
    out["plan"][2:5] = [{**row, "status": "completed"} for row in out["plan"][2:5]]
    out["trace"].append({"tool": "decompose_change", "status": "completed", "description": f"结构项 + 表现项 = {mix+performance:+.8f} pp，总体变化 {delta:+.8f} pp；闭合误差 {abs(mix+performance-delta):.10f} pp。"})
    if out["data_quality"]["affected_metrics"]:
        out["limitations"].append("旁路指标因各自的成熟、水位或事件校验未通过而留空：" + "、".join(METRICS[key]["name"] for key in out["data_quality"]["affected_metrics"]) + "。")
    if current["feed_result_unresolved"] or previous["feed_result_unresolved"]:
        out["limitations"].append("存在首次 Feed 请求结果缺失、冲突或 request_id 无法唯一关联；受影响分组的首次请求失败率保持不可用，不记作 0%。")
    out["limitations"].extend(["精确 D1、精确 D7 和次 1—7 日回访使用不同指标 ID；未成熟或不完整的旁路指标显示不可用。", "24h 漏斗保持同一 cohort 与事件顺序，D1/D7 是并列后续结果；跨日活跃人数不能直接相加为去重用户。", "分层缺失时沿用该分层可观察期的比率作为分解约定，该部分只记入结构项，不估计缺失期表现。", "诊断仅提供描述性变化与关联证据；未执行真实干预，未观测经营增量或收益。"])
    if (date.fromisoformat(params["end"])-date.fromisoformat(params["start"])) != (date.fromisoformat(params["compare_end"])-date.fromisoformat(params["compare_start"])):
        out["limitations"].append("两期长度不相同：比率可以描述性比较，注册人数差不能直接作为增长结论；还需核对星期构成。")
    if min(current["users"],previous["users"]) < 200:
        out["limitations"].append("至少一期少于 200 人；切片与趋势不稳定，仅用于探索，不据此判断变化可复现。")
    out["suggestions"] = ["核对延迟快照 late_data 的缺失批次和水位；缺数期间暂停受影响指标的经营判断。", "用回填快照 recovered 重算原日期队列；分别复核数据完整性与留存变化。", "按 Android 或版本筛选，核对路径关联；对候选修复进入独立实验评审。"]
