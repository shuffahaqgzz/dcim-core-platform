"""Strict public contracts for deterministic analytics and RCA."""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_UTC_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
DomainName = Literal["compute", "memory", "storage", "network", "power", "cooling", "hardware"]
DomainTrend = Literal["increasing", "stable", "decreasing"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)


class AnalysisMode(StrEnum):
    REACTIVE = "reactive"
    FORWARD = "forward"
    HYBRID = "hybrid"


class LineageReference(_StrictModel):
    event_id: str
    step: str = Field(min_length=1)

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, value: str) -> str:
        return _validate_uuid4(value)


class AnalyticsIncident(_StrictModel):
    incident_id: str
    correlation_id: str
    observed_at: str
    active_domains: list[DomainName]
    domain_scores: dict[DomainName, float]
    lineage: list[LineageReference]
    mode: AnalysisMode = AnalysisMode.REACTIVE
    anomaly_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    drift_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    domain_persistence_ratio: dict[DomainName, float] = Field(default_factory=dict)
    domain_trend: dict[DomainName, DomainTrend] = Field(default_factory=dict)
    forecast_domain_scores: dict[DomainName, float] | None = None
    forecast_horizon_h: int | None = Field(default=None, gt=0)
    forecast_confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @field_validator("incident_id", "correlation_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        return _validate_uuid4(value)

    @field_validator("observed_at")
    @classmethod
    def validate_observed_at(cls, value: str) -> str:
        if _UTC_TIMESTAMP.fullmatch(value) is None:
            raise ValueError("timestamp must be ISO-8601 UTC ending in Z")
        datetime.fromisoformat(f"{value[:-1]}+00:00")
        return value

    @model_validator(mode="after")
    def validate_domain_references(self) -> Self:
        if len(self.active_domains) != len(set(self.active_domains)):
            raise ValueError("active domains must be unique")
        if any(domain not in self.domain_scores for domain in self.active_domains):
            raise ValueError("every active domain must have a domain score")
        if any(not 0.0 <= ratio <= 1.0 for ratio in self.domain_persistence_ratio.values()):
            raise ValueError("domain persistence ratios must be between zero and one")
        if self.mode in (AnalysisMode.FORWARD, AnalysisMode.HYBRID):
            if self.forecast_domain_scores is None or self.forecast_horizon_h is None or self.forecast_confidence is None:
                raise ValueError("forward and hybrid analysis require forecast evidence")
        return self


def _validate_uuid4(value: str) -> str:
    parsed = UUID(value)
    if parsed.version != 4:
        raise ValueError("identifier must be a UUIDv4")
    return value


__all__ = ["AnalysisMode", "AnalyticsIncident", "DomainName", "LineageReference"]
