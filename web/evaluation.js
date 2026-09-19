import {escape as e,icon,formatNumber} from './ui.js';
const obj=v=>v&&typeof v==='object'&&!Array.isArray(v)?v:null;
export function evaluationModel(payload={}){
  const nested=obj(payload.v2_summary);
  const active=nested||payload;
  const isV2=Boolean(nested)||/V2/i.test(active.title||'')||(active.cases||[]).some(c=>String(c.id).startsWith('V2-'));
  const live=obj(payload.live_summary)||obj(active.live_summary)||{status:active.live_status||'not_run'};
  const liveCompleted=live.status==='completed'&&Number(live.total)>0;
  return {active,isV2,completed:active.status==='completed',live,liveCompleted,
    liveScore:liveCompleted?`${live.passed??'—'} / ${live.total}`:'未运行',
    liveRate:liveCompleted?Number(live.passed)/Number(live.total):null,
    first:obj(payload.v2_first_run_summary)||obj(active.first_run_summary)||(isV2?null:obj(payload.first_run_summary)),
    legacy:nested?{main:{total:payload.total,passed:payload.passed},audit:payload.audit_summary,first:payload.first_run_summary}:null,
    cases:Array.isArray(active.cases)?active.cases:[],
    metrics:Array.isArray(active.metrics)?active.metrics:[]};
}
export function evaluationOverviewHTML(model,source){
  const {active,isV2,completed,live,liveCompleted,liveScore,first,legacy,cases}=model;
  return `<div class="verification-hero"><div><span class="eyebrow">${isV2?'GROWTH V2 / PUBLIC REGRESSION':'LEGACY DOMAIN / PUBLIC REGRESSION'}</span><h2>${e(active.title||'分析流程验证')}</h2><p>${completed?'已执行指标口径、原始事件复算、数据质量、实验决策和 SQL 证据检查。':'当前没有可核验的完整评测结果。'}<br>规则回归与真实模型评测分别记录。</p>${active.generated_at?`<div class="evaluation-timestamp">结果记录：${e(active.generated_at)}</div>`:''}</div><a class="button button-secondary" href="${source}/blob/main/docs/evaluation.md" target="_blank" rel="noopener">评测方法 ${icon('arrow-up')}</a></div>
  <div class="eval-summary-grid"><div class="eval-metric" data-evaluation-primary><span>${isV2?'V2 增长决策回归':'旧域确定性回归'}</span><strong>${completed?`${e(active.passed??'—')} <small>/ ${e(active.total??cases.length)}</small>`:'未运行'}</strong><small>${completed?`${e(active.unique_tasks??cases.length)} 个独立任务 · ${e(active.total??cases.length)} 次执行`:'等待实际执行记录'}<br>公开固定样本 · 不代表模型正确率</small></div><div class="eval-metric" data-evaluation-live><span>真实模型端到端</span><strong>${e(liveScore)}</strong><small>${liveCompleted?`${e(live.unique_tasks??live.requested_cases??'—')} 个独立任务 · ${e(live.total)} 次执行`:'尚无真实模型评测结果'}<br>${liveCompleted?'按记录中的模型与版本统计':'当前公开结果为规则计算'}</small></div><div class="eval-metric"><span>人工分析提效对照</span><strong>${active.efficiency_status==='completed'?'已记录':'未记录'}</strong><small>人工复核与修订时间单独计量<br>本机引擎耗时不等于人工提效</small></div></div>
  ${first?`<div class="audit-strip"><div><span>${isV2?'V2 首轮记录':'旧域首轮记录'}</span><strong>${e(first.passed??'—')} / ${e(first.total??'—')}</strong></div><p>首轮未通过 ${e(first.failed??Math.max(0,Number(first.total)-Number(first.passed)))} 个任务。保留首轮和修复后结果，样本已用于公开回归。<a class="text-link" href="${source}/blob/main/evals/${isV2?'v2-first-run':'first-run'}.json" target="_blank" rel="noopener">查看首轮 ↗</a></p></div>`:''}
  ${legacy?`<details class="legacy-evaluation"><summary>旧域回归归档 <span>原增长域与复购历史样本</span></summary><div><p>旧主集 ${e(legacy.main.passed??'—')} / ${e(legacy.main.total??'—')}；旧补充审计 ${e(legacy.audit?.passed??'—')} / ${e(legacy.audit?.total??'—')}。历史结果不计入 V2 通过率。</p>${legacy.first?`<p>旧主集首次 ${e(legacy.first.passed)} / ${e(legacy.first.total)}；旧审计首次 ${e(legacy.audit?.first_run_passed??'—')} / ${e(legacy.audit?.total??'—')}。</p>`:''}<a class="text-link" href="${source}/tree/main/evals" target="_blank" rel="noopener">查看历史记录 ↗</a></div></details>`:''}
  ${active.transport?`<div class="evaluation-scope"><strong>验证链路</strong><span>${e(active.transport)}</span></div>`:''}`;
}
