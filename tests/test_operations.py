import json
import sqlite3
import pytest
from fastapi.testclient import TestClient
from app import main,telemetry,monitoring


def sample_result(status='completed',scenario='business_drop'):
    return {'status':status,'metric_contract':{'current_period':['2026-08-24','2026-08-30'],'version':'test-v1'},
            'data_quality':{'status':'blocked' if status=='data_quality_blocked' else 'passed','as_of':scenario},
            'kpis':[] if status=='data_quality_blocked' else [{'id':'new_user_retention_d7','value':20,'previous':25,'delta':-5,'unit':'%'}],
            'summary':'核查结果','evidence':[{'id':'Q1'}]}


def test_monitoring_deduplicates_and_keeps_business_alert_after_data_recovers(tmp_path):
    path=tmp_path/'monitor.db'
    first=monitoring.persist_check(sample_result(),'business_drop',path=path)
    repeat=monitoring.persist_check(sample_result(),'business_drop',path=path)
    assert not first['reused'] and repeat['reused']
    assert first['run_id']==repeat['run_id']
    monitoring.persist_check(sample_result('data_quality_blocked','late_data'),'late_data',path=path)
    blocked=monitoring.summary(path=path)
    assert {a['category']:a['status'] for a in blocked['alerts']}=={'business':'data_waiting','data_quality':'open'}
    monitoring.persist_check(sample_result('completed','recovered'),'recovered',path=path)
    restored=monitoring.summary(path=path)
    assert {a['category']:a['status'] for a in restored['alerts']}=={'business':'open','data_quality':'resolved'}
    assert len(restored['jobs'])==3
    assert len(restored['transitions'])==5


def test_feedback_requires_capability_and_does_not_invent_study_metrics(tmp_path):
    path=tmp_path/'usage.db'
    result={'run_id':'a'*32,'domain':'onboarding','mode':'demo','status':'completed','trace':[],'request':{'question':'PRIVATE_SENTINEL'}}
    token=telemetry.record_run(result,path=path)
    base={'run_id':'a'*32,'outcome':'needs_revision','failure_category':'evidence','human_minutes':3}
    with pytest.raises(ValueError):telemetry.save_feedback({**base,'feedback_token':'wrong'},path=path)
    telemetry.save_feedback({**base,'feedback_token':token},path=path)
    telemetry.save_feedback({**base,'outcome':'useful','feedback_token':token},path=path)
    data=telemetry.summary(path=path)
    assert data['total_runs']==1 and data['verified_task_success_rate'] is None
    assert data['unique_participants'] is None and data['study_status']=='not_conducted'
    assert sum(x['count'] for x in data['feedback'])==1
    assert token not in json.dumps(data) and 'PRIVATE_SENTINEL' not in path.read_bytes().decode(errors='ignore')


def test_test_runs_are_excluded_from_product_telemetry(tmp_path):
    path=tmp_path/'usage.db'
    telemetry.record_run({'run_id':'b'*32,'domain':'onboarding','status':'completed'},path=path,source='automated_test')
    assert telemetry.summary(path=path)['total_runs']==0


@pytest.fixture()
def client():
    main.limits.clear()
    with TestClient(main.app) as c:yield c


def test_new_domains_replay_reports_and_real_feedback(client):
    for domain,scenario in [('onboarding','business_drop'),('onboarding','late_data'),('experiments','guardrail')]:
        response=client.post('/api/v1/analyze',json={'domain':domain,'question':'生成增长报告并核验指标','filters':{'scenario':scenario}})
        assert response.status_code==200,response.text
        run=response.json()
        assert run['decision'] and run['evidence']
        report=client.get(f"/api/v1/runs/{run['run_id']}/report")
        assert report.status_code==200 and '决策备忘录' in report.text
        feedback=client.post('/api/v1/feedback',json={'run_id':run['run_id'],'feedback_token':run['feedback_token'],'outcome':'useful'})
        assert feedback.status_code==200
        denied=client.post('/api/v1/feedback',json={'run_id':run['run_id'],'feedback_token':'x'*32,'outcome':'incorrect'})
        assert denied.status_code==403
    assert client.get('/api/v1/metrics/onboarding').json()['metrics']
    assert client.get('/api/v1/usage').json()['verified_task_success_rate'] is None


def test_monitor_mutation_requires_admin_token(client,monkeypatch):
    monkeypatch.delenv('ANALYST_ADMIN_TOKEN',raising=False)
    monkeypatch.delenv('LIVE_ACCESS_TOKEN',raising=False)
    assert client.post('/api/v1/monitoring/run',json={'scenario':'late_data'}).status_code==403
    monkeypatch.setenv('ANALYST_ADMIN_TOKEN','test-only-monitor-token')
    result=client.post('/api/v1/monitoring/run',json={'scenario':'late_data'},headers={'Authorization':'Bearer test-only-monitor-token'})
    assert result.status_code==200 and result.json()['status']=='data_waiting'
    assert 'test-only-monitor-token' not in client.get('/api/v1/monitoring').text


def test_live_daily_budget_survives_in_memory_limiter_reset(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from fastapi import HTTPException
    monkeypatch.setattr(main,'VAR',tmp_path)
    monkeypatch.setattr(main,'model_status',lambda:{'configured':True})
    monkeypatch.setenv('LIVE_ACCESS_TOKEN','test-daily-limit')
    monkeypatch.setenv('LIVE_DAILY_LIMIT','1')
    req=SimpleNamespace(headers={'authorization':'Bearer test-daily-limit'},client=SimpleNamespace(host='testclient'))
    main.require_live(req)
    main.limits.clear()
    with pytest.raises(HTTPException) as error:main.require_live(req)
    assert error.value.status_code==429
    with sqlite3.connect(tmp_path/'live-quota.sqlite3') as con:
        assert con.execute('SELECT calls FROM live_quota').fetchone()[0]==1
