"""Deterministic topology-aware root cause analysis."""

from __future__ import annotations

from math import exp

from pydantic import BaseModel, ConfigDict, Field

from .contracts import AnalysisMode, AnalyticsIncident, LineageReference

TOPOLOGY = {
    "power": {"cooling": 0.9, "compute": 0.8},
    "cooling": {"compute": 0.8, "memory": 0.6, "storage": 0.6},
    "hardware": {"storage": 0.8, "compute": 0.7},
    "storage": {"compute": 0.5},
    "compute": {"memory": 0.4},
    "network": {"compute": 0.7},
}


class RCAResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)
    incident_id: str
    correlation_id: str
    observed_at: str
    mode: AnalysisMode
    domain_probabilities: dict[str, float]
    root_domain: str
    ranked_domains: list[str]
    causal_chain: list[str]
    impact_domains: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str
    assumptions: list[str]
    lineage: list[LineageReference]
    forecast_horizon_h: int | None = None
    forecast_confidence: float | None = None


def analyze_root_cause(incident: AnalyticsIncident) -> RCAResult:

    if not incident.active_domains:
        return RCAResult(
            incident_id=incident.incident_id,
            correlation_id=incident.correlation_id,
            observed_at=incident.observed_at,
            mode=incident.mode,
            domain_probabilities={"unknown": 1.0},
            root_domain="unknown",
            ranked_domains=["unknown"],
            causal_chain=[],
            impact_domains=[],
            confidence=0.0,
            explanation="No active domains detected; no causal claim was produced.",
            assumptions=["Input contained no active domains."],
            lineage=incident.lineage,
            forecast_horizon_h=incident.forecast_horizon_h,
            forecast_confidence=incident.forecast_confidence,
        )

    raw_scores = {domain: _score_domain(domain, incident) for domain in incident.active_domains}
    probabilities = _softmax(raw_scores)
    ranked = sorted(probabilities, key=lambda domain: (-probabilities[domain], domain))
    root = ranked[0]
    chain = _causal_chain(root, set(incident.active_domains), probabilities)
    chain_text = " -> ".join(chain) if chain else root

    return RCAResult(
        incident_id=incident.incident_id,
        correlation_id=incident.correlation_id,
        observed_at=incident.observed_at,
        mode=incident.mode,
        domain_probabilities=probabilities,
        root_domain=root,
        ranked_domains=ranked,
        causal_chain=chain,
        impact_domains=sorted(incident.active_domains),
        confidence=probabilities[root],
        explanation=f"Root cause chain based on supplied domain evidence: {chain_text}.",
        assumptions=[
            "Topology is a deterministic Development prior.",
            "Only supplied domain scores, persistence, trend, anomaly ratio, and drift ratio were evaluated.",
        ],
        lineage=incident.lineage,
        forecast_horizon_h=incident.forecast_horizon_h,
        forecast_confidence=incident.forecast_confidence,
    )


def _score_domain(domain: str, incident: AnalyticsIncident) -> float:
    downstream = sum(TOPOLOGY.get(domain, {}).values())
    upstream = sum(targets.get(domain, 0.0) for targets in TOPOLOGY.values())
    topology_score = downstream * 0.6 + upstream * 0.4
    observed_score = incident.domain_scores[domain]
    if incident.mode is AnalysisMode.REACTIVE:
        evidence_score = observed_score
    elif incident.mode is AnalysisMode.FORWARD:
        evidence_score = (incident.forecast_domain_scores or {}).get(domain, 0.0)
    else:
        forecast = (incident.forecast_domain_scores or {}).get(domain, 0.0)
        confidence = incident.forecast_confidence or 0.0
        evidence_score = observed_score * (1.0 - confidence) + forecast * confidence
    persistence = incident.domain_persistence_ratio.get(domain, 0.0)
    trend = {"increasing": 1.0, "stable": 0.2, "decreasing": -0.5}.get(
        incident.domain_trend.get(domain, "stable"), 0.2
    )
    return (
        0.15 * topology_score
        + 0.50 * evidence_score
        + 0.15 * persistence
        + 0.10 * trend
        + 0.07 * incident.anomaly_ratio
        + 0.03 * incident.drift_ratio
    )


def _softmax(scores: dict[str, float]) -> dict[str, float]:
    maximum = max(scores.values())
    exponentials = {domain: exp(score - maximum) for domain, score in scores.items()}
    total = sum(exponentials.values())
    return {domain: exponentials[domain] / total for domain in sorted(exponentials)}


def _causal_chain(root: str, active: set[str], probabilities: dict[str, float]) -> list[str]:
    chain = [root]
    current = root
    for _depth in range(3):
        candidates = [
            domain
            for domain in TOPOLOGY.get(current, {})
            if domain in active and domain not in chain and probabilities.get(domain, 0.0) >= 0.15
        ]
        if not candidates:
            break
        current = max(candidates, key=lambda domain: (probabilities[domain], domain))
        chain.append(current)
    return chain


__all__ = ["RCAResult", "analyze_root_cause"]
