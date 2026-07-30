import unittest
from typing import Literal, cast

from scripts.phase2.identity import (
    AliasClaim,
    IdentityInputError,
    IdentityRecord,
    OperatorOnlyError,
    Resolution,
    alias_is_eligible,
    derive_asset_id,
    derive_ci_id,
    merge_identities,
    resolve_alias,
    resolve_identity,
    split_identity,
)


CLOCK = "2026-07-29T00:00:00Z"


def claim(
    identity: dict[str, str],
    *,
    alias_type: Literal["hostname", "fqdn", "ip"] = "hostname",
    value: str = "shared.example.invalid",
    valid_from: str = "2026-07-28T00:00:00Z",
    valid_to: str | None = None,
    confidence: int = 50,
) -> AliasClaim:
    return {
        "identity": identity, "type": alias_type, "value": value,
        "valid_from": valid_from, "valid_to": valid_to,
        "source_confidence": confidence,
    }


class IdentityResolverTests(unittest.TestCase):
    def assert_conflict(
        self, result: Resolution, identifiers: tuple[str, ...]
    ) -> None:
        expected: Resolution = {
            "status": "quarantined",
            "reason": {"reason": "identity_conflict", "conflicting_identifiers": identifiers},
        }
        self.assertEqual(expected, result)

    def test_derive_asset_id_golden_vectors(self) -> None:
        vectors = {
            "SYNTHETIC-0001": "031feaba-bb4a-5680-af12-05575569ab85",
            "SYNTHETIC-0002": "32819141-a82d-5335-8d35-6130ca35134b",
            "SYNTHETIC-SERVER-0001": "a08a836a-f6f6-58bd-8006-08dbfe5c982f",
            "SYNTHETIC-NAS-0001": "1ce60326-2586-5675-b041-df48e89e9199",
            "SYNTHETIC-UPS-0001": "75364746-58c8-5c93-b64f-57a4220f56a7",
            "SYNTHETIC-NVR-0001": "73e8fb96-9956-5b1a-88a3-c467e6d266c5",
        }
        for serial, expected in vectors.items():
            with self.subTest(serial=serial):
                actual = derive_asset_id(
                    {"manufacturer": "ExampleVendor", "serial_number": serial}
                )
                self.assertEqual(expected, str(actual))
        native = {"native_uuid": "550E8400-E29B-41D4-A716-446655440000"}
        self.assertEqual("39542c91-ef59-53b8-a0c8-159b8c7eaa8a", str(derive_asset_id(native)))
        acme = {"manufacturer": "  Acme Systems  ", "serial_number": " sn-0042 "}
        self.assertEqual("9b998410-a0e4-5e66-857f-1bad8b4afaba", str(derive_asset_id(acme)))
        composed = {"manufacturer": " café ", "serial_number": " ab12 "}
        decomposed = {"manufacturer": "cafe\u0301", "serial_number": "AB12"}
        self.assertEqual(derive_asset_id(composed), derive_asset_id(decomposed))
        self.assertEqual(
            derive_asset_id({"manufacturer": "Acme", "serial_number": "ab12"}),
            derive_asset_id({"manufacturer": "Acme", "serial_number": "AB12"}),
        )
        with self.assertRaises(IdentityInputError):
            _ = derive_asset_id({"manufacturer": " \t ", "serial_number": "AB12"})

    def test_derive_ci_id_golden_vectors(self) -> None:
        vectors = {
            "device-001": "71a77244-4212-56a3-817e-fc03e71dc4b2",
            "device-002": "4c467397-f5ad-50be-8539-ddc2b7c58519",
            "server-001": "dc2d07b2-1405-5a56-965e-c1c2d3098e21",
            "nas-001": "f0648673-d058-5bbf-bce2-f54efac5cdab",
            "ups-001": "a5f95890-2bbc-5e7a-85ff-b395a1fb8d09",
            "nvr-001": "3ee841e9-333a-5567-9375-318d9e875ed0",
        }
        for device, expected in vectors.items():
            with self.subTest(device=device):
                self.assertEqual(expected, str(derive_ci_id("synthetic-lab", device)))
        self.assertEqual(
            "f3a481af-08df-5be0-bf4e-35d287d3256d",
            str(derive_ci_id("  Monitoring Core ", "Device-007")),
        )

    def test_duplicate_serial_across_sources(self) -> None:
        result = resolve_identity(
            (
                {"manufacturer": "Vendor A", "serial_number": "DUP-1"},
                {"manufacturer": "Vendor B", "serial_number": "DUP-1"},
            ),
            (),
            CLOCK,
        )
        self.assert_conflict(
            result,
            (
                "asset|mfr_serial|vendor a|DUP-1",
                "asset|mfr_serial|vendor b|DUP-1",
            ),
        )

    def test_hostname_reuse_after_validity_expiry(self) -> None:
        expired = claim(
            {"manufacturer": "Example", "serial_number": "OLD"},
            valid_to="2026-07-28T23:59:59Z",
            confidence=100,
        )
        current = claim(
            {"manufacturer": "Example", "serial_number": "CURRENT"},
            valid_from="2026-07-29T00:00:00Z",
            confidence=10,
        )
        self.assertEqual(
            {"status": "resolved", "identity": current["identity"]},
            resolve_alias((expired, current), CLOCK),
        )

    def test_ip_moves_between_devices(self) -> None:
        former = claim(
            {"manufacturer": "Example", "serial_number": "FIRST"},
            alias_type="ip",
            value="192.0.2.10",
            valid_to="2026-07-28T00:00:00Z",
            confidence=100,
        )
        present = claim(
            {"manufacturer": "Example", "serial_number": "SECOND"},
            alias_type="ip",
            value="192.0.2.10",
            valid_from="2026-07-28T00:00:01Z",
            confidence=1,
        )
        result = resolve_alias((former, present), CLOCK)
        self.assertEqual(
            {"status": "resolved", "identity": present["identity"]},
            result,
        )

    def test_confidence_tie_quarantines(self) -> None:
        claims = (
            claim({"manufacturer": "Example", "serial_number": "ONE"}, confidence=80),
            claim({"manufacturer": "Example", "serial_number": "TWO"}, confidence=80),
        )
        result = resolve_alias(claims, CLOCK)
        self.assert_conflict(
            result,
            (
                "asset|mfr_serial|example|ONE",
                "asset|mfr_serial|example|TWO",
            ),
        )

    def test_merge_appends_lineage_to_both(self) -> None:
        identity = {"native_uuid": "550e8400-e29b-41d4-a716-446655440000",
                    "manufacturer": "Example", "serial_number": "ONE"}
        left: IdentityRecord = {"identity": identity, "lineage": []}
        right: IdentityRecord = {"identity": dict(identity), "lineage": []}
        merged_left, merged_right = merge_identities(left, right, CLOCK)
        self.assertEqual("merge", merged_left["lineage"][-1]["action"])
        self.assertEqual("merge", merged_right["lineage"][-1]["action"])
        self.assertEqual([], left["lineage"])
        self.assertEqual([], right["lineage"])

    def test_latest_valid_from_breaks_confidence_tie(self) -> None:
        older = claim({"manufacturer": "Example", "serial_number": "OLD"},
                      valid_from="2026-07-27T00:00:00Z")
        newer = claim({"manufacturer": "Example", "serial_number": "NEW"},
                      valid_from="2026-07-28T00:00:00Z")
        self.assertEqual(
            {"status": "resolved", "identity": newer["identity"]},
            resolve_alias((older, newer), CLOCK),
        )

    def test_mixed_alias_groups_are_rejected(self) -> None:
        identity = {"manufacturer": "Example", "serial_number": "ONE"}
        baseline = claim(identity)
        for mixed in (
            claim(identity, value="other.example.invalid"),
            claim(identity, alias_type="fqdn"),
        ):
            with self.subTest(mixed=mixed):
                with self.assertRaises(IdentityInputError):
                    _ = resolve_alias((baseline, mixed), CLOCK)

    def test_same_native_uuid_with_conflicting_serial_quarantines_order_stably(
        self,
    ) -> None:
        native_uuid = "550e8400-e29b-41d4-a716-446655440000"
        left = {
            "native_uuid": native_uuid,
            "manufacturer": "Example",
            "serial_number": "LEFT",
        }
        right = {
            "native_uuid": native_uuid,
            "manufacturer": "Example",
            "serial_number": "RIGHT",
        }
        forward = resolve_identity((left, right), (), CLOCK)
        reverse = resolve_identity((right, left), (), CLOCK)
        self.assertEqual(forward, reverse)
        self.assert_conflict(
            forward,
            (
                "asset|mfr_serial|example|LEFT",
                "asset|mfr_serial|example|RIGHT",
                f"asset|native_uuid|{native_uuid}",
            ),
        )
        alias_forward = resolve_alias((claim(left), claim(right)), CLOCK)
        alias_reverse = resolve_alias((claim(right), claim(left)), CLOCK)
        self.assertEqual(forward, alias_forward)
        self.assertEqual(alias_forward, alias_reverse)

    def test_ci_strong_identity_resolves(self) -> None:
        identity = {"source_system": " Monitoring Core ",
                    "native_device_id": "Device-007"}
        result = resolve_identity((identity,), (), CLOCK)
        self.assertEqual({"status": "resolved", "identity": identity}, result)
        self.assertEqual(result, resolve_alias((claim(identity),), CLOCK))

    def test_ci_and_cross_class_conflicts_quarantine_deterministically(self) -> None:
        ci_one = {"source_system": "monitoring", "native_device_id": "one"}
        ci_two = {"source_system": "monitoring", "native_device_id": "two"}
        asset = {"manufacturer": "Example", "serial_number": "ONE"}
        ci_conflict = resolve_identity((ci_two, ci_one), (), CLOCK)
        cross_class = resolve_identity((ci_one, asset), (), CLOCK)
        self.assert_conflict(
            ci_conflict,
            ("ci|monitoring|one", "ci|monitoring|two"),
        )
        self.assert_conflict(
            cross_class,
            ("asset|mfr_serial|example|ONE", "ci|monitoring|one"),
        )

    def test_ip_cannot_be_primary(self) -> None:
        with self.assertRaises(IdentityInputError):
            _ = derive_asset_id({"ip": "192.0.2.10"})

    def test_malformed_clock_and_alias_are_rejected(self) -> None:
        live = claim({"manufacturer": "Example", "serial_number": "ONE"})
        self.assertRaises(IdentityInputError, alias_is_eligible, live, "not-a-clock")
        for confidence in (cast(int, True), cast(int, cast(object, "high")), 101):
            live["source_confidence"] = confidence
            self.assertRaises(IdentityInputError, resolve_alias, (live,), CLOCK)
        live = claim({"manufacturer": "Example", "serial_number": "ONE"})
        live["valid_from"] = cast(str, cast(object, 7))
        self.assertRaises(IdentityInputError, resolve_alias, (live,), CLOCK)
        bad_identity = {"manufacturer": cast(str, cast(object, 7)), "serial_number": "ONE"}
        self.assertRaises(IdentityInputError, derive_asset_id, bad_identity)

    def test_stale_replay_is_stable(self) -> None:
        stale = claim(
            {"manufacturer": "Example", "serial_number": "OLD"},
            valid_from="2025-01-01T00:00:00Z",
            valid_to="2026-01-01T00:00:00Z",
        )
        self.assertEqual(resolve_alias((stale,), CLOCK), resolve_alias((stale,), CLOCK))

    def test_split_is_operator_only(self) -> None:
        with self.assertRaises(OperatorOnlyError):
            split_identity()
