from __future__ import annotations
from pathlib import Path
import json
import re
from app.domains import growth,repurchase,onboarding,experiments
from app.config import VAR,ROOT

DOMAINS={'onboarding':onboarding,'experiments':experiments,'repurchase':repurchase,'growth':growth}

def database(domain:str)->Path:
    if domain not in DOMAINS:raise ValueError('未知分析场景。')
    return VAR/f'{domain}.sqlite3'

def initialize():
    VAR.mkdir(parents=True,exist_ok=True)
    for name,module in DOMAINS.items():module.build_database(database(name))

def catalog():return [m.metadata() for m in DOMAINS.values()]

def infer_demo_task(question:str,domain:str)->str:
    if domain=='experiments':return 'report' if any(x in question for x in ['报告','周报']) else 'experiment'
    if domain=='onboarding':
        if any(x in question for x in ['质量','延迟','水位','埋点','缺数']):return 'quality'
        if '漏斗' in question:return 'funnel'
    if any(x in question.lower() for x in ['实验','a/b','ab test','显著','随机分组']):return 'experiment'
    if any(x in question for x in ['周报','报告','简报']):return 'report'
    if domain=='repurchase' and any(x in question for x in ['分群','客户','名单','预算','留出','召回']):return 'segment'
    return 'diagnose'

def clarification(domain,question,options=None):
    return {'status':'needs_clarification','title':'先确认分析范围','summary':question,'metric_contract':{},'kpis':[],'tables':[],'charts':[],'findings':[],'evidence':[],'trace':[],'limitations':['还未执行本次取数。'],'suggestions':options or [],'clarification':{'question':question,'options':options or []}}

def demo_scope_issue(request: dict) -> str | None:
    """Refuse recognized text constraints that the rule path would ignore.

    This is a bounded consistency check, not a general language parser. Dates
    and dimensions for rule analysis must be supplied in structured fields.
    """
    q=request.get('question','')
    fields=[request.get(k) for k in ('start','end','compare_start','compare_end') if request.get(k)]
    iso_dates=set(re.findall(r'(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)',q))
    iso_dates.update(f'{int(y):04d}-{int(m):02d}-{int(d):02d}' for y,m,d in re.findall(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日',q))
    month_days={(int(m),int(d)) for m,d in re.findall(r'(\d{1,2})\s*月\s*(\d{1,2})\s*日',q)}
    selected_month_days={(int(d[5:7]),int(d[8:10])) for d in fields if re.fullmatch(r'\d{4}-\d{2}-\d{2}',d)}
    if iso_dates-set(fields) or month_days-selected_month_days:
        return '问题中的日期未与日期表单一致。请在日期表单填写本期与对比期，或调整问题文字后重试。'
    filters=request.get('filters') or {}
    mentions={
        'device':{value for value,pattern in [('android',r'android|安卓'),('ios',r'(?<![A-Za-z])ios(?![A-Za-z])'),('web',r'网页|(?<![A-Za-z])web(?![A-Za-z])')] if re.search(pattern,q,re.I)},
        'channel':{value for value,terms in [('organic',['自然流量']),('paid_search',['付费搜索']),('social',['社交投放']),('referral',['好友推荐'])] if any(term in q for term in terms)},
        'app_version':set(re.findall(r'(?<![\d.])\d+\.\d+\.\d+(?![\d.])',q)),
        'region':{region for region in ['华东','华南','华北','西部'] if region in q},
    }
    names={'device':'设备','channel':'渠道','app_version':'应用版本','region':'地区'}
    for key,values in mentions.items():
        if not values:continue
        chosen=filters.get(key)
        selected=set(chosen) if isinstance(chosen,list) else {chosen} if isinstance(chosen,str) else set()
        if values!=selected:
            return f'问题中的{names[key]}条件未与筛选表单一致。请在{names[key]}筛选中选择相同范围，或调整问题文字后重试。'
    budgets=re.findall(r'预算\s*(?:为|是|[:：])?\s*(\d+(?:\.\d+)?)\s*元',q)
    budgets+=re.findall(r'(\d+(?:\.\d+)?)\s*元(?:的)?\s*预算',q)
    if budgets:
        try:matches=all(float(value)==float(filters.get('budget')) for value in budgets)
        except (TypeError,ValueError):matches=False
        if not matches:return '问题中的预算未与预算表单一致。请在预算表单填写相同金额后重试。'
    return None

def analyze_domain(request:dict, *,infer=True)->dict:
    request={k:v for k,v in request.items() if v is not None}
    domain=request.get('domain','onboarding')
    if domain not in DOMAINS:raise ValueError('未知分析场景。')
    q=request.get('question','')
    if infer:
        issue=demo_scope_issue(request)
        if issue:return clarification(domain,issue)
    if domain in {'growth','repurchase'} and re.search(r'(?<![A-Za-z0-9])D\s*\d+(?![A-Za-z0-9])|第\s*[0-9一二三四五六七八九十百]+\s*[天日]\s*(?:的\s*)?(?:精确\s*)?(?:留存|复购|回访)',q,re.I):
        definition='次 7 日内至少一次回访' if domain=='growth' else '首次购买后 30 日内至少一次复购'
        return clarification(domain,f'此示例定义为{definition}，不等于指定第 N 日的留存/复购。是否按已定义窗口指标分析？',['按已定义窗口口径分析','取消本次分析'])
    if re.search(r'净利润|利润率|净\s*LTV|完整\s*ROI|盈利|毛利',q,re.I):
        return clarification(domain,'当前合成数据没有完整成本、利润或生命周期价值字段，无法计算净利润、完整 ROI 或净 LTV。请补充成本与归因口径，或选择已定义的留存/复购指标。',['查看已定义的业务指标','取消本次分析'])
    if re.search(r'删除表|删掉数据库|删除所有|\b(drop|delete|truncate|update|insert|alter|attach)\b',q,re.I):
        return clarification(domain,'工作台仅提供只读分析，不执行数据删除。请选择分析任务。')
    task=request.get('task') or infer_demo_task(q,domain)
    request['task']=task
    if infer and not any(x in q.lower() for x in ['留存','回访','增长','渠道','设备','实验','报告','周报','分群','客户','名单','复购','预算','留出','召回','转化','ab test','retention','d1','d7','激活','漏斗','质量','延迟','水位','埋点','缺数','版本','成熟','围栏','srm','onboarding']):
        return clarification(domain,'Python 规则分析仅支持已注册的增长、实验、复购和报告任务。请指定指标或选择示例问题。',[x['question'] for x in DOMAINS[domain].metadata().get('examples',[])])
    return DOMAINS[domain].analyze(request,database(domain))

def business_context(domain:str)->str:
    folders={'growth':'growth-diagnosis','repurchase':'repurchase-operations','onboarding':'onboarding-diagnosis','experiments':'experiment-review'}
    folder=ROOT/'skills'/folders[domain]
    parts=[]
    for p in sorted(folder.rglob('*')):
        if p.is_file() and p.suffix in ['.md','.yaml','.json']:
            parts.append(f'FILE {p.relative_to(ROOT)}\n{p.read_text()[:15000]}')
    return '\n\n'.join(parts)[:38000]


def evaluation_summary():
    path=ROOT/'evals'/'results.json'
    if not path.exists():return {'status':'not_run','metrics':[],'cases':[],'live_status':'not_run'}
    result=json.loads(path.read_text())
    for filename,key in [('audit-results.json','audit_summary'),('first-run.json','first_run_summary'),('v2-first-run.json','v2_first_run_summary')]:
        source=ROOT/'evals'/filename
        if source.exists():
            value=json.loads(source.read_text());result[key]={k:value.get(k) for k in ['total','passed','failed','mode']}
    initial=ROOT/'evals'/'audit-first-run.json'
    if initial.exists() and 'audit_summary' in result:result['audit_summary']['first_run_passed']=json.loads(initial.read_text()).get('passed')
    for filename,key in [('v2-results.json','v2_summary'),('v2-live-results.json','live_summary')]:
        source=ROOT/'evals'/filename
        if source.exists():result[key]=json.loads(source.read_text())
    return result
