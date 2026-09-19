"""Isolated API-to-report contract checks, using explicit provider test doubles.

No test here calls a real model or measures natural-language model accuracy.
Each test patches every mutable data-directory binding before application start.
"""
import copy
import html
import json
import sqlite3
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient


class ScriptedResponses:
    def __init__(self, steps):
        self.steps = iter(steps)
        self.requests = []

    def create(self, **request):
        self.requests.append(copy.deepcopy(request))
        step = next(self.steps)
        if isinstance(step, Exception):
            raise step
        name, arguments = step
        return SimpleNamespace(
            output=[SimpleNamespace(type="function_call", name=name,
                                    arguments=json.dumps(arguments), call_id=f"chain-{len(self.requests)}")],
            usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        )


@pytest.fixture()
def chain_api(tmp_path, monkeypatch):
    # Avoid reading a developer's local credential file even when run independently.
    with patch("dotenv.load_dotenv", return_value=False):
        from app import config, engine, live_agent, main, monitoring, telemetry
    monkeypatch.setenv("ANALYST_DATA_DIR", str(tmp_path))
    for name in ("OPENAI_API_KEY", "LIVE_ACCESS_TOKEN", "ANALYST_ADMIN_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    for module in (config, engine, main, monitoring, telemetry):
        monkeypatch.setattr(module, "VAR", tmp_path)

    def prohibit_real_client(*args, **kwargs):
        raise AssertionError("Chain tests must not construct a real provider client")

    monkeypatch.setattr(live_agent, "OpenAI", prohibit_real_client)
    main.limits.clear()
    with TestClient(main.app) as client:
        yield SimpleNamespace(client=client, engine=engine, live=live_agent,
                              main=main, telemetry=telemetry, directory=tmp_path)


def request_payload(**overrides):
    return {
        "domain": "onboarding", "mode": "live", "task": "diagnose",
        "question": "比较两个成熟注册周的精确 D7 留存，给出有证据的增长诊断。",
        "start": "2026-08-24", "end": "2026-08-30",
        "compare_start": "2026-08-17", "compare_end": "2026-08-23",
        "filters": {"metric": "new_user_retention_d7", "scenario": "business_drop"},
        **overrides,
    }


def tool_arguments(context, payload, **changes):
    # Match the strict tool schema, including optional properties represented by null.
    schema = next(item for item in context.live.tools_schema() if item["name"] == "analyze_business")
    fields = schema["parameters"]["properties"]["filters"]["properties"]
    arguments = {key: payload.get(key) for key in ("task", "start", "end", "compare_start", "compare_end")}
    arguments["filters"] = {key: payload.get("filters", {}).get(key) for key in fields}
    arguments.update(changes)
    return arguments


def install_provider(context, monkeypatch, steps):
    provider = ScriptedResponses(steps)
    execute = context.live.execute
    monkeypatch.setattr(context.live, "execute", lambda payload: execute(payload, client=SimpleNamespace(responses=provider)))
    return provider


def plan():
    return ("register_analysis_plan", {"steps": ["metric_contract", "data_quality", "cohort_comparison", "evidence_report"]})


def saved_run_count(context):
    with sqlite3.connect(context.directory / "runs.sqlite3") as connection:
        return connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0]


def assert_failure_without_result(context, response):
    assert response.status_code == 503
    assert "kpis" not in response.json() and "evidence" not in response.json()
    assert saved_run_count(context) == 0
    failure_id = response.headers["X-Analysis-Run-Id"]
    assert context.client.get(f"/api/v1/runs/{failure_id}").status_code == 404
    assert context.client.get(f"/api/v1/runs/{failure_id}/report").status_code == 404
    with sqlite3.connect(context.directory / "telemetry.sqlite3") as connection:
        status, stage = connection.execute("SELECT status,failure_stage FROM task_event WHERE run_id=?", (failure_id,)).fetchone()
    assert status == "failed" and stage


def assert_saved_evidence_and_reports(context, result):
    loaded = context.client.get(f"/api/v1/runs/{result['run_id']}").json()
    assert loaded == {key: value for key, value in result.items() if key != "feedback_token"}
    assert "feedback_token" not in loaded
    assert loaded["provenance"]["data_kind"] == "synthetic"
    evidence_ids = {item["id"] for item in loaded["evidence"]}
    for item in loaded["findings"]:
        assert item["evidence_ids"]
        assert set(item["evidence_ids"]) <= evidence_ids
    # Onboarding KPI/chart objects do not declare evidence_ids. Check their
    # numeric aggregate against replayable SQL rather than assuming that field.
    totals = next((item["rows"] for item in loaded["evidence"] if item["id"] == "onboarding-totals"), [])
    if totals:
        periods = {row["period"]: row for row in totals}
        current, previous = periods["current"], periods["previous"]
        metrics = {item["id"]: item for item in loaded["kpis"]}
        assert metrics["new_user_retention_d7"]["value"] == pytest.approx(current["d7"] / current["users"] * 100, abs=0.0005)
        assert metrics["new_user_retention_d7"]["previous"] == pytest.approx(previous["d7"] / previous["users"] * 100, abs=0.0005)
        assert metrics["new_registered_users"]["value"] == current["users"]
        strata = next(item["rows"] for item in loaded["evidence"] if item["id"] == "onboarding-strata")
        grouped = {}
        for row in strata:
            grouped.setdefault((row["channel"], row["device"]), {})[row["period"]] = row
        mix = performance = 0
        for rows in grouped.values():
            now, prior = rows["current"], rows["previous"]
            now_weight, prior_weight = now["users"] / current["users"], prior["users"] / previous["users"]
            now_rate, prior_rate = now["retained_users"] / now["users"], prior["retained_users"] / prior["users"]
            mix += (now_weight-prior_weight) * (now_rate+prior_rate) / 2 * 100
            performance += (now_rate-prior_rate) * (now_weight+prior_weight) / 2 * 100
        assert metrics["mix_pp"]["value"] == pytest.approx(mix, abs=0.0005)
        assert metrics["performance_pp"]["value"] == pytest.approx(performance, abs=0.0005)
    with sqlite3.connect(context.engine.database(loaded["domain"])) as connection:
        connection.row_factory = sqlite3.Row
        for evidence in loaded["evidence"]:
            replay = [dict(row) for row in connection.execute(evidence["sql"], evidence.get("parameters", {}))]
            assert replay == evidence["rows"], evidence["id"]
    report_bodies = {}
    for format_name in ("html", "md"):
        response = context.client.get(f"/api/v1/runs/{result['run_id']}/report?format={format_name}")
        assert response.status_code == 200
        assert "attachment;" in response.headers["Content-Disposition"]
        assert "合成演示数据" in response.text and result["run_id"] in response.text
        normalized = html.unescape(response.text) if format_name == "html" else response.text
        assert result["summary"] in normalized
        for finding in result["findings"]:
            assert finding["text"] in normalized
            assert all(evidence_id in normalized for evidence_id in finding.get("evidence_ids", []))
        for evidence in result["evidence"]:
            assert evidence["sql"] in normalized
        report_bodies[format_name] = response.text
    return report_bodies


def test_demo_executes_python_without_model_then_reads_back_immutable_reports(chain_api, monkeypatch):
    def forbid_live(*args, **kwargs):
        raise AssertionError("Demo must not enter the provider loop")
    monkeypatch.setattr(chain_api.live, "execute", forbid_live)
    response = chain_api.client.post("/api/v1/analyze", json=request_payload(mode="demo"))
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed" and result["mode"] == "demo"
    assert "model_run" not in result
    assert result["trace"][0]["tool"] == "demo_intent_router"
    assert "未调用" in result["trace"][0]["description"] and "模型" in result["trace"][0]["description"]
    reports = assert_saved_evidence_and_reports(chain_api, result)
    # Exports are rendered from the stored run, not recomputed on newer data.
    with sqlite3.connect(chain_api.engine.database("onboarding")) as connection:
        connection.execute("DELETE FROM onboarding_events")
    for format_name, before in reports.items():
        after = chain_api.client.get(f"/api/v1/runs/{result['run_id']}/report?format={format_name}")
        assert after.text == before
    assert chain_api.client.get(f"/api/v1/runs/{result['run_id']}").json()["kpis"] == result["kpis"]


def test_missing_key_explicitly_fails_without_demo_fallback(chain_api):
    assert chain_api.client.get("/api/v1/catalog").json()["model"]["configured"] is False
    response = chain_api.client.post("/api/v1/analyze", json=request_payload())
    assert "未使用演示结果代替" in response.json()["detail"]
    assert_failure_without_result(chain_api, response)
    assert chain_api.client.get("/api/v1/usage").json()["failures"] == [
        {"stage": "configuration", "kind": "missing_api_key", "count": 1}
    ]


def test_live_protocol_double_reaches_sql_python_evidence_and_reports(chain_api, monkeypatch):
    payload = request_payload(filters={"scenario": "business_drop", "metric": "new_user_retention_d7", "app_version": ["1.8.0", "1.9.0"]})
    provider = install_provider(chain_api, monkeypatch, [
        ("get_business_context", {}),
        ("get_metric_contract", {"metric_id": "new_user_retention_d7"}),
        # Independent quality checks are valid before registering the analysis plan.
        ("check_data_quality", {}), plan(),
        ("query_readonly_sql", {"sql": "SELECT COUNT(*) AS events FROM onboarding_events"}),
        ("analyze_business", tool_arguments(chain_api, payload)),
        ("finish_report", {"finding_indices": [0]}),
    ])
    response = chain_api.client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed" and result["request"] == payload
    assert result["model_run"]["provider"] == "test-double"
    assert result["model_run"]["live_verified"] is False
    assert result["model_run"]["sql_generation"] == "model"
    assert result["model_run"]["usage"] == {"input_tokens": 70, "output_tokens": 35}
    assert result["registered_plan"] == plan()[1]["steps"]
    assert any(item["id"] == "AIQ01" for item in result["evidence"])
    assert all(request["store"] is False and request["parallel_tool_calls"] is False for request in provider.requests)
    outputs = [item for item in provider.requests[-1]["input"] if isinstance(item, dict) and item.get("type") == "function_call_output"]
    assert any(json.loads(item["output"]).get("status") == "completed" for item in outputs)
    assert_saved_evidence_and_reports(chain_api, result)


@pytest.mark.parametrize("changed", ["task", "start", "filters"])
def test_model_cannot_rewrite_explicit_task_dates_or_filters(chain_api, monkeypatch, changed):
    payload = request_payload(task="quality", question="只检查数据质量，不输出业务诊断。")
    arguments = tool_arguments(chain_api, payload)
    if changed == "task":
        arguments["task"] = "diagnose"
    elif changed == "start":
        arguments["start"] = "2026-08-25"
    else:
        arguments["filters"]["metric"] = "new_user_retention_d1"
    install_provider(chain_api, monkeypatch, [
        ("get_business_context", {}), plan(),
        *[("analyze_business", arguments)] * 3,
    ])
    response = chain_api.client.post("/api/v1/analyze", json=payload)
    assert_failure_without_result(chain_api, response)
    assert "连续" in response.json()["detail"]


def test_model_without_registered_plan_cannot_finish_business_analysis(chain_api, monkeypatch):
    payload = request_payload()
    install_provider(chain_api, monkeypatch, [
        ("get_business_context", {}),
        *[("analyze_business", tool_arguments(chain_api, payload))] * 3,
    ])
    response = chain_api.client.post("/api/v1/analyze", json=payload)
    assert_failure_without_result(chain_api, response)


def test_provider_failure_after_context_has_no_business_result_or_demo_fallback(chain_api, monkeypatch):
    timeout = chain_api.live.APITimeoutError(request=httpx.Request("POST", "https://provider-test.invalid/responses"))
    install_provider(chain_api, monkeypatch, [("get_business_context", {}), timeout])
    response = chain_api.client.post("/api/v1/analyze", json=request_payload())
    assert_failure_without_result(chain_api, response)
    with sqlite3.connect(chain_api.directory / "telemetry.sqlite3") as connection:
        usage = connection.execute("SELECT usage_status,input_tokens,output_tokens FROM task_event").fetchone()
    assert usage == ("partial", 10, 5)


def test_valid_live_quality_chain_keeps_business_output_blocked_for_late_data(chain_api, monkeypatch):
    payload = request_payload(filters={"scenario": "late_data", "metric": "new_user_retention_d7"})
    install_provider(chain_api, monkeypatch, [
        ("get_business_context", {}), ("check_data_quality", {}), plan(),
        ("analyze_business", tool_arguments(chain_api, payload)),
        ("finish_report", {"finding_indices": []}),
    ])
    response = chain_api.client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "data_quality_blocked"
    assert result["data_quality"]["status"] == "blocked"
    assert result["kpis"] == []
    assert result["model_run"]["live_verified"] is False
    assert_saved_evidence_and_reports(chain_api, result)


@pytest.mark.parametrize("conditions", [
    {"question": "只分析 iOS 设备，在 2026-08-10 至 2026-08-16 注册的新用户精确 D7 留存。", "filters": {}},
    {"question": "只分析 iOS 设备的精确 D7 留存。", "start": "2026-08-24", "end": "2026-08-30", "filters": {"device": "android", "metric": "new_user_retention_d7"}},
    {"question": "分析 2026-08-10 至 2026-08-16 注册用户的精确 D7 留存。", "start": "2026-08-24", "end": "2026-08-30", "filters": {"metric": "new_user_retention_d7"}},
])
def test_demo_does_not_silently_ignore_textual_date_or_device_conditions(chain_api, conditions):
    response = chain_api.client.post("/api/v1/analyze", json={
        "domain": "onboarding", "mode": "demo", "task": "diagnose", **conditions,
    })
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "needs_clarification"
    assert result["clarification"]["question"]
    assert result["kpis"] == [] and result["evidence"] == [] and result["charts"] == []
    assert "model_run" not in result


def test_demo_accepts_explicit_text_conditions_matching_form_parameters(chain_api):
    payload = request_payload(
        mode="demo", question="只分析 iOS 设备，在 2026-08-24 至 2026-08-30 注册的新用户精确 D7 留存。",
        filters={"device": "ios", "metric": "new_user_retention_d7", "scenario": "business_drop"},
    )
    response = chain_api.client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed"
    assert result["metric_contract"]["current_period"] == ["2026-08-24", "2026-08-30"]
    scope = next(item for item in result["evidence"] if item["id"] == "onboarding-cohort-scope")
    assert scope["parameters"]["filter_device_0"] == "ios"


@pytest.mark.parametrize("filters,expected", [
    ({}, "needs_clarification"),
    ({"budget": 200}, "needs_clarification"),
    ({"budget": 300}, "completed"),
])
def test_demo_budget_text_requires_matching_structured_budget(chain_api, filters, expected):
    response = chain_api.client.post("/api/v1/analyze", json={
        "domain": "repurchase", "mode": "demo", "task": "segment",
        "question": "在 300 元预算内制定复购召回分群与留出计划。", "filters": filters,
    })
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == expected
    if expected == "needs_clarification":
        assert result["kpis"] == [] and result["evidence"] == []
        assert "预算" in result["clarification"]["question"]
    else:
        assert result["request"]["filters"]["budget"] == 300
        assert result["metric_contract"]["allocation"]["budget"] == 300
