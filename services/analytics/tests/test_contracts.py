from __future__ import annotations

import unittest
from uuid import UUID

from pydantic import ValidationError

from dcim_analytics.contracts import AnalysisMode, AnalyticsIncident, LineageReference


class AnalyticsContractTests(unittest.TestCase):
    def test_incident_accepts_strict_lineage_contract(self) -> None:
        incident = AnalyticsIncident(
            incident_id="11111111-1111-4111-8111-111111111111",
            correlation_id="22222222-2222-4222-8222-222222222222",
            observed_at="2026-08-07T00:00:00Z",
            active_domains=["power", "compute"],
            domain_scores={"power": 5.0, "compute": 3.5},
            lineage=[
                LineageReference(
                    event_id="33333333-3333-4333-8333-333333333333",
                    step="synthetic-anomaly",
                )
            ],
            mode=AnalysisMode.REACTIVE,
        )

        self.assertEqual(incident.mode, AnalysisMode.REACTIVE)
        self.assertEqual(UUID(incident.correlation_id).version, 4)
        self.assertEqual(incident.lineage[0].step, "synthetic-anomaly")

    def test_incident_rejects_unknown_fields(self) -> None:
        with self.assertRaises(ValidationError):
            AnalyticsIncident(
                incident_id="11111111-1111-4111-8111-111111111111",
                correlation_id="22222222-2222-4222-8222-222222222222",
                observed_at="2026-08-07T00:00:00Z",
                active_domains=[],
                domain_scores={},
                lineage=[],
                unexpected="rejected",
            )

    def test_incident_requires_utc_timestamp(self) -> None:
        with self.assertRaises(ValidationError):
            AnalyticsIncident(
                incident_id="11111111-1111-4111-8111-111111111111",
                correlation_id="22222222-2222-4222-8222-222222222222",
                observed_at="2026-08-07T07:00:00+07:00",
                active_domains=[],
                domain_scores={},
                lineage=[],
            )

    def test_incident_rejects_duplicate_or_unsupported_domains(self) -> None:
        for domains, scores in (
            (["power", "power"], {"power": 4.0}),
            (["unsupported"], {"unsupported": 4.0}),
        ):
            with self.subTest(domains=domains), self.assertRaises(ValidationError):
                AnalyticsIncident(
                    incident_id="11111111-1111-4111-8111-111111111111",
                    correlation_id="22222222-2222-4222-8222-222222222222",
                    observed_at="2026-08-07T00:00:00Z",
                    active_domains=domains,
                    domain_scores=scores,
                    lineage=[],
                )

    def test_incident_rejects_invalid_trend_and_persistence(self) -> None:
        with self.assertRaises(ValidationError):
            AnalyticsIncident(
                incident_id="11111111-1111-4111-8111-111111111111",
                correlation_id="22222222-2222-4222-8222-222222222222",
                observed_at="2026-08-07T00:00:00Z",
                active_domains=["power"],
                domain_scores={"power": 4.0},
                lineage=[],
                domain_trend={"power": "invented"},
                domain_persistence_ratio={"power": 1.1},
            )


if __name__ == "__main__":
    unittest.main()
