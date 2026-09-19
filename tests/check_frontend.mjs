/**
 * Dependency-free frontend contract checks. No browser or DOM automation.
 *   node tests/check_frontend.mjs
 *   node tests/check_frontend.mjs --api http://127.0.0.1:8766
 * Optional API mode makes one deterministic analysis, downloads its reports,
 * and verifies that invalid feedback cannot be recorded. It never calls a model.
 */
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import * as components from '../web/components.js';
import {chartHTML,tableHTML} from '../web/ui.js';
import {evaluationModel,evaluationOverviewHTML} from '../web/evaluation.js';

const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const read=relative=>fs.readFileSync(path.join(root,relative),'utf8');
const json=relative=>JSON.parse(read(relative));
const web=relative=>path.join(root,'web',relative);
const passed=[];
function check(name,fn){fn();passed.push(name);console.log(`PASS ${name}`);}

check('ES module syntax and relative imports',()=>{
  for(const file of ['app.js','ui.js','components.js','evaluation.js']){
    const checked=spawnSync(process.execPath,['--check',web(file)],{encoding:'utf8'});
    assert.equal(checked.status,0,checked.stderr);
    for(const [,target] of read('web/'+file).matchAll(/from ['"](\.\/[^'"]+)['"]/g)){
      assert(fs.existsSync(path.resolve(web(''),target)),`${file}: missing ${target}`);
    }
  }
});
check('entrypoint assets, shell IDs and public presentation',()=>{
  const html=read('web/index.html'),app=read('web/app.js');
  const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);
  assert.equal(ids.length,new Set(ids).size,'Duplicate shell ID');
  for(const [,relative]of html.matchAll(/(?:src|href)="(\.\/[^"#]+)"/g))assert(fs.existsSync(web(relative)),relative);
  for(const [,relative]of app.matchAll(/(?:src|href)="(\.\/[^"#]+)"/g))assert(fs.existsSync(web(relative)),relative);
  for(const phrase of ['面试官','我们的思考','建议你','待开发','下滑来自到数延迟','识别假异常'])assert(!html.concat(app).includes(phrase),phrase);
  assert(app.includes("localStorage.setItem('lx-analyst-api'"),'API base persistence missing');
  assert(!/localStorage[^\n]{0,100}(accessToken|feedback_token|OPENAI_API_KEY)/.test(app),'Sensitive token persistence');
  assert(app.includes("u.protocol==='http:'")&&app.includes("['localhost','127.0.0.1','[::1]']"),'HTTPS boundary missing');
  assert(app.includes("/^sk-/"),'Model-key rejection missing');
});
const scenarioFiles=fs.readdirSync(web('demo')).filter(f=>f.endsWith('.json')&&!['catalog.json','portfolio.json','usage.json','monitoring.json','evaluations.json'].includes(f));
check(`${scenarioFiles.length} scenario result and report contracts`,()=>{
  assert(scenarioFiles.length>=12);
  for(const file of scenarioFiles){
    const d=json('web/demo/'+file);
    const html=[components.decisionHTML(d.decision),components.qualityHTML(d.data_quality),components.hypothesesHTML(d.hypotheses),components.funnelHTML(d.funnel),components.findingsHTML(d.findings),components.evidenceHTML(d.evidence),components.traceHTML(d.trace),components.kvHTML(d.metric_contract),...components.arr(d.charts).map(c=>chartHTML(c)),...components.arr(d.tables).map(t=>tableHTML(t)),...components.arr(d.kpis).map(components.kpiHTML)].join('');
    assert(!html.includes('NaN'),`${file}: non-finite display`);
    assert(!html.includes('[object Object]'),`${file}: unresolved object`);
    assert(html.length>100,file);
    assert(components.reportHTML(d).includes('完整分析'),file);
    if(d.decision?.action)assert(components.decisionHTML(d.decision).includes(d.decision.action),'Singular experiment action lost');
    for(const suffix of ['-report.html','-report.md'])assert(fs.existsSync(web('demo/'+file.replace(/\.json$/,suffix))),`${file}${suffix}`);
  }
});
check('catalog scenario dates and published snapshots',()=>{
  const catalog=json('web/demo/catalog.json');
  for(const domain of catalog.domains.filter(d=>['onboarding','experiments'].includes(d.id))){
    for(const sc of domain.filters.scenario){
      const name=['business_drop','healthy_gain'].includes(sc.value)?domain.id:`${domain.id}-${sc.value}`;
      const result=json(`web/demo/${name}.json`);
      assert.equal(result.request.filters.scenario,sc.value);
      if(domain.id==='experiments'){
        assert.equal(components.requestWindow(result).start,sc.start,`${name} window start`);
        assert.equal(components.requestWindow(result).end,sc.end,`${name} window end`);
      }
    }
  }
});
check('quality state, p-value precision, escaping and long evidence',()=>{
  assert(components.checksHTML([{label:'质量',status:'blocked',observed:3}]).includes('check-mark failed'));
  assert(components.kpiHTML({id:'srm_p',value:0.000023,unit:''}).includes('2.30e-5'));
  assert(!components.findingsHTML([{kind:'fact',text:'<script>alert(1)</script>'}]).includes('<script>'));
  assert(tableHTML({rows:[{detail:'证据'.repeat(60)}]}).includes('long-cell'));
  assert(!components.funnelHTML(json('web/demo/onboarding.json').funnel).includes('"step_id"'),'Raw funnel JSON displayed');
});
check('V2 primary evaluation, legacy separation and first run',()=>{
  const legacy=json('evals/results.json'),v2=json('evals/v2-results.json'),first=json('evals/v2-first-run.json'),live=json('evals/v2-live-results.json');
  const payload={...legacy,audit_summary:json('evals/audit-results.json'),v2_summary:v2,live_summary:live,v2_first_run_summary:first};
  const model=evaluationModel(payload);
  assert(model.isV2);assert.equal(model.active.total,v2.total);assert.equal(model.active.unique_tasks,55);
  assert.equal(model.cases.length,v2.cases.length);assert(model.cases.every(c=>String(c.id).startsWith('V2-')));
  assert.equal(model.first.passed,53);assert.equal(model.first.total,55);
  assert.equal(model.legacy.main.total,60);assert.equal(model.legacy.audit.total,10);
  const html=evaluationOverviewHTML(model,'https://example.com/project');
  assert(html.includes('V2 增长决策回归'));assert(html.includes('旧域回归归档'));assert(html.includes('53 / 55'));
  const nestedFirst=evaluationModel({...payload,v2_first_run_summary:undefined,v2_summary:{...v2,first_run_summary:first}});
  assert.equal(nestedFirst.first.passed,53);
  assert.equal(evaluationModel(v2).active.total,55);
});
check('unrun model never becomes zero or perfect accuracy',()=>{
  const live=json('evals/v2-live-results.json');
  const model=evaluationModel({v2_summary:json('evals/v2-results.json'),live_summary:{...live,status:'not_run',total:0,passed:0}});
  assert.equal(model.liveRate,null);assert.equal(model.liveScore,'未运行');assert(!model.liveCompleted);
  const html=evaluationOverviewHTML(model,'https://example.com/project');
  const liveCard=html.match(/data-evaluation-live>([\s\S]*?)<\/div>/)?.[1];
  assert(liveCard&&liveCard.includes('未运行'));
  assert(!liveCard.includes('0%')&&!liveCard.includes('100%')&&!liveCard.includes('0 / 0'));
  const measured=evaluationModel({v2_summary:json('evals/v2-results.json'),live_summary:{status:'completed',passed:7,total:10,unique_tasks:5}});
  assert.equal(measured.liveRate,.7);assert.equal(measured.liveScore,'7 / 10');
});
check('source-level analysis, reports and feedback API contracts',()=>{
  const app=read('web/app.js'),server=read('app/main.py'),schema=read('app/schemas.py');
  assert(app.includes("api('/api/v1/analyze'),{method:'POST'"));assert(server.includes("@app.post('/api/v1/analyze')"));
  assert(app.includes('/api/v1/runs/${encodeURIComponent(data.run_id)}/report?format=${format}'));
  assert(server.includes("@app.get('/api/v1/runs/{run_id}/report')"));assert(server.includes("{'html','md'}"));
  for(const name of ['run_id','feedback_token','outcome','failure_category','human_minutes']){assert(schema.includes(name));assert(app.includes(name));}
  for(const value of ['useful','needs_revision','incorrect','not_completed','none','understanding','metric','time_window','tool','evidence','delivery']){
    assert(schema.includes(`'${value}'`),value);assert(app.includes(`value="${value}"`),value);
  }
  assert(app.includes('max="480"'));assert(schema.includes('le=480'));
  assert(app.includes('minutes===\'\'?null:Number(minutes)'));
  assert(app.includes('data._replay||!state.online||!data.feedback_token'),'Static feedback must remain disabled');
});

check('study protocol links and live runtime-error usage state',()=>{
  const html=components.studyProtocolHTML();
  assert(html.includes('真实用户研究尚未开展'));
  assert(html.includes('./resources/user-study.html'));
  assert(html.includes('download'));
  assert(fs.existsSync(web('resources/user-study.html')),'Study protocol artifact missing');
  const app=read('web/app.js');
  assert(app.includes('studyProtocolHTML({completed:u.study_status'));
  assert(app.includes('${studyProtocolHTML()}'));
  const usage=tableHTML({rows:[{mode:'live',status:'runtime_error',count:2}]});
  assert(usage.includes('运行失败'));assert(usage.includes('模型模式'));assert(usage.includes('>2</td>'));
  assert(!usage.includes('通过'));
  const unknown=components.kpiHTML({label:'调用用量',value:null,unit:'tokens'});assert(unknown.includes('—'));assert(!unknown.includes('NaN'));assert(!app.includes('input_tokens??0'));assert(!app.includes('output_tokens??0'));
});

const apiIndex=process.argv.indexOf('--api');
if(apiIndex!==-1){
  const base=new URL(process.argv[apiIndex+1]);
  assert(['http:','https:'].includes(base.protocol),'Unsupported API URL');
  assert(['127.0.0.1','localhost','[::1]'].includes(base.hostname),'Contract checks only target an existing local service');
  const origin='http://127.0.0.1:8766';
  const request=async(p,opts={})=>{const response=await fetch(new URL(p,base),{...opts,signal:AbortSignal.timeout(45000)});return response;};
  for(const endpoint of ['/api/health','/api/v1/catalog','/api/v1/evaluations']){
    const response=await request(endpoint);assert(response.ok,`${endpoint} HTTP ${response.status}`);const value=await response.json();if(endpoint==='/api/v1/evaluations'){const model=evaluationModel(value);assert(model.isV2,'Service must expose V2 summary');assert.equal(model.active.unique_tasks,55);assert.equal(model.first?.passed,53);if(value.live_summary?.status==='not_run')assert.equal(model.liveRate,null);}
  }
  for(const requestedOrigin of [origin,'http://localhost:8766']){const preflight=await request('/api/v1/analyze',{method:'OPTIONS',headers:{Origin:requestedOrigin,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type,authorization'}});assert(preflight.ok,`8766 CORS preflight: ${preflight.status}`);assert.equal(preflight.headers.get('access-control-allow-origin'),requestedOrigin,'8766 CORS origin');}
  const payload={domain:'onboarding',question:'前端合同验收：比较成熟注册队列的精确 D7 留存。',task:'diagnose',mode:'demo',filters:{scenario:'business_drop',metric:'new_user_retention_d7'}};
  const response=await request('/api/v1/analyze',{method:'POST',headers:{'Content-Type':'application/json',Origin:origin},body:JSON.stringify(payload)});
  assert(response.ok,`Analyze HTTP ${response.status}`);const result=await response.json();
  assert.equal(result.mode,'demo');assert.match(result.run_id,/^[a-f0-9]{32}$/);assert(result.feedback_token?.length>=20);
  for(const format of ['html','md']){const report=await request(`/api/v1/runs/${result.run_id}/report?format=${format}`);assert(report.ok,`${format} report ${report.status}`);assert((await report.text()).includes(result.title));}
  const badFeedback=await request('/api/v1/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({run_id:result.run_id,feedback_token:'invalid-contract-check-token',outcome:'needs_revision',failure_category:'delivery',human_minutes:null})});
  assert.equal(badFeedback.status,403,'Invalid feedback capability should be rejected');
  const outOfRange=await request('/api/v1/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({run_id:result.run_id,feedback_token:'invalid-contract-check-token',outcome:'needs_revision',failure_category:'delivery',human_minutes:481})});
  assert.equal(outOfRange.status,422,'Feedback upper bound should be schema validated');
  passed.push('local HTTP analyze/report/CORS/feedback contracts');console.log('PASS local HTTP analysis, reports, 8766 CORS and feedback boundaries; no valid feedback was submitted.');
}
console.log(`\n${passed.length} frontend contract groups passed. No browser or DOM automation. No real model calls.`);
