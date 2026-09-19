"""Export complete, reproducible analysis cases for a static portfolio deployment."""
from __future__ import annotations
import hashlib
import json
import sys
import tempfile
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import engine,reports,monitoring,telemetry
from app.config import ROOT,VERSION


def main():
    engine.initialize()
    dest=ROOT/'web'/'demo';dest.mkdir(parents=True,exist_ok=True)
    generated=datetime.now(timezone.utc).isoformat()
    def save(name,payload):
        (dest/name).write_text(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    save('catalog.json',{'domains':engine.catalog(),'model':{'configured':False,'mode':'demo','model':'gpt-5-mini','provider':'OpenAI Responses API'},'version':VERSION,'data_notice':'匿名合成数据；静态回放由 Python 实际查询生成。'})
    requests=[
        ('onboarding',{'domain':'onboarding','task':'diagnose','question':'最近两个成熟注册周的精确D7留存为什么下降？先核验数据，再拆渠道、设备与版本。','filters':{'scenario':'business_drop','metric':'new_user_retention_d7'}}),
        ('onboarding-late_data',{'domain':'onboarding','task':'diagnose','question':'检查D7留存下降与批次数据延迟，说明哪些结论可以使用。','filters':{'scenario':'late_data','metric':'new_user_retention_d7'}}),
        ('onboarding-recovered',{'domain':'onboarding','task':'diagnose','question':'数据回填后重新检查D7留存，区分数据恢复与业务恢复。','filters':{'scenario':'recovered','metric':'new_user_retention_d7'}}),
        ('repurchase',{'domain':'repurchase','task':'segment','question':'按截止日历史购买行为制定200元预算下的复购候选与随机留出方案。','filters':{'budget':200,'contact_cost':2,'holdout_ratio':.2}}),
        ('growth',{'domain':'growth','task':'diagnose','question':'比较成熟队列的次7日内回访，拆解渠道和设备变化。'}),
    ]
    for scenario in ['healthy_gain','srm','guardrail','immature','underpowered','unequal_allocation','config_change','data_gap']:
        name='experiments' if scenario=='healthy_gain' else 'experiments-'+scenario
        requests.append((name,{'domain':'experiments','task':'experiment','question':'评审新用户承接实验：核对分配与成熟、主指标和负反馈围栏，给出决策。','filters':{'scenario':scenario}}))
    snapshots={}
    for name,request in requests:
        request['mode']='demo'
        result=engine.analyze_domain(request,infer=False)
        fingerprint=hashlib.sha256(json.dumps({'request':request,'contract':result.get('metric_contract'),'kpis':result.get('kpis'),'status':result.get('status')},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        result.update(domain=request['domain'],mode='demo',request=request,static_snapshot=True,created_at=generated,run_id=fingerprint[:32])
        result['provenance']={'application_version':VERSION,'data_kind':'synthetic','metric_version':result.get('metric_contract',{}).get('version'),'snapshot_sha256':fingerprint,'fingerprint_scope':'request, metric_contract, kpis, status','execution':'Python business tools; no model call'}
        result['trace']=[{'tool':'static_snapshot','status':'completed','description':'静态案例：读取已保存的 Python / SQL 计算结果，未调用模型。'}]+result.get('trace',[])
        save(name+'.json',result)
        (dest/(name+'-report.html')).write_text(reports.html_report(result))
        (dest/(name+'-report.md')).write_text(reports.markdown_report(result))
        snapshots[name]=result
    save('evaluations.json',engine.evaluation_summary())
    with tempfile.TemporaryDirectory(prefix='analyst-export-') as tmp:
        path=Path(tmp)/'monitor.sqlite3'
        for scenario,name in [('business_drop','onboarding'),('late_data','onboarding-late_data'),('recovered','onboarding-recovered')]:
            monitoring.persist_check(snapshots[name],scenario,path=path)
        monitor=monitoring.summary(path=path)
        monitor.update(static_snapshot=True,source='合成场景的实际检查、阻断与回填记录',scheduler_status='replay_of_executed_batches')
        save('monitoring.json',monitor)
        usage=telemetry.summary(path=Path(tmp)/'usage.sqlite3')
        usage.update(static_snapshot=True,source='暂无真实用户试用记录')
        save('usage.json',usage)
    ob=snapshots['onboarding'];exp=snapshots['experiments'];rep=snapshots['repurchase']
    metric_count=sum(len(x.get('metrics',[])) for x in engine.catalog() if x['id'] in {'onboarding','experiments','repurchase'})
    cases=[]
    for identifier,title,context,target in [
        ('onboarding','新用户留存下降：从指标到干预方案','增长负责人需要判断优先优化流量结构还是注册后的首次体验。','#growth'),
        ('onboarding-late_data','数据延迟：先恢复完整性，再判断业务','数据批次迟到时，需要暂停受影响判断，回填后再核对业务变化。','#growth'),
        ('experiments-guardrail','主指标正向：仍需检查体验代价','产品实验需要同时满足业务收益、数据可信和负向体验约束。','#experiments'),
        ('repurchase','复购运营：有限预算中的候选与验证','运营需要在预算内圈定候选，并保留随机对照以验证后续增量。','#repurchase')]:
        s=snapshots[identifier]
        cases.append({'id':identifier,'title':title,'context':context,'summary':s['summary'],'decision':s.get('decision'), 'kpis':s.get('kpis',[]),'evidence_count':len(s.get('evidence',[])),'href':target,'report':'demo/'+identifier+'-report.html','data_source':'合成数据方法验证'})
    save('portfolio.json',{
        'title':'刘希 · AI 数据分析','headline':'从增长问题，到有证据的业务决定。','version':VERSION,'generated_at':generated,
        'data_source':'匿名合成增长与电商数据',
        'kpis':[{'label':'可复现分析场景','value':len(snapshots),'unit':'个'}, {'label':'业务分析域','value':3,'unit':'个'}, {'label':'注册指标合同','value':metric_count,'unit':'项'}, {'label':'主要案例SQL证据','value':sum(len(s.get('evidence',[])) for s in [ob,exp,rep]),'unit':'组'}],
        'cases':cases,'primary_result':ob['summary'],
        'capabilities':['指标语义与成熟窗口','事件数据与质量门','有序漏斗与分群诊断','随机实验与围栏评审','受控自然语言工具调用','SQL与报告证据追溯','告警恢复与幂等回填','任务运行与自愿反馈'],
        'validation':{'deterministic':'computed','live_model':'not_run','user_study':'not_conducted','business_lift':'not_measured'},
        'links':{'github':'https://github.com/liu-XI71/liu-xi-ai-analyst','original':'https://liu-xi71.github.io/'}
    })
    print(f'Exported {len(snapshots)} actual analysis snapshots, {len(snapshots)*2} reports, catalog, metrics, monitoring and usage states.')

if __name__=='__main__':main()
