"""Replay synthetic SNMPv3 fixtures without network or control capabilities."""

from __future__ import annotations

from collections.abc import Callable, Iterator
import json
from pathlib import Path
from typing import TypeAlias

from scripts.phase2.errors import KillSwitchEngaged, Phase2Error


JsonValue: TypeAlias = (
    None
    | bool
    | int
    | float
    | str
    | list["JsonValue"]
    | dict[str, "JsonValue"]
)
CanonicalEnvelope: TypeAlias = dict[str, JsonValue]


class _SNMPv3FixtureError(Phase2Error):
    pass


class SNMPv3FixtureAdapter:
    """Yield canonical envelopes from an allowlisted set of fixture paths."""

    __slots__ = ("_clock", "_fixture_paths", "_kill_flag", "_stop_file")

    def __init__(
        self,
        fixture_paths: list[Path],
        clock: str,
        kill_flag: Callable[[], bool],
        stop_file: Path | None,
    ) -> None:
        self._fixture_paths = tuple(fixture_paths)
        self._clock = clock
        self._kill_flag = kill_flag
        self._stop_file = stop_file

    def __iter__(self) -> Iterator[CanonicalEnvelope]:
        for fixture_path in self._fixture_paths:
            self._raise_if_stopped()
            envelope = json.loads(fixture_path.read_text(encoding="utf-8"))
            if not isinstance(envelope, dict):
                raise _SNMPv3FixtureError(
                    f"{fixture_path}: fixture root must be a JSON object"
                )
            fixture_source = envelope.get("source")
            if not isinstance(fixture_source, dict):
                raise _SNMPv3FixtureError(
                    f"{fixture_path}: source must be a JSON object"
                )
            native_event_id = fixture_source.get("native_event_id")
            if not isinstance(native_event_id, str) or not native_event_id:
                raise _SNMPv3FixtureError(
                    f"{fixture_path}: source.native_event_id must be a non-empty string"
                )
            envelope["observed_at"] = self._clock
            envelope["source"] = {
                "system": "snmpv3-synthetic",
                "instance": fixture_source.get("instance"),
                "connector": "snmpv3-fixture-adapter",
                "transport": "snmpv3",
                "native_event_id": native_event_id,
            }
            yield envelope

    def _raise_if_stopped(self) -> None:
        if self._kill_flag() or (
            self._stop_file is not None and self._stop_file.exists()
        ):
            raise KillSwitchEngaged("SNMPv3 fixture adapter kill switch engaged")
