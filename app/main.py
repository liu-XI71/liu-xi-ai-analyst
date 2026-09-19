from __future__ import annotations
import json,os,re,secrets,sqlite3,threading,time,uuid
from collections import defaultdict,deque
from contextlib import asynccontextmanager
from datetime import datetime,timezone
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import HTMLResponse,PlainTextResponse,FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import ROOT,VAR,VERSION,model_status
from app.schemas import AnalysisRequest,SQLRequest
from app import engine,live_agent,reports
from app.sql_tools import query_readonly

@asynccontextmanager
async def lifespan(app):
    engine.initialize()
    with sqlite3.connect(VAR/'runs.sqlite3') as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, created_at TEXT, payload TEXT)')
    yield

app=FastAPI(title='刘希｜AI 数据分析工作台',version=VERSION,lifespan=lifespan)
origins=[x.strip() for x in os.getenv('CORS_ORIGINS','http://localhost:8765,http://127.0.0.1:8765,https://liu-xi71.github.io').split(',') if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=False,allow_methods=['GET','POST'],allow_headers=['Content-Type','Authorization'])
limits=defaultdict(deque);limit_lock=threading.Lock();live_semaphore=threading.BoundedSemaphore(2)

def rate_limit(key,n=30,seconds=60):
    with limit_lock:
        now=time.monotonic();bucket=limits[key]
        while bucket and bucket[0]<now-seconds:bucket.popleft()
        if len(bucket)>=n:raise HTTPException(429,'请求过于频繁，请稍后再试。')
        bucket.append(now)

def require_live(request):
    token=os.getenv('LIVE_ACCESS_TOKEN','')
    provided=request.headers.get('authorization','').removeprefix('Bearer ')
    local=request.client and request.client.host in {'127.0.0.1','::1','testclient'}
    if token:
        if not secrets.compare_digest(provided,token):raise HTTPException(403,'实时模型调用需要部署方的访问令牌。')
    elif not local and os.getenv('ALLOW_LIVE_PUBLIC','false').lower()!='true':
        raise HTTPException(403,'此部署尚未开放公众实时模型调用。')
    rate_limit('live-global',int(os.getenv('LIVE_DAILY_LIMIT','40')),86400)

@app.middleware('http')
async def headers(request,call_next):
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    response.headers['X-Frame-Options']='DENY'
    return response

@app.get('/api/health')
def health():return {'status':'ok','version':VERSION,'data':'synthetic','model_configured':model_status()['configured']}

@app.get('/api/v1/catalog')
def catalog():return {'domains':engine.catalog(),'model':model_status(),'version':VERSION,'data_notice':'固定种子合成演示；真实经历案例单独展示。'}

@app.post('/api/v1/analyze')
def analyze(body:AnalysisRequest,request:Request):
    rate_limit(request.client.host if request.client else 'unknown')
    payload=body.model_dump(exclude_none=True)
    began=time.monotonic()
    try:
        if body.mode=='live':
            require_live(request)
            if not live_semaphore.acquire(blocking=False):raise HTTPException(429,'实时任务正在运行，请稍后再试。')
            try:result=live_agent.execute(payload)
            finally:live_semaphore.release()
        else:
            result=engine.analyze_domain(payload)
            result['trace']=[{'tool':'demo_intent_router','status':'completed','description':'演示模式：有限关键词路由与参数化业务查询，未调用大模型。'}]+result.get('trace',[])
        result.update(run_id=uuid.uuid4().hex,mode=body.mode,created_at=datetime.now(timezone.utc).isoformat(),domain=body.domain,request=payload,duration_ms=round((time.monotonic()-began)*1000,2))
        with sqlite3.connect(VAR/'runs.sqlite3') as conn:
            conn.execute('INSERT INTO runs VALUES (?,?,?)',(result['run_id'],result['created_at'],json.dumps(result,ensure_ascii=False,allow_nan=False)))
        return result
    except live_agent.ModelUnavailable as exc:raise HTTPException(503,str(exc)) from exc
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

@app.get('/api/v1/runs/{run_id}')
def read_run(run_id:str):
    if not re.fullmatch(r'[a-f0-9]{32}',run_id):raise HTTPException(404,'运行记录不存在。')
    with sqlite3.connect(VAR/'runs.sqlite3') as conn:row=conn.execute('SELECT payload FROM runs WHERE id=?',(run_id,)).fetchone()
    if not row:raise HTTPException(404,'运行记录不存在或已随临时部署重启清除。')
    return json.loads(row[0])

@app.get('/api/v1/runs/{run_id}/report')
def report(run_id:str,format:str='html'):
    run=read_run(run_id)
    if format not in {'html','md'}:raise HTTPException(422,'报告格式仅支持 html 或 md。')
    content=reports.html_report(run) if format=='html' else reports.markdown_report(run)
    return (HTMLResponse if format=='html' else PlainTextResponse)(content,headers={'Content-Disposition':f'attachment; filename="analysis-{run_id[:8]}.{format}"'})

@app.post('/api/v1/sql/preview')
def sql_preview(body:SQLRequest,request:Request):
    rate_limit('sql-'+(request.client.host if request.client else 'unknown'),15)
    try:return query_readonly(engine.database(body.domain),body.sql)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

@app.get('/api/v1/evaluations')
def evaluations():
    return engine.evaluation_summary()

@app.get('/api/v1/skills/{domain}')
def skill(domain:str):
    if domain not in engine.DOMAINS:raise HTTPException(404,'未知业务Skill。')
    return {'domain':domain,'content':engine.business_context(domain)}

app.mount('/',StaticFiles(directory=ROOT/'web',html=True),name='web')
