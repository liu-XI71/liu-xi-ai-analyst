"""Integration regressions for observed failures; no real provider requests."""
import json
import sqlite3
import threading
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app import engine, live_agent, main, monitoring, telemetry


class ScriptedProvider:
    def __init__(self, script, with_usage=True):
        self.script = iter(script)
        self.with_usage = with_usage
        self.calls = 0

    def create(self, **request):
        self.calls += 1
        action = next(self.script)
        if isinstance(action, Exception):
            raise action
        name, args = action
        return SimpleNamespace(
            output=[SimpleNamespace(type='function_call', name=name,
                                    arguments=json.dumps(args), call_id=f'regression-{self.calls}')],
            usage=SimpleNamespace(input_tokens=10, output_tokens=5) if self.with_usage else None,
        )


def scripted_request(domain, filters, task='diagnose'):
    engine.initialize()
    provider = ScriptedProvider([
        ('get_business_context', {}),
        ('register_analysis_plan', {'steps': ['metric_contract', 'evidence_report']}),
        ('analyze_business', {'task': task, 'start': None, 'end': None,
                              'compare_start': None, 'compare_end': None, 'filters': filters}),
        ('finish_report', {'finding_indices': []}),
    ])
    result = live_agent.execute({'domain': domain, 'question': '生成留存或复购报告', 'filters': filters},
                                client=SimpleNamespace(responses=provider))
    return result


def monitor_result(status, quality):
    return {'status': status, 'metric_contract': {'current_period': ['2026-08-24', '2026-08-30']},
            'data_quality': {'status': quality}, 'kpis': [], 'evidence': [], 'summary': '尚无完整证据'}


@pytest.mark.parametrize('status,quality', [
    ('insufficient_data', 'insufficient_data'), ('needs_clarification', 'unknown'),
    ('completed', 'blocked'), ('completed', 'unknown'),
])
def test_monitor_cannot_clear_alert_without_completed_and_passed(tmp_path, status, quality):
    path = tmp_path/'monitor.sqlite'
    monitoring.persist_check(monitor_result('data_quality_blocked', 'blocked'), 'late_data', path=path)
    result = monitoring.persist_check(monitor_result(status, quality), 'business_drop', path=path)
    snapshot = monitoring.summary(path=path)
    assert result['status'] == 'data_waiting'
    assert snapshot['alerts'][0]['status'] == 'data_waiting'
    assert '校验通过' not in snapshot['alerts'][0]['details']['note']
    valid = monitoring.persist_check(monitor_result('completed', 'passed'), 'recovered', path=path)
    assert valid['status'] == 'completed'
    assert monitoring.summary(path=path)['alerts'][0]['status'] == 'resolved'


def test_live_schema_and_execution_accept_version_lists_and_integer_seed():
    schema = next(item for item in live_agent.tools_schema() if item['name'] == 'analyze_business')
    properties = schema['parameters']['properties']['filters']['properties']
    assert any(option.get('type') == 'array' for option in properties['app_version']['anyOf'])
    assert {'integer', 'string', 'null'} == {option['type'] for option in properties['seed']['anyOf']}
    versions = scripted_request('onboarding', {'app_version': ['1.8.0', '1.9.0']})
    seed = scripted_request('repurchase', {'seed': 71}, task='segment')
    assert versions['status'] == seed['status'] == 'completed'
    assert seed['metric_contract']['allocation']['seed'] == '71'
    assert versions['model_run']['provider'] == 'test-double'
    assert versions['model_run']['live_verified'] is False


def test_partial_provider_failure_keeps_known_usage_and_no_prompt():
    engine.initialize()
    timeout = live_agent.APITimeoutError(request=httpx.Request('POST', 'https://example.test/responses'))
    provider = ScriptedProvider([('get_business_context', {}), timeout])
    with pytest.raises(live_agent.ModelUnavailable) as caught:
        live_agent.execute({'domain': 'onboarding', 'question': 'PRIVATE_PROMPT_SENTINEL'},
                           client=SimpleNamespace(responses=provider))
    technical = caught.value.technical
    assert technical['stage'] == 'provider'
    assert technical['usage_status'] == 'partial'
    assert technical['usage'] == {'input_tokens': 10, 'output_tokens': 5}
    assert 'PRIVATE_PROMPT_SENTINEL' not in json.dumps(technical)
    assert all(set(item) == {'tool', 'status'} for item in technical['trace'])


def test_tool_validation_failure_has_complete_returned_usage_and_redacted_trace():
    engine.initialize()
    provider = ScriptedProvider([('get_business_context', {})] + [('PRIVATE_TOOL_SENTINEL', {'secret': 'PRIVATE_ARG_SENTINEL'})]*3)
    with pytest.raises(live_agent.ModelUnavailable) as caught:
        live_agent.execute({'domain': 'onboarding', 'question': 'PRIVATE_PROMPT_SENTINEL'},
                           client=SimpleNamespace(responses=provider))
    technical = caught.value.technical
    assert technical['stage'] == 'tool_validation'
    assert technical['usage_status'] == 'complete'
    assert technical['usage']['input_tokens'] == 40
    assert 'PRIVATE_' not in json.dumps(technical)
    assert sum(item['status'] == 'rejected' for item in technical['trace']) == 3


def test_missing_usage_in_success_is_unknown_instead_of_verified_zero():
    engine.initialize()
    provider = ScriptedProvider([('request_clarification', {'question': '请明确指标', 'options': []})], with_usage=False)
    result = live_agent.execute({'domain': 'onboarding', 'question': '分析'}, client=SimpleNamespace(responses=provider))
    assert result['model_run']['usage_status'] == 'unknown'
    assert result['model_run']['live_verified'] is False


@pytest.fixture()
def isolated_api(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'VAR', tmp_path)
    monkeypatch.setattr(telemetry, 'VAR', tmp_path)
    monkeypatch.setattr(monitoring, 'VAR', tmp_path)
    monkeypatch.setattr(main.engine, 'initialize', lambda: None)
    monkeypatch.setattr(main, 'model_status', lambda: {'configured': True})
    monkeypatch.setenv('LIVE_ACCESS_TOKEN', 'runtime-review-token')
    monkeypatch.setenv('LIVE_DAILY_LIMIT', '1')
    main.limits.clear()
    with TestClient(main.app) as client:
        yield client, tmp_path


def live_post(client, token='runtime-review-token'):
    return client.post('/api/v1/analyze', json={'domain': 'onboarding', 'mode': 'live', 'question': 'PRIVATE_PROMPT_SENTINEL'},
                       headers={'Authorization': 'Bearer '+token})


def test_busy_and_unauthorized_requests_do_not_reserve_daily_budget(isolated_api, monkeypatch):
    client, directory = isolated_api
    lock = threading.BoundedSemaphore(1)
    lock.acquire()
    monkeypatch.setattr(main, 'live_semaphore', lock)
    with patch.object(main.live_agent, 'execute') as execute:
        unauthorized = live_post(client, token='wrong')
        busy = live_post(client)
    assert unauthorized.status_code == 403 and busy.status_code == 429
    execute.assert_not_called()
    assert not (directory/'live-quota.sqlite3').exists()
    assert client.get('/api/v1/usage').json()['total_runs'] == 0
    lock.release()


def test_admitted_provider_failure_records_telemetry_and_keeps_quota(isolated_api, monkeypatch):
    client, directory = isolated_api
    semaphore = threading.BoundedSemaphore(1)
    monkeypatch.setattr(main, 'live_semaphore', semaphore)
    failure = live_agent.ModelUnavailable('模拟Provider不可用', stage='provider', kind='APITimeoutError')
    with patch.object(main.live_agent, 'execute', side_effect=failure) as execute:
        response = live_post(client)
        rejected = live_post(client)
    assert response.status_code == 503 and rejected.status_code == 429
    assert execute.call_count == 1
    assert len(response.headers['X-Analysis-Run-Id']) == 32
    usage = client.get('/api/v1/usage').json()
    assert usage['total_runs'] == 1
    assert usage['by_status'] == [{'mode': 'live', 'status': 'failed', 'count': 1}]
    assert usage['failures'] == [{'stage': 'provider', 'kind': 'APITimeoutError', 'count': 1}]
    assert usage['tools']['input_tokens'] is None and usage['tools']['output_tokens'] is None
    assert usage['tools']['unknown_usage_runs'] == 1
    with sqlite3.connect(directory/'live-quota.sqlite3') as con:
        assert con.execute('SELECT calls FROM live_quota').fetchone()[0] == 1
    assert 'PRIVATE_PROMPT_SENTINEL' not in (directory/'telemetry.sqlite3').read_bytes().decode(errors='ignore')
    # Both executed failure and quota rejection release their execution slot.
    assert semaphore.acquire(blocking=False)
    semaphore.release()


def test_partial_usage_is_not_a_complete_aggregate(tmp_path):
    path = tmp_path/'telemetry.sqlite'
    telemetry.record_run({'run_id': 'a'*32, 'domain': 'onboarding', 'mode': 'live', 'status': 'failed',
                          'model_run': {'usage': {'input_tokens': 17, 'output_tokens': 9}, 'usage_status': 'partial'},
                          'failure': {'stage': 'provider', 'kind': 'APIError'}}, path=path)
    tools = telemetry.summary(path=path)['tools']
    assert tools['input_tokens'] is None and tools['output_tokens'] is None
    assert tools['known_input_tokens'] == 17 and tools['known_output_tokens'] == 9
    assert tools['partial_usage_runs'] == 1


def test_existing_telemetry_schema_migrates_without_losing_history(tmp_path):
    path = tmp_path/'old.sqlite'
    with sqlite3.connect(path) as con:
        con.execute('''CREATE TABLE task_event(run_id TEXT PRIMARY KEY,created_at TEXT,domain TEXT,mode TEXT,status TEXT,
                       duration_ms REAL,tool_calls INTEGER,tool_failures INTEGER,input_tokens INTEGER,output_tokens INTEGER,
                       feedback_hash TEXT,source TEXT)''')
        con.execute('INSERT INTO task_event VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', ('old','2026-09-19','onboarding','live','completed',10,2,0,20,10,'hash','application'))
    result = telemetry.summary(path=path)
    assert result['total_runs'] == 1
    assert result['tools']['unknown_usage_runs'] == 1
    assert result['tools']['input_tokens'] is None
    telemetry.record_run({'run_id': 'new', 'domain': 'onboarding', 'mode': 'demo', 'status': 'completed'}, path=path)
    assert telemetry.summary(path=path)['total_runs'] == 2
