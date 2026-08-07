from __future__ import annotations

import unittest

from dcim_analytics.contracts import AnalysisMode, AnalyticsIncident, LineageReference
from dcim_analytics.correlation import AggregationSample, aggregate_samples, correlate
from dcim_analytics.domain import score_domains
from dcim_analytics.rca import analyze_root_cause


def incident(**overrides):
    values = {
        "incident_id": "11111111-1111-4111-8111-111111111111",
        "correlation_id": "22222222-2222-4222-8222-222222222222",
        "observed_at": "2026-08-07T00:00:00Z",
        "active_domains": ["power", "compute"],
        "domain_scores": {"power": 5.0, "compute": 3.5},
        "lineage": [LineageReference(event_id="33333333-3333-4333-8333-333333333333", step="synthetic")],
    }
    values.update(overrides)
    return AnalyticsIncident(**values)


class DomainTests(unittest.TestCase):
    def test_scores_only_domains_with_available_features(self) -> None:
        state = score_domains({"total_facility_power": 5.0, "cpu_utilization": 3.2})
        self.assertEqual(state.active_domains, ["compute", "power"])
        self.assertEqual(state.domain_scores, {"compute": 3.2, "power": 5.0})

    def test_rejects_unknown_feature(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown feature"):
            score_domains({"made_up_metric": 4.0})

    def test_scoring_rejects_coercion_and_invalid_threshold(self) -> None:
        for scores, threshold in (({"cpu_utilization": "4.0"}, 3.0), ({"cpu_utilization": 4.0}, -1.0)):
            with self.subTest(scores=scores, threshold=threshold), self.assertRaises(ValueError):
                score_domains(scores, activation_threshold=threshold)


class CorrelationTests(unittest.TestCase):
    def test_aggregation_is_deterministic(self) -> None:
        samples = [
            AggregationSample(anomalous=True, severe_drift=False, domain_scores={"power": 4.0, "compute": 3.0}),
            AggregationSample(anomalous=False, severe_drift=True, domain_scores={"power": 5.0, "compute": 4.0}),
            AggregationSample(anomalous=True, severe_drift=False, domain_scores={"power": 6.0, "compute": 5.0}),
        ]
        result = aggregate_samples(samples)
        self.assertEqual(result.window_size, 3)
        self.assertAlmostEqual(result.anomaly_ratio, 2 / 3)
        self.assertEqual(result.domain_trend["power"], "increasing")
        self.assertEqual(result.co_occurrence["power"]["compute"], 3)

    def test_aggregation_rejects_untyped_sample_and_invalid_threshold(self) -> None:
        with self.assertRaises(ValueError):
            aggregate_samples([{"anomalous": True}], activation_threshold=3.0)
        with self.assertRaises(ValueError):
            aggregate_samples([AggregationSample(anomalous=True, severe_drift=False, domain_scores={"power": 4.0})], -1.0)

    def test_correlation_preserves_lineage(self) -> None:
        result = correlate(incident())
        self.assertEqual(result.correlation_id, "22222222-2222-4222-8222-222222222222")
        self.assertEqual(result.lineage[0].step, "synthetic")


class RCATests(unittest.TestCase):
    def test_power_evidence_outranks_compute(self) -> None:
        result = analyze_root_cause(incident())
        self.assertEqual(result.root_domain, "power")
        self.assertEqual(result.causal_chain, ["power", "compute"])
        self.assertAlmostEqual(sum(result.domain_probabilities.values()), 1.0)
        self.assertEqual(result.lineage[0].step, "synthetic")

    def test_empty_domains_return_explicit_unknown(self) -> None:
        result = analyze_root_cause(incident(active_domains=[], domain_scores={}))
        self.assertEqual(result.root_domain, "unknown")
        self.assertEqual(result.confidence, 0.0)
        self.assertIn("No active domains", result.explanation)

    def test_forward_mode_requires_forecast_context(self) -> None:
        with self.assertRaisesRegex(ValueError, "forecast"):
            analyze_root_cause(incident(mode=AnalysisMode.FORWARD))

    def test_forward_mode_preserves_forecast_context(self) -> None:
        result = analyze_root_cause(
            incident(
                mode=AnalysisMode.FORWARD,
                active_domains=["power", "compute"],
                domain_scores={"power": 5.0, "compute": 3.5},
                forecast_domain_scores={"power": 2.0, "compute": 6.0},
                forecast_horizon_h=24,
                forecast_confidence=0.8,
            )
        )
        self.assertEqual(result.mode, AnalysisMode.FORWARD)
        self.assertEqual(result.forecast_horizon_h, 24)
        self.assertEqual(result.forecast_confidence, 0.8)
        self.assertEqual(result.root_domain, "compute")

    def test_causal_chain_contains_only_real_edges(self) -> None:
        result = analyze_root_cause(
            incident(
                active_domains=["cooling", "compute", "memory", "storage"],
                domain_scores={"cooling": 6.0, "compute": 4.0, "memory": 3.5, "storage": 3.2},
            )
        )
        topology = {"cooling": {"compute", "memory", "storage"}, "compute": {"memory"}}
        pairs = zip(result.causal_chain, result.causal_chain[1:], strict=False)
        self.assertTrue(all(right in topology.get(left, set()) for left, right in pairs))

    def test_same_input_returns_same_analysis(self) -> None:
        first = analyze_root_cause(incident()).model_dump()
        second = analyze_root_cause(incident()).model_dump()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
