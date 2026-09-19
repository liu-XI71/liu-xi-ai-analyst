import json
from types import SimpleNamespace as Obj
import pytest
from fastapi.testclient import TestClient
from app import main,engine,live_agent
from app.sql_tools import query_readonly

@pytest.fixture()
def client():
    main.limits.clear()
    with TestClient(main.app) as c:yield c

def test_run_readback_and_export(client):
    r=client.post('/api/v1/analyze',json={'domain':'growth','question':'分析留存下降','mode':'demo'})
    assert r.status_code==200
    data=r.json();assert data['status']=='completed' and data['mode']=='demo'
    assert data['evidence'] and data['charts']
    loaded=client.get('/api/v1/runs/'+data['run_id']);assert loaded.json()=={k:v for k,v in data.items() if k!='feedback_token'}
    assert 'feedback_token' not in loaded.json()
    for fmt in ['html','md']:
        report=client.get(f"/api/v1/runs/{data['run_id']}/report?format={fmt}")
        assert report.status_code==200 and 'SQL' in report.text
        assert 'attachment;' in report.headers['content-disposition']
    assert client.get('/api/v1/runs/invalid').status_code==404

def test_key_absence_and_auth_do_not_fake_live(client,monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    monkeypatch.delenv('LIVE_ACCESS_TOKEN',raising=False)
    r=client.post('/api/v1/analyze',json={'domain':'growth','question':'留存分析','mode':'live'})
    assert r.status_code==503 and '未使用演示' in r.json()['detail']
    monkeypatch.setenv('LIVE_ACCESS_TOKEN','test-only-access')
    r=client.post('/api/v1/analyze',json={'domain':'growth','question':'留存分析','mode':'live'})
    assert r.status_code==403
    assert 'test-only-access' not in json.dumps(client.get('/api/v1/catalog').json())

@pytest.mark.parametrize('sql',[
    'DELETE FROM growth_users','SELECT 1; SELECT 2','SELECT * FROM sqlite_master',
    "SELECT load_extension('/tmp/x')",'PRAGMA database_list',
    "ATTACH DATABASE '/tmp/a' AS a",'SELECT * FROM growth_metadata',
    'SELECT randomblob(1000000000)',
    'SELECT * FROM main.growth_users',
    'SELECT 1e999 AS value',
    "SELECT x'FF' AS value",
])
def test_sql_rejects_writes_and_private_tables(client,sql):
    response=client.post('/api/v1/sql/preview',json={'domain':'growth','sql':sql})
    assert response.status_code==422

def test_sql_truncation_timeout_and_cte(client):
    result=query_readonly(engine.database('growth'),'SELECT user_id FROM growth_users',max_rows=3)
    assert result['row_count']==3 and result['truncated']
    result=query_readonly(engine.database('growth'),'WITH x AS (SELECT COUNT(*) AS n FROM growth_users) SELECT n FROM x')
    assert result['rows'][0]['n']>0
    with pytest.raises(ValueError):query_readonly(engine.database('growth'),'WITH RECURSIVE t(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM t) SELECT sum(x) FROM t',timeout=.01)

def fake_client(calls):
    class Responses:
        def __init__(self):self.calls=[]
        def create(self,**kw):
            self.calls.append(kw)
            name,args=calls[len(self.calls)-1]
            return Obj(output=[Obj(type='function_call',name=name,arguments=json.dumps(args),call_id=f'c{len(self.calls)}')],usage=Obj(input_tokens=10,output_tokens=5))
    return Obj(responses=Responses())

def analysis_args(**kw):
    return dict(task='diagnose',start=None,end=None,compare_start=None,compare_end=None,filters={},**kw)

def test_real_loop_dispatch_with_fake_provider(client):
    mock=fake_client([('get_business_context',{}),('register_analysis_plan',{'steps':['metric_contract','evidence_report']}),('query_readonly_sql',{'sql':'SELECT COUNT(*) AS n FROM growth_users'}),('analyze_business',analysis_args()),('finish_report',{'finding_indices':[0]})])
    result=live_agent.execute({'domain':'growth','question':'留存下降为什么','mode':'live'},client=mock)
    assert result['status']=='completed'
    assert result['model_run']['rounds']==5
    assert result['model_run']['usage']=={'input_tokens':50,'output_tokens':25}
    assert result['model_run']['sql_generation']=='model'
    assert result['model_run']['live_verified'] is False
    assert any(e['id']=='AIQ01' for e in result['evidence'])
    assert any(isinstance(x,dict) and x.get('type')=='function_call_output' for x in mock.responses.calls[-1]['input'])
    # This verifies protocol only. It is not evidence of a real provider call.

def test_model_cannot_drop_explicit_filters(client):
    mock=fake_client([('get_business_context',{}),('register_analysis_plan',{'steps':['metric_contract','evidence_report']})]+[('analyze_business',analysis_args())]*3)
    with pytest.raises(live_agent.ModelUnavailable,match='连续'):
        live_agent.execute({'domain':'growth','question':'留存下降','filters':{'channel':'organic'}},client=mock)

def test_invalid_report_selection_is_rejected(client):
    mock=fake_client([('get_business_context',{}),('register_analysis_plan',{'steps':['metric_contract','evidence_report']}),('analyze_business',analysis_args())]+[('finish_report',{'finding_indices':[-1]})]*3)
    with pytest.raises(live_agent.ModelUnavailable):live_agent.execute({'domain':'growth','question':'留存下降'},client=mock)

def test_report_escapes_user_question(client):
    r=client.post('/api/v1/analyze',json={'domain':'growth','question':'留存 <script>alert(1)</script>'}).json()
    html=client.get(f"/api/v1/runs/{r['run_id']}/report").text
    assert '<script>alert(1)</script>' not in html
