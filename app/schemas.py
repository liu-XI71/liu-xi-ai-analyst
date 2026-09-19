from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    question: str = Field(min_length=1, max_length=1500)
    domain: Literal['growth', 'repurchase', 'onboarding', 'experiments'] = 'onboarding'
    task: Literal['diagnose','experiment','report','segment','funnel','quality'] | None = None
    start: str | None = None
    end: str | None = None
    compare_start: str | None = None
    compare_end: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    mode: Literal['demo','live'] = 'demo'

class SQLRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    domain: Literal['growth','repurchase','onboarding','experiments']
    sql: str = Field(min_length=1,max_length=6000)

class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    run_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    feedback_token: str = Field(min_length=20,max_length=100)
    outcome: Literal['useful','needs_revision','incorrect','not_completed']
    failure_category: Literal['none','understanding','metric','time_window','tool','evidence','delivery'] = 'none'
    human_minutes: float | None = Field(default=None,ge=0,le=480)

class MonitorRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    scenario: Literal['business_drop','late_data','recovered'] = 'business_drop'
