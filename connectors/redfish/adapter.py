"""Replay synthetic Redfish fixtures without network or write capabilities."""

from __future__ import annotations

from collections.abc import Callable, Iterator
import json
from pathlib import Path
from typing import ClassVar, Protocol, TypeAlias

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


class _JsonLoader(Protocol):
    def __call__(self, s: str) -> JsonValue: ...


_JSON_LOADS: _JsonLoader = json.loads


class _RedfishFixtureError(Phase2Error):
    pass


class RedfishFixtureAdapter:
    """Yield canonical envelopes from synthetic Redfish fixture files."""

    __slots__: ClassVar[tuple[str, ...]] = (
        "_clock",
        "_fixture_paths",
        "_kill_flag",
        "_stop_file",
    )
    _clock: str
    _fixture_paths: tuple[Path, ...]
    _kill_flag: Callable[[], bool]
    _stop_file: Path | None

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
            stop_file_exists = (
                self._stop_file is not None and self._stop_file.exists()
            )
            if self._kill_flag() or stop_file_exists:
                raise KillSwitchEngaged(
                    "Redfish fixture adapter kill switch is engaged"
                )
            envelope = _JSON_LOADS(fixture_path.read_text(encoding="utf-8"))
            if not isinstance(envelope, dict):
                raise _RedfishFixtureError(
                    f"{fixture_path}: fixture root must be a JSON object"
                )
            source = envelope.get("source")
            if not isinstance(source, dict):
                raise _RedfishFixtureError(
                    f"{fixture_path}: source must be a JSON object"
                )
            native_event_id = source.get("native_event_id")
            if not isinstance(native_event_id, str) or not native_event_id:
                raise _RedfishFixtureError(
                    f"{fixture_path}: source.native_event_id must be a non-empty string"
                )
            envelope["observed_at"] = self._clock
            envelope["source"] = {
                "system": "redfish-synthetic",
                "instance": source.get("instance"),
                "connector": "redfish-fixture-adapter",
                "transport": "redfish",
                "native_event_id": native_event_id,
            }
            yield envelope
