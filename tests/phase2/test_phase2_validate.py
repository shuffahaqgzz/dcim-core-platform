from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import threading
from typing import Literal
import unittest

from contracts.python.dcim_contracts.disposition import JsonObject
from scripts.phase2.errors import DispositionImbalanceError
from scripts.phase2.ledger import DispositionLedger
from scripts.phase2.validate import DispositionEngine


ROOT = Path(__file__).resolve().parents[2]
EVENTS = ROOT / "fixtures" / "synthetic" / "events"
INVALID = ROOT / "fixtures" / "synthetic" / "invalid" / "invalid-event.json"
FIXTURE_PATHS = (
    EVENTS / "p1-redfish-health.json",
    EVENTS / "p1-ups-alarm.json",
    EVENTS / "p2-network-utilization.json",
    EVENTS / "p2-nas-capacity.json",
    EVENTS / "p2-nvr-health.json",
    EVENTS / "p2-server-capacity.json",
)
GOLDEN_HASHES = {
    "p1-redfish-health.json": "895b179f222f8970dbf8894cb468153a3c9f6bb96bbe936727b036ed14f6602e",
    "p1-ups-alarm.json": "aa6004a965935c9a38a04e2af70fafe6903b4dca5424dfff84355cd4637e1eb8",
    "p2-network-utilization.json": "443b82d984f3660ea239213cd8482cc3260a1cff64a5d162aab837650d7b11a5",
    "p2-nas-capacity.json": "d42e30e6d67f395603f84b960eefa1642b92e50137362af972392c985cdc92f7",
    "p2-nvr-health.json": "b9b8371fbde33140d110e8e19f550af26b15857510b540da10a4d5cb51276112",
    "p2-server-capacity.json": "2569489163e3857b34b43292a8b37ad5ad86c391c9f37871ed076cdfe97e2bdd",
}


class AtomicClaimStore:
    """Thread-safe first-wins fake with one claim critical section."""

    def __init__(self) -> None:
        self.claims: dict[str, str] = {}
        self.calls = 0
        self._lock = threading.Lock()

    def try_claim(
        self, event_id: str, content_sha256: str
    ) -> Literal["new", "duplicate", "conflict"]:
        with self._lock:
            self.calls += 1
            stored = self.claims.get(event_id)
            if stored is None:
                self.claims[event_id] = content_sha256
                return "new"
            if stored == content_sha256:
                return "duplicate"
            return "conflict"


class SyntheticClaimError(Exception):
    pass


class FailingClaimStore:
    def try_claim(
        self, event_id: str, content_sha256: str
    ) -> Literal["new", "duplicate", "conflict"]:
        raise SyntheticClaimError("synthetic claim failure")


def load(path: Path) -> JsonObject:
    return json.loads(path.read_text(encoding="utf-8"))


class Phase2DispositionEngineTests(unittest.TestCase):
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self.store = AtomicClaimStore()
        self.ledger = DispositionLedger()
        self.engine = DispositionEngine(store=self.store, ledger=self.ledger)

    def assert_balanced(self, expected: dict[str, int]) -> None:
        self.ledger.assert_balanced()
        self.assertEqual(expected, self.ledger.to_json())

    def test_six_fixtures_then_replay_balances_ledger(self) -> None:
        # Given: all six approved synthetic envelopes and an empty atomic store.
        fixtures = [load(path) for path in FIXTURE_PATHS]
        original = deepcopy(fixtures[0])
        # When: each fixture and one replay are handled.
        results = [self.engine.handle(item) for item in fixtures]
        replay = self.engine.handle(fixtures[0])
        # Then: six are accepted, the replay is duplicate, and accounting balances.
        self.assertEqual(["accepted"] * 6, [result.status for result in results])
        self.assertEqual("duplicate", replay.status)
        self.assertEqual(original, fixtures[0])
        self.assert_balanced(
            {"received": 7, "accepted": 6, "quarantined": 0, "duplicate": 1}
        )

    def test_invalid_fixture_has_exact_schema_reason(self) -> None:
        # Given: the repository's intentionally incomplete synthetic event.
        candidate = load(INVALID)
        # When: the candidate crosses canonical validation.
        result = self.engine.handle(candidate)
        # Then: it is quarantined once with the stable schema reason before claim.
        self.assertEqual(("quarantined", "schema_invalid"), (result.status, result.reason))
        self.assertEqual(0, self.store.calls)
        self.assert_balanced(
            {"received": 1, "accepted": 0, "quarantined": 1, "duplicate": 0}
        )

    def test_conflicting_valid_content_preserves_first_hash(self) -> None:
        # Given: one accepted envelope and a valid same-ID envelope with changed content.
        original = load(FIXTURE_PATHS[0])
        accepted = self.engine.handle(original)
        changed = deepcopy(original)
        changed["priority"] = "P2"
        stored_hash = self.store.claims[original["event_id"]]
        # When: the changed envelope attempts the same atomic claim.
        conflict = self.engine.handle(changed)
        # Then: conflict quarantine is explicit and the first hash is unchanged.
        self.assertEqual("accepted", accepted.status)
        self.assertEqual(
            ("quarantined", "event_id_content_conflict"),
            (conflict.status, conflict.reason),
        )
        self.assertEqual(stored_hash, self.store.claims[original["event_id"]])

    def test_invalid_claimed_id_never_calls_store(self) -> None:
        # Given: an accepted ID and an invalid candidate reusing that ID.
        valid = load(FIXTURE_PATHS[0])
        self.engine.handle(valid)
        invalid = deepcopy(valid)
        invalid["occurred_at"] = "not-a-time"
        calls_before = self.store.calls
        # When: invalid input is handled.
        result = self.engine.handle(invalid)
        # Then: validation wins over dedupe and no claim is attempted.
        self.assertEqual(("quarantined", "schema_invalid"), (result.status, result.reason))
        self.assertEqual(calls_before, self.store.calls)

    def test_typed_payload_failures_map_to_payload_invalid(self) -> None:
        # Given: event-specific payloads with missing, wrong, or extra fields.
        health = load(FIXTURE_PATHS[0])
        network = load(FIXTURE_PATHS[2])
        cases = (
            (health, {"health": "Warning", "component": "SyntheticPowerSupply"}),
            (health, {**health["payload"], "health": 7}),
            (health, {**health["payload"], "extra": "forbidden"}),
            (network, {**network["payload"], "sample_window_seconds": "60"}),
            (network, {**network["payload"], "utilization_percent": 73}),
            (network, {**network["payload"], "extra": "forbidden"}),
        )
        # When: each malformed typed payload is handled.
        results = []
        for envelope, payload in cases:
            candidate = deepcopy(envelope)
            candidate["event_id"] = f"00000000-0000-4000-8000-0000000000{len(results):02d}"
            candidate["payload"] = payload
            results.append(self.engine.handle(candidate))
        # Then: every case uses payload_invalid and none reaches atomic claim.
        self.assertEqual(
            [("quarantined", "payload_invalid")] * len(cases),
            [(result.status, result.reason) for result in results],
        )
        self.assertEqual(0, self.store.calls)

    def test_unknown_fields_reject_at_every_nested_model(self) -> None:
        # Given: one valid envelope with extras at four contract levels.
        base = load(FIXTURE_PATHS[0])
        cases = (
            ((), "extra"),
            (("source",), "extra"),
            (("enrichment",), "extra"),
            (("enrichment", "lineage", 0), "extra"),
        )
        # When: each unknown field crosses validation.
        results = []
        for index, (path, key) in enumerate(cases):
            candidate = deepcopy(base)
            target = candidate
            for part in path:
                target = target[part]
            target[key] = index
            results.append(self.engine.handle(candidate))
        # Then: every unknown field is schema-invalid before claim.
        self.assertEqual(["schema_invalid"] * 4, [result.reason for result in results])
        self.assertEqual(0, self.store.calls)

    def test_uuid_and_timestamp_validation_is_strict(self) -> None:
        # Given: malformed UUID and UTC timestamp variants, including non-strings.
        base = load(FIXTURE_PATHS[0])
        cases = (
            ("event_id", "not-a-uuid"),
            ("correlation_id", 7),
            ("occurred_at", "2026-07-16T00:00:00+00:00"),
            ("occurred_at", "2026-07-16T00:00:00z"),
            ("occurred_at", "2026-02-30T00:00:00Z"),
            ("observed_at", 7),
        )
        # When: each malformed scalar is handled independently.
        results = []
        for field, value in cases:
            candidate = deepcopy(base)
            candidate[field] = value
            results.append(self.engine.handle(candidate))
        # Then: strict semantic validation rejects all before claim.
        self.assertEqual(["schema_invalid"] * len(cases), [r.reason for r in results])
        self.assertEqual(0, self.store.calls)

    def test_lineage_timestamp_requires_utc_z(self) -> None:
        # Given: a lineage timestamp expressed with a UTC offset.
        candidate = load(FIXTURE_PATHS[0])
        candidate["enrichment"]["lineage"][0]["at"] = "2026-07-16T00:00:00+00:00"
        # When: the envelope is handled.
        result = self.engine.handle(candidate)
        # Then: nested timestamp validation rejects it before claim.
        self.assertEqual("schema_invalid", result.reason)
        self.assertEqual(0, self.store.calls)

    def test_scalar_mismatch_and_non_finite_numbers_reject(self) -> None:
        # Given: schema scalar mismatches and non-finite generic payload numbers.
        base = load(FIXTURE_PATHS[1])
        cases = (
            ("schema_version", 1),
            ("event_type", 4),
            ("priority", 2),
            ("payload", {"metric": "x", "value": float("nan")}),
            ("payload", {"metric": "x", "value": float("inf")}),
        )
        # When: each candidate is handled.
        results = []
        for field, value in cases:
            candidate = deepcopy(base)
            candidate[field] = value
            results.append(self.engine.handle(candidate))
        # Then: none is coerced or claimed.
        self.assertEqual(["schema_invalid"] * len(cases), [r.reason for r in results])
        self.assertEqual(0, self.store.calls)

    def test_absent_optional_fields_are_not_invented_in_canonical_dump(self) -> None:
        # Given: a valid envelope with every optional schema field absent.
        candidate = load(FIXTURE_PATHS[0])
        candidate["source"].pop("native_event_id")
        candidate["enrichment"].pop("asset_identity")
        candidate["enrichment"].pop("ci_identity")
        candidate["enrichment"].pop("quality_flags")
        candidate["enrichment"]["lineage"][0].pop("result")
        # When: it is accepted and canonically serialized.
        result = self.engine.handle(candidate)
        # Then: absent optional keys remain absent in the mandated dump.
        self.assertEqual("accepted", result.status)
        self.assertEqual(candidate, result.canonical)

    def test_concurrent_same_id_is_one_accept_and_remaining_duplicates(self) -> None:
        # Given: 24 concurrent calls with the same valid envelope and atomic fake.
        candidate = load(FIXTURE_PATHS[2])
        # When: all workers race the one claim operation.
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(self.engine.handle, [candidate] * 24))
        # Then: exactly one wins and every loser is duplicate, never conflict.
        statuses = [result.status for result in results]
        self.assertEqual(1, statuses.count("accepted"))
        self.assertEqual(23, statuses.count("duplicate"))
        self.assertNotIn("quarantined", statuses)
        self.assert_balanced(
            {"received": 24, "accepted": 1, "quarantined": 0, "duplicate": 23}
        )

    def test_store_failure_propagates_and_leaves_unbalanced_ledger(self) -> None:
        # Given: a valid envelope and a store that fails during atomic claim.
        ledger = DispositionLedger()
        engine = DispositionEngine(store=FailingClaimStore(), ledger=ledger)
        # When: the claim operation raises.
        with self.assertRaisesRegex(SyntheticClaimError, "synthetic claim failure"):
            engine.handle(load(FIXTURE_PATHS[0]))
        # Then: no terminal success is recorded and zero-loss accounting fails.
        self.assertEqual(
            {"received": 1, "accepted": 0, "quarantined": 0, "duplicate": 0},
            ledger.to_json(),
        )
        with self.assertRaises(DispositionImbalanceError):
            ledger.assert_balanced()

    def test_golden_hashes_in_fresh_python_process(self) -> None:
        # Given: six pinned vectors and a fresh interpreter command.
        program = """
import hashlib,json,sys
from pathlib import Path
from contracts.python.dcim_contracts.envelope import Envelope
for raw in sys.argv[1:]:
 p=Path(raw); value=json.loads(p.read_text())
 model=Envelope.model_validate(value,strict=True)
 canonical=model.model_dump(mode='json',round_trip=True)
 wire=json.dumps(canonical,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
 print(p.name,hashlib.sha256(wire.encode('utf-8')).hexdigest())
"""
        # When: that fresh process recomputes canonical fixture hashes.
        result = subprocess.run(
            [str(Path(sys.executable)), "-c", program, *map(str, FIXTURE_PATHS)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        actual = dict(line.split() for line in result.stdout.splitlines())
        # Then: it exits cleanly and exactly matches all independent literals.
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(GOLDEN_HASHES, actual)


if __name__ == "__main__":
    unittest.main()
