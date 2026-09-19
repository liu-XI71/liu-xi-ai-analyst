"""Minimal product telemetry: observed runs and voluntary feedback, never invented users."""
from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from app.config import VAR


def _path(path: Path | None = None) -> Path:
    target = path or VAR / 'telemetry.sqlite3'
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def initialize(path: Path | None = None):
    with sqlite3.connect(_path(path)) as con:
        con.executescript('''
          CREATE TABLE IF NOT EXISTS task_event (
            run_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, domain TEXT NOT NULL,
            mode TEXT NOT NULL, status TEXT NOT NULL, duration_ms REAL NOT NULL,
            tool_calls INTEGER NOT NULL, tool_failures INTEGER NOT NULL,
            input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL,
            feedback_hash TEXT NOT NULL, source TEXT NOT NULL
          );
          CREATE TABLE IF NOT EXISTS task_feedback (
            run_id TEXT PRIMARY KEY REFERENCES task_event(run_id),
            updated_at TEXT NOT NULL, outcome TEXT NOT NULL,
            failure_category TEXT NOT NULL, human_minutes REAL
          );
        ''')
        # Preserve existing deployments. Legacy token totals have no completeness
        # marker and remain unknown until an actual new run records that marker.
        con.execute('BEGIN IMMEDIATE')
        columns = {row[1] for row in con.execute('PRAGMA table_info(task_event)')}
        for name, definition in (
            ('usage_status', "TEXT NOT NULL DEFAULT 'unknown'"),
            ('failure_stage', 'TEXT'), ('failure_type', 'TEXT'),
        ):
            if name not in columns:
                con.execute(f'ALTER TABLE task_event ADD COLUMN {name} {definition}')


def record_run(result: dict, *, path: Path | None = None, source='application') -> str:
    """Return a per-run feedback capability; persist its hash only. No prompt text here."""
    initialize(path)
    token = secrets.token_urlsafe(24)
    trace = result.get('trace', [])
    model_run = result.get('model_run', {})
    usage = model_run.get('usage') or {}
    mode = result.get('mode', 'demo')
    usage_state = model_run.get('usage_status') or ('not_applicable' if mode != 'live' else ('complete' if all(key in usage for key in ('input_tokens', 'output_tokens')) else 'unknown'))
    if usage_state not in {'complete', 'partial', 'unknown', 'not_applicable'}:
        usage_state = 'unknown'
    failure = result.get('failure') or {}
    with sqlite3.connect(_path(path)) as con:
        con.execute('''INSERT INTO task_event
            (run_id,created_at,domain,mode,status,duration_ms,tool_calls,tool_failures,
             input_tokens,output_tokens,feedback_hash,source,usage_status,failure_stage,failure_type)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
            result['run_id'], result.get('created_at', datetime.now(timezone.utc).isoformat()),
            result['domain'], mode, result['status'],
            result.get('duration_ms', 0), len(trace),
            sum(t.get('status') in {'rejected', 'failed', 'error'} for t in trace),
            usage.get('input_tokens', 0), usage.get('output_tokens', 0),
            hashlib.sha256(token.encode()).hexdigest(), source,
            usage_state, failure.get('stage'), failure.get('kind'),
        ))
    return token


def save_feedback(payload: dict, *, path: Path | None = None) -> dict:
    initialize(path)
    with sqlite3.connect(_path(path)) as con:
        row = con.execute('SELECT feedback_hash FROM task_event WHERE run_id=?', (payload['run_id'],)).fetchone()
        digest = hashlib.sha256(payload['feedback_token'].encode()).hexdigest()
        if not row or not secrets.compare_digest(row[0], digest):
            raise ValueError('反馈凭证无效或对应任务不存在。')
        con.execute('INSERT INTO task_feedback VALUES (?,?,?,?,?) ON CONFLICT(run_id) DO UPDATE SET updated_at=excluded.updated_at,outcome=excluded.outcome,failure_category=excluded.failure_category,human_minutes=excluded.human_minutes', (
            payload['run_id'], datetime.now(timezone.utc).isoformat(), payload['outcome'],
            payload.get('failure_category', 'none'), payload.get('human_minutes'),
        ))
    return {'status': 'recorded', 'message': '反馈已记录，同一任务更新反馈不会重复计数。'}


def summary(*, path: Path | None = None) -> dict:
    initialize(path)
    with sqlite3.connect(_path(path)) as con:
        con.row_factory = sqlite3.Row
        by_status = [dict(r) for r in con.execute('SELECT mode,status,COUNT(*) AS count FROM task_event WHERE source=? GROUP BY mode,status', ('application',))]
        tools = dict(con.execute('''SELECT COALESCE(SUM(tool_calls),0) AS calls,
            COALESCE(SUM(tool_failures),0) AS failures,
            COALESCE(SUM(CASE WHEN usage_status IN ('complete','partial') THEN input_tokens ELSE 0 END),0) AS known_input_tokens,
            COALESCE(SUM(CASE WHEN usage_status IN ('complete','partial') THEN output_tokens ELSE 0 END),0) AS known_output_tokens,
            SUM(CASE WHEN mode='live' AND usage_status='partial' THEN 1 ELSE 0 END) AS partial_usage_runs,
            SUM(CASE WHEN mode='live' AND usage_status='unknown' THEN 1 ELSE 0 END) AS unknown_usage_runs
            FROM task_event WHERE source=?''', ('application',)).fetchone())
        tools['partial_usage_runs'] = tools['partial_usage_runs'] or 0
        tools['unknown_usage_runs'] = tools['unknown_usage_runs'] or 0
        usage_incomplete = tools['partial_usage_runs'] + tools['unknown_usage_runs'] > 0
        tools['input_tokens'] = None if usage_incomplete else tools['known_input_tokens']
        tools['output_tokens'] = None if usage_incomplete else tools['known_output_tokens']
        failures = [dict(row) for row in con.execute('''SELECT failure_stage AS stage,failure_type AS kind,COUNT(*) AS count
            FROM task_event WHERE source=? AND status='failed' GROUP BY failure_stage,failure_type''', ('application',))]
        feedback = [dict(r) for r in con.execute('SELECT f.outcome,f.failure_category,COUNT(*) AS count FROM task_feedback f JOIN task_event t USING(run_id) WHERE t.source=? GROUP BY f.outcome,f.failure_category', ('application',))]
        timings = [r[0] for r in con.execute('SELECT duration_ms FROM task_event WHERE source=? ORDER BY duration_ms', ('application',))]
        human = con.execute('SELECT COUNT(f.human_minutes),AVG(f.human_minutes) FROM task_feedback f JOIN task_event t USING(run_id) WHERE t.source=?', ('application',)).fetchone()
    import math, statistics
    total = sum(r['count'] for r in by_status)
    return {
        'status': 'observed_runs' if total else 'no_observations',
        'title': 'Agent 使用与反馈',
        'source': '本部署实际请求的技术记录；不等于独立用户试用研究',
        'total_runs': total, 'unique_participants': None,
        'verified_task_success_rate': None,
        'study_status': 'not_conducted',
        'by_status': by_status, 'tools': tools, 'feedback': feedback, 'failures': failures,
        'latency_ms': {'p50': statistics.median(timings) if timings else None,
                       'p95': timings[max(0, math.ceil(len(timings) * .95) - 1)] if timings else None},
        'human_review': {'observations': human[0], 'mean_minutes': human[1]},
        'definitions': {
            'completed': '技术流程完成，不自动判为业务任务正确',
            'failed': '已进入执行但未完成的脱敏技术记录；不保存原始问题或Provider错误正文',
            'tool_counts': '按执行轨迹条目统计业务工具及终止失败事件，不等同Provider API请求次数',
            'feedback': '用户自愿评价，同一运行只保留最新一条',
            'cost': 'Token 为调用记录；未配置定价时不推算美元费用',
            'token_usage': '存在未知或部分用量时，总token为null；known_*只表示已观测部分，不等于完整消耗或零费用',
        },
        'limitations': ['不以开发请求数推算真实用户数、采纳率、留存或节省时间。',
                        '遥测不保存原始问题、姓名、邮箱、IP 或模型密钥。'],
    }
