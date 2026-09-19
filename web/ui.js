export const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const paths = {
  grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  trend:'<path d="M3 17l6-6 4 4 8-10"/><path d="M15 5h6v6"/><path d="M3 4v17h18"/>',
  users:'<circle cx="9" cy="8" r="3"/><path d="M3 21v-2a6 6 0 0 1 12 0v2M16 5a3 3 0 0 1 0 6M21 21v-2a6 6 0 0 0-4-5.66"/>',
  check:'<path d="M12 3l8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z"/><path d="m8 12 3 3 5-6"/>',
  book:'<path d="M12 6c-2-2-6-3-10-2v15c4-1 8 0 10 2m0-15c2-2 6-3 10-2v15c-4-1-8 0-10 2V6Z"/>',
  github:'<path d="M9 19c-4.3 1.3-4.3-2.2-6-2.7m12 5v-3.3a2.9 2.9 0 0 0-.8-2.3c2.7-.3 5.6-1.3 5.6-6a4.7 4.7 0 0 0-1.3-3.3 4.4 4.4 0 0 0-.1-3.3S17.3 2.8 15 4a11.6 11.6 0 0 0-6 0C6.7 2.8 5.6 3.1 5.6 3.1a4.4 4.4 0 0 0-.1 3.3 4.7 4.7 0 0 0-1.3 3.3c0 4.7 2.9 5.7 5.6 6A2.9 2.9 0 0 0 9 18v3.3"/>',
  external:'<path d="M14 3h7v7M10 14 21 3"/><path d="M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5"/>',
  'arrow-up':'<path d="M7 17 17 7M7 7h10v10"/>',
  'arrow-right':'<path d="M4 12h16m-6-6 6 6-6 6"/>',
  'arrow-left':'<path d="M20 12H4m6-6-6 6 6 6"/>',
  settings:'<path d="m9 3-.5 3L6 7 3.5 6l-2 3.5L4 11v3l-2.5 1.5 2 3.5L6 18l2.5 1 .5 3h4l.5-3 2.5-1 2.5 1 2-3.5L18 14v-3l2.5-1.5-2-3.5L16 7l-2.5-1-.5-3H9Z" transform="translate(1 -1) scale(.92)"/><circle cx="12" cy="12" r="3"/>',
  menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
  close:'<path d="m6 6 12 12M6 18 18 6"/>',
  lock:'<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/>',
  database:'<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
  terminal:'<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m6 8 4 4-4 4M13 16h5"/>',
  file:'<path d="M14 2H5a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V9l-7-7Z"/><path d="M14 2v7h7M7 13h10M7 17h7"/>',
  chart:'<path d="M3 3v18h18M8 16V9M13 16V5M18 16v-4"/>',
  spark:'<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z"/>',
  download:'<path d="M12 3v12m-5-5 5 5 5-5M4 15v5h16v-5"/>',
  chevron:'<path d="m6 9 6 6 6-6"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
  tick:'<path d="m5 12 4 4L19 6"/>',
  alert:'<path d="M12 3 2 21h20L12 3Z"/><path d="M12 9v5M12 17h.01"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  play:'<path d="m8 4 13 8-13 8V4Z"/>',
  refresh:'<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6.1 6.1A8 8 0 0 1 20 12M4 12a8 8 0 0 0 13.9 5.9"/>',
  code:'<path d="m7 6-6 6 6 6m10-12 6 6-6 6M14 3l-4 18"/>',
  layers:'<path d="m12 3 10 5-10 5L2 8l10-5ZM2 12l10 5 10-5M2 16l10 5 10-5"/>',
  target:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>'
};
export const icon = (name, extra = '') => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" ${extra}>${paths[name] || paths.file}</svg>`;
export function hydrateIcons(root = document){root.querySelectorAll('[data-icon]').forEach(el => {el.innerHTML = icon(el.dataset.icon);});}
export const valueText = value => value === null || value === undefined ? '—' : typeof value === 'object' ? JSON.stringify(value) : String(value);
export function formatNumber(value, digits = 2){if(value === null || value === undefined || value === '') return '—';const n = Number(value);if(!Number.isFinite(n)) return String(value);return n.toLocaleString('zh-CN',{maximumFractionDigits:digits});}
export const labels = {mode:'运行方式',count:'运行次数',outcome:'使用结果',failure_category:'问题分类',cohort:'用户队列',date:'日期',week:'周',month:'月份',channel:'渠道',device:'设备',segment:'分群',users:'用户数',user_count:'用户数',new_users:'新增用户',retained_users:'留存用户',retention:'留存率',retention_rate:'留存率',rate:'占比',period:'时期',metric:'指标',value:'数值',previous:'对比期',current:'当前期',delta:'变化',customer_id:'客户 ID',customer_count:'客户数',customers:'客户数',revenue:'收入',orders:'订单数',order_count:'订单数',avg_order_value:'平均客单价',repurchase_rate:'复购率',repeat_rate:'复购率',repeat_customers:'复购客户',group:'实验分组',variant:'实验分组',sample_size:'样本量',conversions:'转化人数',conversion_rate:'转化率',metric_version:'口径版本',denominator:'分母',numerator:'分子',unit:'单位',definition:'定义',window:'观察窗口',grain:'粒度',data_source:'数据来源',source:'数据来源',data_range:'数据范围',start:'开始日期',end:'结束日期',start_date:'开始日期',end_date:'结束日期',compare_start:'对比开始',compare_end:'对比结束',current_period:'当前期',comparison_period:'对比期',comparison:'对比期',maturity:'成熟性',formula:'计算公式',name:'名称',version:'版本',description:'说明',sql:'SQL',population:'人群',filters:'筛选',task:'任务',limitations:'边界',contribution:'贡献',contribution_pp:'贡献（百分点）',within_effect:'组内变化',mix_effect:'结构变化',mix_effect_pp:'结构变化（百分点）',within_effect_pp:'组内变化（百分点）',p_value:'p 值',ci_low:'区间下限',ci_high:'区间上限',lift:'提升',uplift:'提升',recency_days:'最近购买间隔（天）',frequency:'购买次数',monetary:'累计消费',rfm_segment:'RFM 分群',status:'状态'};
Object.assign(labels, {retention_pct:'留存率（%）',previous_pct:'对比期（%）',current_pct:'本期（%）',previous_users:'对比期用户数',current_users:'本期用户数',previous_rate_pct:'对比期留存（%）',current_rate_pct:'本期留存（%）',mix_pp:'结构贡献（百分点）',performance_pp:'组内贡献（百分点）',total_pp:'总贡献（百分点）',signup_date:'注册日期',component:'变化来源',label:'分群',avg_recency:'平均未购天数',avg_frequency:'平均购买次数',window_value:'窗口交易额（元）',history_value:'历史交易额（元）',region:'地区',recency:'未购天数',assignment:'随机分组',planned_cost:'计划成本（元）',id:'标识',timezone:'时区',snapshot_date:'数据快照日',latest_mature_cohort:'最新成熟队列',exclusions:'排除范围',not_equivalent_to:'区别于',previous_period:'对比期',observation_end:'观察截止日',metrics:'业务指标',candidate_cutoff:'候选截止日',monetary_window:'金额窗口',frequency_window:'频次窗口',allocation:'随机分配',arm:'实验组',cost_per_user:'人均激励成本（元）',revenue_per_user:'人均收入（元）',gate:'决策门槛',rule:'规则',observed:'观测值',passed:'通过状态',lift_pp:'绝对提升（百分点）',ci95_low_pp:'95% 区间下限',ci95_high_pp:'95% 区间上限',srm_p_value:'SRM p 值',experiment_period:'实验窗口',srm_alpha:'SRM 阈值',min_lift_pp:'最小业务提升',max_incremental_cost_per_user:'增量成本上限',currency:'币种',split:'数据集',domain:'场景',question:'问题',category:'类别',expected_status:'预期状态',actual_status:'实际状态',duration_ms:'耗时（ms）'});
Object.assign(labels, {
  schema_valid: '事件版本有效',
  event_integrity_valid: '事件关系有效',
  feed_result_unresolved: '首屏结果未确认人数',
  unsupported_schema_events: '版本不兼容事件数',
  invalid_event_relationships: '关系异常事件数',
  duplicate_event_ids: '重复事件 ID 数',
  required_until: '所需完整观察截止',
  watermark_complete: '数据水位完整',
  available: '指标可用',
  activation_pct: '24 小时激活率（%）',
  first_feed_failure_pct: '首次首屏请求失败率（%）'
});
const valueLabels={runtime_error:'运行失败',model_unavailable:'模型不可用',data_quality_blocked:'数据需修复',passed:'通过',failed:'未通过',blocked:'已暂停',invalid_data:'数据无效',waiting_for_maturity:'等待成熟',insufficient_evidence:'证据不足',pending:'尚未执行',recovered:'已恢复',resolved:'已恢复',open:'触发中',demo:'确定性计算',live:'模型模式',no_observations:'无使用记录',onboarding:'新用户增长',experiments:'实验评审',repurchase:'复购运营',growth:'原增长域',paid_search:'付费搜索',social:'社交渠道',current:'本期',previous:'对比期',control:'对照组',treatment:'处理组',holdout:'留出组',first:'近期单次购买',active:'活跃复购',cooling:'31—60 日未购',dormant:'60 日以上未购',single:'单次购买沉默',completed:'完成',needs_clarification:'需澄清',insufficient_data:'数据不足',paid:'付费渠道',organic:'自然渠道',referral:'推荐渠道',ios:'iOS',android:'Android',web:'网页'};
export const displayValue=(key,value)=>typeof value==='boolean'?(value?'通过':'未通过'):typeof value==='string'?(valueLabels[value]||value):value;
export const label = key => labels[key] || String(key).replace(/_/g,' ');
export function tableHTML(table, maxRows = 100){
  const rows = Array.isArray(table?.rows) ? table.rows : [];
  const columns = Array.isArray(table?.columns) && table.columns.length ? table.columns.map(c => typeof c === 'object' ? (c.key || c.id || c.name) : c) : Object.keys(rows[0] || {});
  if(!rows.length) return '<div class="chart-empty">此查询没有返回数据行。</div>';
  return `<div class="data-table-wrapper"><table class="data-table"><thead><tr>${columns.map(c=>`<th scope="col" title="${escape(c)}">${escape(label(c))}</th>`).join('')}</tr></thead><tbody>${rows.slice(0,maxRows).map(row=>`<tr>${columns.map((c,i)=>{const v=Array.isArray(row)?row[i]:row[c];return `<td class="${typeof v==='string'&&v.length>55?'long-cell':''}" title="${escape(valueText(v))}">${escape(typeof v==='number'?formatNumber(v,4):valueText(displayValue(c,v)))}</td>`;}).join('')}</tr>`).join('')}</tbody></table></div>${rows.length>maxRows?`<p class="field-help">展示前 ${maxRows} 行，共 ${rows.length} 行；完整结果可在报告中查看。</p>`:''}`;
}
export function contractHTML(contract){return `<dl class="contract-grid">${Object.entries(contract || {}).map(([key,value])=>`<dt>${escape(label(key))}</dt><dd>${escape(typeof value === 'object'? JSON.stringify(value,null,2):valueText(value))}</dd>`).join('')}</dl>`;}
export function chartHTML(chart, {dark = false, compact = false} = {}){
  const data = Array.isArray(chart?.data)?chart.data:[];
  if(!data.length) return '<div class="chart-empty">当前结果没有可绘制的数据。</div>';
  const xKey = chart.x_key || Object.keys(data[0])[0];
  const hasNumber=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
  const ys = (Array.isArray(chart.y_keys)?chart.y_keys:[]).filter(key=>data.some(d=>hasNumber(d[key])));
  if(!ys.length) return '<div class="chart-empty">图表缺少数值字段，可在数据表中查看原始结果。</div>';
  const rows=data.slice(0,36),w=compact?430:640,h=compact?142:285,p={left:compact?37:53,right:20,top:22,bottom:compact?25:48},pw=w-p.left-p.right,ph=h-p.top-p.bottom;
  const colors=dark?['#52d3b6','#8eb0c6','#c4cdae','#95d4cb']:['#178a70','#86a8b4','#c3cba5','#81bbae','#abbdd0'];
  const vals=rows.flatMap(d=>ys.filter(k=>hasNumber(d[k])).map(k=>Number(d[k])));
  let min=Math.min(0,...vals),max=Math.max(0,...vals);if(max===min){max=min+1;}const span=max-min;max+=span*.13;if(min<0)min-=span*.08;
  const yy=v=>p.top+ph-(Number(v)-min)/(max-min)*ph;
  const step=pw/Math.max(rows.length,1),xx=i=>p.left+step*(i+.5);
  let elements='';
  const stroke=dark?'#29464d':'#eaf0eb',textColor=dark?'#719a9c':'#8a9a91';
  for(let i=0;i<=4;i++){const v=min+(max-min)*i/4,y=yy(v);elements+=`<line x1="${p.left}" y1="${y}" x2="${w-p.right}" y2="${y}" stroke="${stroke}"/><text x="${p.left-9}" y="${y+3}" text-anchor="end" style="fill:${textColor};font-size:${compact?8:10}px">${escape(formatNumber(v,Math.abs(v)<1?2:1))}</text>`;}
  const interval = Math.max(1,Math.ceil(rows.length/(compact?4:7)));
  const ticks=[];for(let i=0;i<rows.length;i+=interval)ticks.push(i);if(ticks.at(-1)!==rows.length-1){if(rows.length-1-ticks.at(-1)<interval*.75)ticks.pop();ticks.push(rows.length-1);}
  rows.forEach((d,i)=>{if(ticks.includes(i)){let text=String(displayValue(xKey,d[xKey]??i+1));if(/^\d{4}-\d{2}-\d{2}$/.test(text))text=text.slice(5);if(text.length>12)text=text.slice(0,10)+'…';elements+=`<text x="${xx(i)}" y="${h-p.bottom+19}" text-anchor="middle" style="fill:${textColor};font-size:${compact?8:10}px">${escape(text)}</text>`;}});
  ys.forEach((key,s)=>{
    const color=colors[s%colors.length];
    if(chart.type==='line'||chart.type==='scatter'){
      const points=rows.map((d,i)=>({x:xx(i),y:yy(d[key]),valid:hasNumber(d[key]),d}));
      if(chart.type==='line'){let path='',penDown=false;points.forEach(pt=>{if(!pt.valid){penDown=false;return;}path+=`${penDown?'L':'M'}${pt.x},${pt.y} `;penDown=true;});elements+=`<path d="${path}" fill="none" stroke="${color}" stroke-width="${compact?2:2.5}" stroke-linejoin="round"/>`;}
      points.filter(pt=>pt.valid).forEach(pt=>{elements+=`<circle cx="${pt.x}" cy="${pt.y}" r="${compact?2.5:3.5}" fill="${color}" stroke="${dark?'#132d38':'white'}" stroke-width="1.5"><title>${escape(pt.d[xKey])} · ${escape(label(key))}：${escape(valueText(pt.d[key]))}${escape({count:'人',CNY:'元',ratio:'比例'}[chart.unit]||chart.unit||'')}</title></circle>`;});
    }else{
      const groupWidth=Math.min(step*.67,70),barWidth=groupWidth/ys.length;
      rows.forEach((d,i)=>{const v=Number(d[key]);if(!hasNumber(d[key]))return;const top=Math.min(yy(v),yy(0)),height=Math.max(Math.abs(yy(v)-yy(0)),.8),x=xx(i)-groupWidth/2+s*barWidth;elements+=`<rect x="${x}" y="${top}" width="${Math.max(barWidth-2,2)}" height="${height}" rx="2" fill="${color}"><title>${escape(d[xKey])} · ${escape(label(key))}：${escape(valueText(d[key]))}${escape({count:'人',CNY:'元',ratio:'比例'}[chart.unit]||chart.unit||'')}</title></rect>`;});
    }
  });
  return `<svg class="data-chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="${escape(chart.title||'分析图表')}"><title>${escape(chart.title||'分析图表')}，${escape(chart.unit||'数值')}。具体数据见下方证据表。</title>${elements}</svg>${!compact&&data.length>rows.length?`<p class="field-help" style="padding:0 18px 10px">图表展示前 ${rows.length} 条，共 ${data.length} 条。完整数据请查看结果表与报告。</p>`:''}${compact?'':`<div class="chart-legend">${ys.map((key,i)=>`<span><i style="background:${colors[i%colors.length]}"></i>${escape(label(key))}${chart.unit&&!label(key).includes(chart.unit)?` · ${escape({count:'人',CNY:'元',ratio:'比例'}[chart.unit]||chart.unit)}`:''}</span>`).join('')}</div>`}`;
}
