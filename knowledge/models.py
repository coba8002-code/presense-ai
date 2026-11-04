"""Operator policy is distinct from untrusted model evidence."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator

Text = Annotated[str, Field(min_length=1, max_length=1200)]
Channel = Annotated[str, Field(pattern=r'^UC[A-Za-z0-9_-]{22}$')]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Policy(StrictModel):
    analysis_allowed: bool = False
    knowledge_allowed: bool = False
    notebook_allowed: bool = False
    evidence: Text
    expires_at: int = Field(gt=0)


class Config(StrictModel):
    queries: list[Annotated[str, Field(min_length=1, max_length=150)]] = Field(min_length=1, max_length=4)
    video_ids: list[Annotated[str, Field(pattern=r'^[A-Za-z0-9_-]{11}$')]] = Field(default_factory=list, max_length=20)
    targeted_only: bool = False
    policies: dict[Channel, Policy] = Field(default_factory=dict, max_length=100)
    gemini_model: str = Field(default='gemini-2.5-flash', pattern=r'^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$')
    daily_requests: int = Field(default=20, ge=1, le=1000)
    max_videos: int = Field(default=5, ge=1, le=20)
    max_duration_seconds: int = Field(default=600, ge=1, le=1800)
    retention_days: int = Field(default=7, ge=1, le=30)
    interval_seconds: int = Field(default=3600, ge=300, le=86400)
    notebook: str | None = Field(default=None, pattern=r'^projects/[0-9]+/locations/(global|us|eu)/notebooks/[A-Za-z0-9_-]+$')
    notebook_endpoint: Literal['global', 'us', 'eu'] = 'global'

    @field_validator('video_ids')
    @classmethod
    def unique_ids(cls, value):
        if len(set(value)) != len(value):
            raise ValueError('Distinct video IDs required')
        return value

    @model_validator(mode='after')
    def target_required(self):
        if self.targeted_only and not self.video_ids:
            raise ValueError('Targeted intake requires explicit video IDs')
        return self


class Entry(StrictModel):
    start_seconds: int = Field(ge=0, le=1800)
    end_seconds: int = Field(ge=0, le=1800)
    kind: Literal['observation', 'speaker_statement', 'hypothesis']
    text: Text
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)

    @model_validator(mode='after')
    def ordered(self):
        if self.end_seconds < self.start_seconds:
            raise ValueError('Invalid timestamp order')
        return self


class Analysis(StrictModel):
    species: Literal['dog', 'cat', 'unknown']
    entries: list[Entry] = Field(max_length=12)
