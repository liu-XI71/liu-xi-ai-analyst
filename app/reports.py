"""Standalone reports preserve every result row and every chart series."""
from __future__ import annotations
import html
import json
import math

MISSING = "未成熟/缺失"
COLORS = ("#147d92", "#d86c31", "#6b5ca5", "#357c57", "#ad5077")
SERIES_LABELS = {
    "previous_pct": "对照期", "current_pct": "本期", "rate7": "次7日内复购率",
    "rate30": "次30日内复购率", "retention_pct": "次7日内留存率",
    "contribution_pp": "变化贡献", "cost_per_user": "人均激励成本",
    "revenue_per_user": "人均7日收入", "customers": "客户数",
}

def _esc(value):
    return html.escape(str(value), quote=True)

def _numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

def _value(value, unit=""):
    if value is None or isinstance(value, float) and not math.isfinite(value):
        return MISSING
    if _numeric(value) and unit in ("ratio", "%"):
        number = value * 100 if unit == "ratio" else value
        return f"{number:.4f}".rstrip("0").rstrip(".") + "%"
    return str(value)

def _md_cell(value):
    return _value(value).replace("|", "\\|").replace("\n", " ")

def _table_html(columns, rows):
    head = "".join(f"<th>{_esc(col)}</th>" for col in columns)
    body = "".join("<tr>" + "".join(f"<td>{_esc(_value(row.get(col)))}</td>" for col in columns) + "</tr>" for row in rows)
    return f'<div class="overflow"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'

def markdown_report(run: dict) -> str:
    fence = chr(96) * 3
    lines = [f"# {run.get('title', '分析报告')}", "", f"运行编号：{run.get('run_id', '—')} · 模式：{run.get('mode', 'demo')} · 时间：{run.get('created_at', '—')}", "", "**数据说明：合成演示数据，不代表任何企业真实经营结果。**", "", run.get("summary", "")]
    for key,label in [('decision','决策备忘录'),('data_quality','数据质量'),('experiment_contract','实验设计'),('hypotheses','假设与验证'),('plan','分析步骤')]:
        if run.get(key):lines += ['',f'## {label}','',fence+'json',json.dumps(run[key],ensure_ascii=False,indent=2),fence]
    lines += ["", "## 指标口径", "", fence+"json", json.dumps(run.get("metric_contract", {}), ensure_ascii=False, indent=2), fence]
    for kind, label in (("fact", "核验事实"), ("hypothesis", "待验证假设"), ("action", "后续行动")):
        lines += ["", f"## {label}", ""]
        lines += [f"- {item['text']}（证据：{', '.join(item.get('evidence_ids', [])) or '流程建议'}）" for item in run.get("findings", []) if item.get("kind") == kind]
    lines += ["", "## 结果表", ""]
    for table in run.get("tables", []):
        cols, rows = table.get("columns", []), table.get("rows", [])
        lines += [f"### {table.get('title', '结果')}", "", f"完整结果：{len(rows)}行。", "", "| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
        lines += ["| " + " | ".join(_md_cell(row.get(col)) for col in cols) + " |" for row in rows]
    for chart in run.get("charts", []):
        columns = [chart.get("x_key", ""), *chart.get("y_keys", [])]
        lines += ["", f"### 图表数据：{chart.get('title', '图表')}", "", f"原始单位：{chart.get('unit', '未指定')}；空值表示{MISSING}。", "", "| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
        lines += ["| " + " | ".join(_md_cell(row.get(col)) for col in columns) + " |" for row in chart.get("data", [])]
    lines += ["", "## SQL 与证据", ""]
    for evidence in run.get("evidence", []):
        lines += [f"### {evidence.get('id')} · {evidence.get('label', '查询')}", "", f"来源：{evidence.get('source', '演示数据库')}；口径版本：{evidence.get('metric_version', '—')}", "", fence+"sql", evidence.get("sql", ""), fence, "参数：" + json.dumps(evidence.get("parameters", {}), ensure_ascii=False)]
    lines += ["", "## 边界与限制", ""] + ["- " + str(item) for item in run.get("limitations", [])]
    lines += ["", "## 执行记录", ""] + ["- " + item.get("tool", "") + "：" + item.get("description", "") for item in run.get("trace", [])]
    if run.get('provenance'):lines += ['', '## 版本与来源', '', fence+'json',json.dumps(run['provenance'],ensure_ascii=False,indent=2),fence]
    return "\n".join(lines) + "\n"


def _decision_html(run):
    decision=run.get('decision') or {}
    if not decision:return ''
    label=decision.get('label',decision.get('status','决策建议'))
    detail=''.join(f'<p>{_esc(decision[k])}</p>' for k in ['reason','action','review_trigger'] if decision.get(k))
    actions=decision.get('actions',[])
    if isinstance(actions,list):detail+='<ul>'+''.join('<li>'+_esc(x)+'</li>' for x in actions)+'</ul>'
    return f'<h2>决策备忘录</h2><section class="decision"><h3>{_esc(label)}</h3>{detail}</section>'


def _audit_html(run):
    blocks=[]
    for key,label in [('data_quality','数据质量'),('experiment_contract','实验设计'),('hypotheses','假设与区分性验证'),('plan','分析步骤'),('provenance','版本与来源')]:
        if run.get(key):blocks.append(f'<details><summary>{label}</summary><pre>{_esc(json.dumps(run[key],ensure_ascii=False,indent=2))}</pre></details>')
    return ''.join(blocks)

def _svg_chart(chart: dict) -> str:
    data, series = chart.get("data", []), chart.get("y_keys", [])
    if not data or not series:
        return ""
    unit, x_key = chart.get("unit", ""), chart.get("x_key", "")
    title = _esc(chart.get("title", "图表"))
    legend_rows = math.ceil(len(series) / 3)
    parts = ["".join(f'<rect x="{(i % 3) * 235}" y="{(i // 3) * 24 + 4}" width="12" height="12" fill="{COLORS[i % len(COLORS)]}"/><text x="{(i % 3) * 235 + 18}" y="{(i // 3) * 24 + 15}" font-size="12">{_esc(SERIES_LABELS.get(key, key))}</text>' for i, key in enumerate(series))]
    numeric = [float(row[key]) for row in data for key in series if _numeric(row.get(key))]
    chart_top = legend_rows * 24 + 18
    if not numeric:
        parts.append(f'<text x="0" y="{chart_top + 24}" font-size="14">没有可绘制的成熟观测值；{MISSING}不代表0。</text>')
        height = chart_top + 60
    elif chart.get("type") == "line":
        left, right, plot_height = 75, 680, 230
        low, high = min([0.0, *numeric]), max([0.0, *numeric])
        if low == high:
            high = low + 1
        x = lambda index: left + (right - left) * index / max(1, len(data) - 1)
        y = lambda value: chart_top + plot_height * (high - value) / (high - low)
        for step in range(5):
            tick = low + (high - low) * step / 4
            parts.append(f'<line x1="{left}" y1="{y(tick)}" x2="{right}" y2="{y(tick)}" stroke="#dce5eb"/><text x="0" y="{y(tick) + 4}" font-size="11">{_esc(_value(round(tick, 4), unit))}</text>')
        label_step = max(1, math.ceil(len(data) / 6))
        for index, row in enumerate(data):
            if index % label_step == 0 or index == len(data) - 1:
                parts.append(f'<text x="{x(index)}" y="{chart_top + plot_height + 22}" text-anchor="middle" font-size="10">{_esc(str(row.get(x_key, ""))[:18])}</text>')
        for series_index, key in enumerate(series):
            color, segment = COLORS[series_index % len(COLORS)], []
            for index, row in enumerate(data):
                value = row.get(key)
                if not _numeric(value):
                    if segment:
                        parts.append(f'<polyline data-series="{_esc(key)}" points="{" ".join(segment)}" stroke="{color}" stroke-width="2" fill="none"/>')
                    segment = []
                    continue
                segment.append(f"{x(index)},{y(float(value))}")
                parts.append(f'<circle data-series="{_esc(key)}" cx="{x(index)}" cy="{y(float(value))}" r="3" fill="{color}"><title>{_esc(row.get(x_key, ""))} · {_esc(SERIES_LABELS.get(key, key))}：{_esc(_value(value, unit))}</title></circle>')
            if segment:
                parts.append(f'<polyline data-series="{_esc(key)}" points="{" ".join(segment)}" stroke="{color}" stroke-width="2" fill="none"/>')
        height = chart_top + plot_height + 48
    else:
        left, right, row_height = 150, 595, 24
        low, high = min([0.0, *numeric]), max([0.0, *numeric])
        if low == high:
            high = low + 1
        x = lambda value: left + (right - left) * (value - low) / (high - low)
        zero, group_height = x(0), len(series) * row_height + 14
        height = chart_top + len(data) * group_height + 10
        parts.append(f'<line x1="{zero}" y1="{chart_top}" x2="{zero}" y2="{height - 10}" stroke="#aab9c2"/>')
        for index, row in enumerate(data):
            group_top = chart_top + index * group_height
            parts.append(f'<text x="0" y="{group_top + 15}" font-size="11">{_esc(str(row.get(x_key, ""))[:22])}</text>')
            for series_index, key in enumerate(series):
                value, top = row.get(key), group_top + series_index * row_height
                if _numeric(value):
                    point = x(float(value))
                    parts.append(f'<rect data-series="{_esc(key)}" x="{min(zero, point)}" y="{top}" width="{abs(point - zero)}" height="16" rx="2" fill="{COLORS[series_index % len(COLORS)]}"/>')
                    parts.append(f'<text x="{max(zero, point) + 7}" y="{top + 13}" font-size="11">{_esc(_value(value, unit))}</text>')
                else:
                    parts.append(f'<text data-series="{_esc(key)}" x="{left + 7}" y="{top + 13}" font-size="11">{MISSING}</text>')
    fallback = _table_html([x_key, *series], data)
    return f'<h3>{title}</h3><svg viewBox="0 0 760 {height}" role="img" aria-label="{title}"><title>{title}</title>{"".join(parts)}</svg><p class="meta">{MISSING}不代表0。图表原始单位：{_esc(unit or "未指定")}。</p><details><summary>查看完整图表数据（{len(data)}行）</summary>{fallback}</details>'

def html_report(run: dict) -> str:
    cards = "".join(f'<article><span>{_esc(kpi.get("label", ""))}</span><strong>{_esc(_value(kpi.get("value"), kpi.get("unit", "")))} {_esc("" if kpi.get("unit") in ("ratio", "%") else kpi.get("unit", ""))}</strong></article>' for kpi in run.get("kpis", []))
    findings = "".join(f'<li><b>{_esc({"fact": "事实", "hypothesis": "假设", "action": "行动"}.get(item.get("kind"), "说明"))}</b> {_esc(item.get("text", ""))}<small>{_esc(", ".join(item.get("evidence_ids", [])))}</small></li>' for item in run.get("findings", []))
    tables = "".join(f'<h3>{_esc(table.get("title", "结果"))}</h3><p class="meta">完整结果：{len(table.get("rows", []))}行。</p>' + _table_html(table.get("columns", []), table.get("rows", [])) for table in run.get("tables", []))
    evidence = "".join(f'<details id="{_esc(item.get("id"))}"><summary>{_esc(item.get("id"))} · {_esc(item.get("label", "查询"))}</summary><pre>{_esc(item.get("sql", ""))}</pre><pre>{_esc(json.dumps(item.get("parameters", {}), ensure_ascii=False))}</pre><p>{_esc(item.get("source", ""))} · {_esc(item.get("metric_version", ""))}</p><pre>{_esc(json.dumps(item.get("rows", []),ensure_ascii=False,indent=2))}</pre></details>' for item in run.get("evidence", []))
    charts = "".join(_svg_chart(chart) for chart in run.get("charts", []))
    limitations = "".join("<li>" + _esc(item) + "</li>" for item in run.get("limitations", []))
    return f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{_esc(run.get('title', '分析报告'))}</title><style>body{{font:16px/1.7 system-ui,sans-serif;color:#152b3c;max-width:1100px;margin:40px auto;padding:0 24px}}h1{{font-size:32px}}h2{{margin-top:40px;border-top:1px solid #dce5eb;padding-top:24px}}.meta,small{{color:#596c7c}}small{{display:block}}.kpis{{display:flex;gap:16px;flex-wrap:wrap}}article,.decision{{background:#f0f5f7;padding:18px;min-width:140px;border-radius:12px}}strong{{display:block;font-size:24px}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:9px;text-align:left;border-bottom:1px solid #dce5eb}}.overflow{{overflow:auto}}pre{{background:#eef3f7;overflow:auto;padding:14px;white-space:pre-wrap;overflow-wrap:anywhere}}details{{padding:12px 0;border-bottom:1px solid #dce5eb}}svg{{width:100%;max-width:950px}}@media print{{details{{display:block}}body{{margin:0}}tr{{break-inside:avoid}}}}</style><header><p>刘希 · AI 数据分析工作台</p><h1>{_esc(run.get('title', '分析报告'))}</h1><p class="meta">{_esc(run.get('run_id', ''))} · {_esc(run.get('mode', 'demo'))} · {_esc(run.get('created_at', ''))}</p><p>合成演示数据，不代表任何企业实际经营结果。</p></header><p>{_esc(run.get('summary', ''))}</p><section class="kpis">{cards}</section>{_decision_html(run)}<h2>事实、假设与行动</h2><ul>{findings}</ul><h2>图表与结果</h2>{charts}{tables}<h2>指标口径与分析合同</h2><pre>{_esc(json.dumps(run.get('metric_contract', {}), ensure_ascii=False, indent=2))}</pre>{_audit_html(run)}<h2>SQL 与证据</h2>{evidence}<h2>适用边界</h2><ul>{limitations}</ul></html>'''
