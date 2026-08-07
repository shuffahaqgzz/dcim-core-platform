"""Pure domain scoring for public-safe analytics inputs."""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict

FEATURE_DOMAINS = {
    "cpu_utilization": "compute",
    "memory_utilization": "memory",
    "disk_temperature": "storage",
    "interface_status": "network",
    "total_facility_power": "power",
    "it_equipment_power": "power",
    "temperature_celsius": "cooling",
}
DOMAIN_WEIGHTS = {
    "compute": 1.0,
    "memory": 1.0,
    "storage": 1.2,
    "network": 1.0,
    "power": 1.5,
    "cooling": 1.4,
}


class DomainState(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)
    domain_scores: dict[str, float]
    active_domains: list[str]
    domain_strength_index: float


def score_domains(feature_scores: dict[str, float], activation_threshold: float = 3.0) -> DomainState:
    if type(activation_threshold) is not float or not math.isfinite(activation_threshold) or activation_threshold < 0.0:
        raise ValueError("activation threshold must be a finite nonnegative float")
    if any(type(score) is not float or not math.isfinite(score) for score in feature_scores.values()):
        raise ValueError("feature scores must be finite floats")
    unknown = sorted(set(feature_scores) - set(FEATURE_DOMAINS))
    if unknown:
        raise ValueError(f"unknown feature: {unknown[0]}")

    scores: dict[str, float] = {}
    for feature, score in feature_scores.items():
        domain = FEATURE_DOMAINS[feature]
        scores[domain] = max(scores.get(domain, 0.0), abs(score))

    scores = dict(sorted(scores.items()))
    active = [domain for domain, score in scores.items() if score >= activation_threshold]
    strength = (
        sum(score * DOMAIN_WEIGHTS[domain] for domain, score in scores.items()) / len(scores)
        if scores
        else 0.0
    )
    return DomainState(domain_scores=scores, active_domains=active, domain_strength_index=strength)


__all__ = ["DomainState", "score_domains"]
