"""Verify new-domain tool contracts with a test double, never provider accuracy."""
import json
from types import SimpleNamespace

import pytest

from app import engine, live_agent


class ScriptedResponses:
    def __init__(self, calls):
        self.script = iter(calls)
        self.requests = []

    def create(self, **request):
        self.requests.append(request)
        name, arguments = next(self.script)
        return SimpleNamespace(
            output=[SimpleNamespace(type='function_call', name=name,
                                    arguments=json.dumps(arguments), call_id=f'test-{len(self.requests)}')],
            usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        )


@pytest.mark.parametrize('scenario,expected', [('business_drop', 'completed'), ('late_data', 'data_quality_blocked')])
def test_onboarding_tool_protocol_preserves_quality_gate(scenario, expected):
    engine.initialize()
    filters = {'scenario': scenario, 'metric': 'new_user_retention_d7'}
    provider = ScriptedResponses([
        ('get_business_context', {}),
        ('get_metric_contract', {'metric_id': 'new_user_retention_d7'}),
        ('register_analysis_plan', {'steps': ['metric_contract', 'data_quality', 'cohort_comparison', 'evidence_report']}),
        ('check_data_quality', {}),
        ('analyze_business', {'task': 'diagnose', 'start': None, 'end': None,
                              'compare_start': None, 'compare_end': None, 'filters': filters}),
        ('finish_report', {'finding_indices': []}),
    ])
    result = live_agent.execute({'domain': 'onboarding', 'question': '检查精确D7留存与数据质量', 'filters': filters},
                                client=SimpleNamespace(responses=provider))
    assert result['status'] == expected
    assert result['registered_plan'][1] == 'data_quality'
    assert result['model_run']['provider'] == 'test-double'
    assert result['model_run']['live_verified'] is False
    assert result['model_run']['rounds'] == 6
    if expected == 'data_quality_blocked':
        assert not result['kpis']
        assert result['data_quality']['status'] == 'blocked'
    else:
        assert result['kpis'][0]['value'] == pytest.approx(191 / 898 * 100, abs=0.0005)


@pytest.mark.parametrize('scenario,decision', [('guardrail', 'stop_or_adjust'), ('srm', 'invalid_data')])
def test_experiment_protocol_cannot_turn_failed_gate_into_rollout(scenario, decision):
    engine.initialize()
    filters = {'scenario': scenario}
    provider = ScriptedResponses([
        ('get_business_context', {}),
        ('register_analysis_plan', {'steps': ['metric_contract', 'experiment_review', 'evidence_report']}),
        ('analyze_business', {'task': 'experiment', 'start': None, 'end': None,
                              'compare_start': None, 'compare_end': None, 'filters': filters}),
        ('finish_report', {'finding_indices': []}),
    ])
    result = live_agent.execute({'domain': 'experiments', 'question': '评审实验是否满足灰度条件', 'filters': filters},
                                client=SimpleNamespace(responses=provider))
    assert result['decision']['code'] == decision
    assert result['decision']['executes_rollout'] is False
    assert result['model_run']['live_verified'] is False


def test_business_tool_rejected_until_context_is_loaded():
    provider = ScriptedResponses([('finish_report', {'finding_indices': []})] * 3)
    with pytest.raises(live_agent.ModelUnavailable, match='连续'):
        live_agent.execute({'domain': 'onboarding', 'question': '分析D7留存'},
                           client=SimpleNamespace(responses=provider))
