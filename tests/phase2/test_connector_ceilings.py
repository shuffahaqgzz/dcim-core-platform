from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from connectors.redfish import RedfishFixtureAdapter
from connectors.snmp import SNMPv3FixtureAdapter
from scripts.phase2.errors import KillSwitchEngaged, Phase2Error


ROOT = Path(__file__).resolve().parents[2]
REDFISH_FIXTURE = ROOT / "fixtures" / "synthetic" / "events" / "p1-redfish-health.json"
SNMP_FIXTURE = ROOT / "fixtures" / "synthetic" / "events" / "p2-network-utilization.json"


class ConnectorCeilingTests(unittest.TestCase):
    def redfish(
        self,
        *,
        poll_interval_seconds: int = 30,
        read_timeout_seconds: int = 10,
        enabled: bool = True,
    ) -> RedfishFixtureAdapter:
        return RedfishFixtureAdapter(
            fixture_paths=[REDFISH_FIXTURE],
            clock="2026-08-04T00:00:00Z",
            kill_flag=lambda: False,
            stop_file=None,
            poll_interval_seconds=poll_interval_seconds,
            read_timeout_seconds=read_timeout_seconds,
            enabled=enabled,
        )

    def snmp(
        self,
        *,
        poll_interval_seconds: int = 60,
        read_timeout_seconds: int = 5,
        enabled: bool = True,
    ) -> SNMPv3FixtureAdapter:
        return SNMPv3FixtureAdapter(
            fixture_paths=[SNMP_FIXTURE],
            clock="2026-08-04T00:00:00Z",
            kill_flag=lambda: False,
            stop_file=None,
            poll_interval_seconds=poll_interval_seconds,
            read_timeout_seconds=read_timeout_seconds,
            enabled=enabled,
        )

    def test_redfish_poll_floor_rejects_health_interval_below_adr_floor(self) -> None:
        # Given: ADR-0023 sets the Redfish health floor at 30 seconds.
        # When: a replay adapter is configured below that floor.
        # Then: the adapter rejects the ceiling contract before iteration.
        with self.assertRaises(Phase2Error):
            _ = self.redfish(poll_interval_seconds=29)

    def test_redfish_read_cap_rejects_timeout_above_adr_cap(self) -> None:
        # Given: ADR-0023 caps Redfish health reads at 10 seconds.
        # When: a replay adapter is configured above that cap.
        # Then: construction fails closed.
        with self.assertRaises(Phase2Error):
            _ = self.redfish(read_timeout_seconds=11)

    def test_snmp_default_poll_floor_rejects_interval_below_adr_floor(self) -> None:
        # Given: ADR-0023 sets the SNMP default/environmental floor at 60 seconds.
        # When: a replay adapter is configured below that floor.
        # Then: the adapter rejects the ceiling contract before iteration.
        with self.assertRaises(Phase2Error):
            _ = self.snmp(poll_interval_seconds=59)

    def test_snmp_read_cap_rejects_timeout_above_adr_cap(self) -> None:
        # Given: ADR-0023 caps SNMP reads at 5 seconds.
        # When: a replay adapter is configured above that cap.
        # Then: construction fails closed.
        with self.assertRaises(Phase2Error):
            _ = self.snmp(read_timeout_seconds=6)

    def test_default_ceiling_values_match_adr_contract(self) -> None:
        # Given: the adapter defaults represent the selected ADR-0023 classes.
        redfish = self.redfish()
        snmp = self.snmp()

        # When: the read-only contract values are inspected.
        values = (
            redfish.poll_interval_seconds,
            redfish.read_timeout_seconds,
            snmp.poll_interval_seconds,
            snmp.read_timeout_seconds,
        )

        # Then: the defaults are Redfish 30/10 and SNMP 60/5 seconds.
        self.assertEqual((30, 10, 60, 5), values)

    def test_config_kill_switch_disabled_yields_zero_records(self) -> None:
        # Given: the tier-1 config kill switch is disabled.
        redfish = self.redfish(enabled=False)
        snmp = self.snmp(enabled=False)

        # When: both fixture iterators are consumed.
        redfish_events = list(redfish)
        snmp_events = list(snmp)

        # Then: no synthetic record is emitted by either adapter.
        self.assertEqual([], redfish_events)
        self.assertEqual([], snmp_events)

    def test_stop_file_mid_iteration_can_resume_without_burst(self) -> None:
        # Given: two synthetic Redfish fixtures and a tier-2 stop file.
        with tempfile.TemporaryDirectory() as directory:
            stop_file = Path(directory) / "redfish.stop"
            adapter = RedfishFixtureAdapter(
                fixture_paths=[REDFISH_FIXTURE, REDFISH_FIXTURE],
                clock="2026-08-04T00:00:00Z",
                kill_flag=lambda: False,
                stop_file=stop_file,
            )
            iterator = iter(adapter)

            # When: the stop file is engaged after the first fixture.
            first = next(iterator)
            stop_file.touch()
            with self.assertRaises(KillSwitchEngaged):
                _ = next(iterator)

            # Then: the stop is immediate and removal resumes the same iterator.
            stop_file.unlink()
            second = next(iterator)
            self.assertEqual(first["event_id"], second["event_id"])

    def test_public_adapter_surface_has_no_write_style_methods(self) -> None:
        # Given: both fixture adapter public surfaces.
        adapters = (self.redfish(), self.snmp())
        forbidden = {"set", "create", "delete", "update", "action"}

        # When: callable public attributes are inspected.
        findings = [
            name
            for adapter in adapters
            for name in dir(adapter)
            if not name.startswith("_")
            and callable(getattr(adapter, name, None))
            and name.lower() in forbidden
        ]

        # Then: no write-style method is exposed.
        self.assertEqual([], findings)


if __name__ == "__main__":
    _ = unittest.main()
