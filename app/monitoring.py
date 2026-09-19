"""Persisted, idempotent daily checks with separate quality and business alerts."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from app.config import VAR


def initialize(path: Path | None = None):
    path = path or VAR / 'monitoring.sqlite3'
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as con:
        con.executescript('''
          CREATE TABLE IF NOT EXISTS monitor_job (
            job_key TEXT PRIMARY KEY, run_id TEXT NOT NULL, created_at TEXT NOT NULL,
            scenario TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL
          );
          CREATE TABLE IF NOT EXISTS monitor_alert (
            alert_key TEXT PRIMARY KEY, category TEXT NOT NULL, title TEXT NOT NULL,
            status TEXT NOT NULL, first_seen TEXT NOT NULL, last_seen TEXT NOT NULL,
            resolved_at TEXT, occurrences INTEGER NOT NULL, payload TEXT NOT NULL
          );
          CREATE TABLE IF NOT EXISTS alert_transition (
            id INTEGER PRIMARY KEY AUTOINCREMENT, alert_key TEXT NOT NULL,
            occurred_at TEXT NOT NULL, previous_status TEXT, status TEXT NOT NULL,
            job_key TEXT NOT NULL, note TEXT NOT NULL
          );
        ''')
    return path


def _transition(con, key, category, title, status, now, job_key, payload):
    old = con.execute('SELECT status FROM monitor_alert WHERE alert_key=?', (key,)).fetchone()
    if old is None and status == 'resolved':
        return
    con.execute('''INSERT INTO monitor_alert VALUES (?,?,?,?,?,?,?,?,?)
        ON CONFLICT(alert_key) DO UPDATE SET status=excluded.status,
        last_seen=excluded.last_seen,resolved_at=excluded.resolved_at,
        occurrences=monitor_alert.occurrences+1,payload=excluded.payload''',
        (key, category, title, status, now, now, now if status == 'resolved' else None,
         1, json.dumps(payload, ensure_ascii=False, allow_nan=False)))
    if old is None or old[0] != status:
        con.execute('INSERT INTO alert_transition(alert_key,occurred_at,previous_status,status,job_key,note) VALUES (?,?,?,?,?,?)',
                    (key, now, old[0] if old else None, status, job_key, payload.get('note', '')))


def run_check(scenario='business_drop', *, path: Path | None = None) -> dict:
    if scenario not in {'business_drop', 'late_data', 'recovered'}:
        raise ValueError('未知监控场景。')
    from app import engine
    req = {'domain': 'onboarding', 'question': '检查增长留存、批次质量及数据完整性恢复状态',
           'task': 'diagnose', 'filters': {'scenario': scenario, 'metric': 'new_user_retention_d7'}}
    result = engine.analyze_domain(req, infer=False)
    return persist_check(result, scenario, path=path)


def persist_check(result, scenario, *, path: Path | None = None):
    path = initialize(path)
    quality = result.get('data_quality') or {}
    is_blocked = result.get('status') == 'data_quality_blocked'
    is_ready = result.get('status') == 'completed' and quality.get('status') == 'passed'
    contract = result.get('metric_contract', {})
    key_material = {'policy_version': 'monitoring.v2.1', 'scenario': scenario, 'contract': contract, 'quality': quality,
                    'kpis': result.get('kpis', []), 'status': result.get('status')}
    signature = json.dumps(key_material, sort_keys=True, ensure_ascii=False, allow_nan=False)
    job_key = hashlib.sha256(signature.encode()).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(path) as con:
        con.execute('BEGIN IMMEDIATE')
        old = con.execute('SELECT payload FROM monitor_job WHERE job_key=?', (job_key,)).fetchone()
        if old:
            return {**json.loads(old[0]), 'reused': True}
        period = json.dumps(contract.get('current_period', ['2026-08-24', '2026-08-30']), separators=(',', ':'))
        alert_scope = hashlib.sha256(period.encode()).hexdigest()[:12]
        qkey, bkey = f'onboarding:quality:{alert_scope}', f'onboarding:d7:{alert_scope}'
        evidence = [e.get('id') for e in result.get('evidence', [])]
        _transition(con, qkey, 'data_quality', '增长数据批次完整性',
                    'resolved' if is_ready else ('open' if is_blocked else 'data_waiting'), now, job_key,
                    {'note': '水位与批次校验通过，允许重新计算成熟指标。' if is_ready else result.get('summary', '尚未获得可用的完整数据，等待复查。'),
                     'evidence_ids': evidence, 'quality': quality})
        changes = [k for k in result.get('kpis', []) if isinstance(k.get('delta'), (int, float)) and k.get('unit') in {'%', '百分点', 'pp'}]
        primary = changes[0] if changes else None
        if not is_ready:
            if con.execute('SELECT 1 FROM monitor_alert WHERE alert_key=?', (bkey,)).fetchone():
                _transition(con, bkey, 'business', '成熟 D7 留存变化', 'data_waiting', now, job_key,
                            {'note': '本次未取得可用的完整数据，保留原业务告警，等待成熟或回填后复核。'})
        elif primary:
            delta = primary['delta']
            _transition(con, bkey, 'business', '成熟 D7 留存变化',
                        'open' if delta <= -2 else 'resolved', now, job_key,
                        {'note': f'本期与对比期差异 {delta:.3f} 个百分点。', 'delta_pp': delta,
                         'threshold_pp': -2, 'rule_type': 'fixed_demo_threshold',
                         'evidence_ids': evidence, 'interpretation': '固定阈值不构成显著性检验，亦非企业生产阈值。'})
        payload = {'run_id': uuid.uuid4().hex, 'job_key': job_key, 'scenario': scenario,
                   'policy_version': 'monitoring.v2.1',
                   'created_at': now, 'status': 'completed' if is_ready else 'data_waiting',
                   'reused': False, 'analysis_status': result['status'], 'summary': result.get('summary'),
                   'data_quality': quality, 'source': '基于固定种子合成事件的批次检查记录',
                   'data_as_of': quality.get('as_of'), 'evidence_ids': evidence}
        con.execute('INSERT INTO monitor_job VALUES (?,?,?,?,?,?)',
                    (job_key, payload['run_id'], now, scenario, payload['status'], json.dumps(payload, ensure_ascii=False)))
    return payload


def summary(*, path: Path | None = None):
    path = initialize(path)
    with sqlite3.connect(path) as con:
        con.row_factory = sqlite3.Row
        alerts = []
        for row in con.execute('SELECT * FROM monitor_alert ORDER BY last_seen DESC'):
            value = dict(row); value['details'] = json.loads(value.pop('payload')); alerts.append(value)
        jobs = [json.loads(row[0]) for row in con.execute('SELECT payload FROM monitor_job ORDER BY created_at DESC LIMIT 20')]
        transitions = [dict(row) for row in con.execute('SELECT * FROM alert_transition ORDER BY id DESC LIMIT 30')]
    return {'status': 'observed_batches' if jobs else 'no_runs', 'title': '增长监控与告警状态',
            'cadence': '日级批次；可手动触发或由调度器调用',
            'scheduler_status': 'external_scheduler_required',
            'data_source': '固定种子合成增长数据', 'jobs': jobs, 'alerts': alerts, 'transitions': transitions,
            'rules': [{'id': 'data_quality', 'description': '缺数时暂停受影响指标；回填完整后重算，业务告警独立判定。'},
                      {'id': 'retention_change', 'description': '成熟 D7 与对比期差异不高于 -2 个百分点时生成业务告警'}],
            'limitations': ['批次检查记录可复现；不代表真实企业实时监控。',
                            '数据可用性恢复不等于留存回升；回填后按原队列重算并单独判定业务告警。']}
