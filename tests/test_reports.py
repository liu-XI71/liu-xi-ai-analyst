import re
from app import reports
from app.domains import growth, repurchase


def chart_svg(document, title):
    return re.search(r'<h3>' + re.escape(title) + r'</h3><svg.*?</svg>', document).group(0)


def test_growth_comparisons_export_both_series(tmp_path):
    path = tmp_path / "growth.sqlite3"
    growth.build_database(path)
    run = growth.analyze({"task": "report"}, path)
    document = reports.html_report(run)
    for chart in run["charts"]:
        if len(chart["y_keys"]) < 2:
            continue
        svg = chart_svg(document, chart["title"])
        for key in chart["y_keys"]:
            assert len(re.findall(r'<rect data-series="' + key + '"', svg)) == len(chart["data"])
        assert "本期" in svg and "对照期" in svg


def test_all_null_mature_repurchases_never_export_as_zero(tmp_path):
    path = tmp_path / "repurchase.sqlite3"
    repurchase.build_database(path)
    run = repurchase.analyze({"task": "diagnose", "start": "2026-06-25", "end": "2026-06-30"}, path)
    assert run["status"] == "insufficient_data"
    document = reports.html_report(run)
    for chart in run["charts"]:
        svg = chart_svg(document, chart["title"])
        assert "没有可绘制的成熟观测值" in svg
        assert 'data-series=' not in svg
    assert "None" not in document
    assert "未成熟/缺失" in reports.markdown_report(run)


def test_partial_null_line_series_preserve_gaps_and_all_points():
    chart = {"title": "部分缺失", "type": "line", "x_key": "day", "y_keys": ["rate7", "rate30"], "unit": "ratio", "data": [{"day": "A", "rate7": 0.1, "rate30": 0.2}, {"day": "B", "rate7": None, "rate30": 0.3}, {"day": "C", "rate7": 0.4, "rate30": None}]}
    svg = chart_svg(reports.html_report({"charts": [chart]}), "部分缺失")
    assert svg.count('<circle data-series="rate7"') == 2
    assert svg.count('<circle data-series="rate30"') == 2
    assert svg.count('<polyline data-series="rate7"') == 2
    assert "10%" in svg and "30%" in svg


def test_full_178_candidate_plan_exports_in_both_formats(tmp_path):
    path = tmp_path / "repurchase.sqlite3"
    repurchase.build_database(path)
    run = repurchase.analyze({"task": "report", "filters": {"budget": 100000, "limit": 200}}, path)
    run["run_id"] = "review-run-178"
    rows = next(table["rows"] for table in run["tables"] if table["id"] == "rp-candidates-table")
    assert len(rows) > 100
    expected = {row["customer_id"] for row in rows}
    for document in (reports.html_report(run), reports.markdown_report(run)):
        assert set(re.findall(r'SYN-[0-9a-f]{10}', document)) == expected
        assert f"完整结果：{len(rows)}行" in document
        assert "review-run-178" in document


def test_chart_exports_preserve_rows_after_thirty_and_escape_text():
    chart = {"title": "完整序列", "type": "bar", "x_key": "item", "y_keys": ["value", "other"], "data": [{"item": f"row-{index}", "value": index, "other": index + 0.25} for index in range(41)]}
    chart["data"][-1]["item"] = "<script>alert(1)</script>"
    document = reports.html_report({"charts": [chart]})
    svg = chart_svg(document, "完整序列")
    assert svg.count('<rect data-series="value"') == 41
    assert svg.count('<rect data-series="other"') == 41
    assert "40.25" in svg
    assert "<script>" not in document
    assert "&lt;script&gt;" in document


def test_bar_keeps_null_distinct_from_real_zero():
    chart = {"title": "空值与零", "type": "bar", "x_key": "item", "y_keys": ["value"], "data": [{"item": "空", "value": None}, {"item": "零", "value": 0}, {"item": "负", "value": -2}]}
    svg = chart_svg(reports.html_report({"charts": [chart]}), "空值与零")
    assert svg.count('<rect data-series="value"') == 2
    assert 'font-size="11">未成熟/缺失</text>' in svg
    assert 'font-size="11">0</text>' in svg
    assert 'font-size="11">-2</text>' in svg
