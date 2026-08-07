"""Deterministic aggregation and correlation without runtime side effects."""

from __future__ import annotations

import math
from itertools import combinations
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .contracts import AnalyticsIncident, DomainName, LineageReference


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)


class AggregationSample(_StrictModel):
    anomalous: bool
    severe_drift: bool
    domain_scores: dict[DomainName, float]


class AggregationResult(_StrictModel):
    window_size: int = Field(gt=0)
    anomaly_ratio: float = Field(ge=0.0, le=1.0)
    drift_ratio: float = Field(ge=0.0, le=1.0)
    domain_persistence_ratio: dict[str, float]
    co_occurrence: dict[str, dict[str, int]]
    domain_trend: dict[str, str]


class CorrelationResult(_StrictModel):
    incident_id: str
    correlation_id: str
    active_domains: list[str]
    weighted_score: float
    lineage: list[LineageReference]


def aggregate_samples(samples: list[Any], activation_threshold: float = 3.0) -> AggregationResult:
    if not samples:
        raise ValueError("aggregation requires at least one sample")
    if any(not isinstance(sample, AggregationSample) for sample in samples):
        raise ValueError("samples must be strict AggregationSample instances")
    if type(activation_threshold) is not float or not math.isfinite(activation_threshold) or activation_threshold < 0.0:
        raise ValueError("activation threshold must be a finite nonnegative float")

    domains = sorted({domain for sample in samples for domain in sample.domain_scores})
    active_counts = {domain: 0 for domain in domains}
    series = {domain: [] for domain in domains}
    co_occurrence: dict[str, dict[str, int]] = {}

    for sample in samples:
        active: list[str] = []
        for domain in domains:
            score = sample.domain_scores.get(domain, 0.0)
            series[domain].append(score)
            if score >= activation_threshold:
                active_counts[domain] += 1
                active.append(domain)
        for left, right in combinations(active, 2):
            co_occurrence.setdefault(left, {})[right] = co_occurrence.get(left, {}).get(right, 0) + 1
            co_occurrence.setdefault(right, {})[left] = co_occurrence.get(right, {}).get(left, 0) + 1

    window = len(samples)
    trends = {domain: _trend(values) for domain, values in series.items()}
    return AggregationResult(
        window_size=window,
        anomaly_ratio=sum(sample.anomalous for sample in samples) / window,
        drift_ratio=sum(sample.severe_drift for sample in samples) / window,
        domain_persistence_ratio={domain: active_counts[domain] / window for domain in domains},
        co_occurrence=co_occurrence,
        domain_trend=trends,
    )


def correlate(incident: AnalyticsIncident) -> CorrelationResult:
    weights = {"power": 1.5, "cooling": 1.4, "storage": 1.2}
    weighted = sum(incident.domain_scores[domain] * weights.get(domain, 1.0) for domain in incident.active_domains)
    return CorrelationResult(
        incident_id=incident.incident_id,
        correlation_id=incident.correlation_id,
        active_domains=incident.active_domains,
        weighted_score=weighted,
        lineage=incident.lineage,
    )


def _trend(values: list[float]) -> str:
    if len(values) < 3:
        return "stable"
    change = (values[-1] - values[0]) / (len(values) - 1)
    if change > 0.5:
        return "increasing"
    if change < -0.5:
        return "decreasing"
    return "stable"


__all__ = ["AggregationResult", "AggregationSample", "CorrelationResult", "aggregate_samples", "correlate"]
