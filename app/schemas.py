from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    question: str = Field(min_length=1, max_length=1500)
    domain: Literal['growth', 'repurchase'] = 'growth'
    task: Literal['diagnose','experiment','report','segment'] | None = None
    start: str | None = None
    end: str | None = None
    compare_start: str | None = None
    compare_end: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    mode: Literal['demo','live'] = 'demo'

class SQLRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    domain: Literal['growth','repurchase']
    sql: str = Field(min_length=1,max_length=6000)
