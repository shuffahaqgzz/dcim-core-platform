"""Replay synthetic Redfish fixtures without network or write capabilities."""

from __future__ import annotations

from collections.abc import Callable, Iterator
import json
from pathlib import Path
from typing import ClassVar, Final, Protocol, TypeAlias, final, override

from scripts.phase2.errors import (
    ConnectorCeilingError,
    KillSwitchEngaged,
    Phase2Error,
)


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
REDFISH_MIN_POLL_INTERVAL_SECONDS: Final = 30
REDFISH_MAX_READ_TIMEOUT_SECONDS: Final = 10


class _RedfishFixtureError(Phase2Error):
    pass


class RedfishFixtureAdapter:
    """Replay synthetic Redfish envelopes with ADR-0023 contract ceilings.

    Ceiling arguments are contract dummies for this replay adapter; no live
    Redfish poll or source request is performed.
    """

    __slots__: ClassVar[tuple[str, ...]] = (
        "_clock",
        "_enabled",
        "_fixture_paths",
        "_kill_flag",
        "_poll_interval_seconds",
        "_read_timeout_seconds",
        "_stop_file",
    )
    _clock: str
    _enabled: bool
    _fixture_paths: tuple[Path, ...]
    _kill_flag: Callable[[], bool]
    _poll_interval_seconds: int
    _read_timeout_seconds: int
    _stop_file: Path | None

    def __init__(
        self,
        fixture_paths: list[Path],
        clock: str,
        kill_flag: Callable[[], bool],
        stop_file: Path | None,
        poll_interval_seconds: int = 30,
        read_timeout_seconds: int = 10,
        enabled: bool = True,
    ) -> None:
        if poll_interval_seconds < REDFISH_MIN_POLL_INTERVAL_SECONDS:
            raise ConnectorCeilingError(
                connector="redfish",
                parameter="poll_interval_seconds",
                value=poll_interval_seconds,
                bound="at least",
                limit=REDFISH_MIN_POLL_INTERVAL_SECONDS,
            )
        if read_timeout_seconds > REDFISH_MAX_READ_TIMEOUT_SECONDS:
            raise ConnectorCeilingError(
                connector="redfish",
                parameter="read_timeout_seconds",
                value=read_timeout_seconds,
                bound="at most",
                limit=REDFISH_MAX_READ_TIMEOUT_SECONDS,
            )
        self._fixture_paths = tuple(fixture_paths)
        self._clock = clock
        self._kill_flag = kill_flag
        self._stop_file = stop_file
        self._poll_interval_seconds = poll_interval_seconds
        self._read_timeout_seconds = read_timeout_seconds
        self._enabled = enabled

    def __iter__(self) -> Iterator[CanonicalEnvelope]:
        return _RedfishFixtureIterator(
            fixture_paths=self._fixture_paths,
            enabled=self._enabled,
            raise_if_stopped=self._raise_if_stopped,
            load_fixture=self._load_fixture,
        )

    @property
    def poll_interval_seconds(self) -> int:
        return self._poll_interval_seconds

    @property
    def read_timeout_seconds(self) -> int:
        return self._read_timeout_seconds

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _raise_if_stopped(self) -> None:
        if self._kill_flag() or (
            self._stop_file is not None and self._stop_file.exists()
        ):
            raise KillSwitchEngaged(
                "Redfish fixture adapter kill switch is engaged"
            )

    def _load_fixture(self, fixture_path: Path) -> CanonicalEnvelope:
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
        return envelope


@final
class _RedfishFixtureIterator(Iterator[CanonicalEnvelope]):
    __slots__: ClassVar[tuple[str, ...]] = (
        "_enabled",
        "_fixture_paths",
        "_index",
        "_load_fixture",
        "_raise_if_stopped",
    )
    _enabled: bool
    _fixture_paths: tuple[Path, ...]
    _index: int
    _load_fixture: Callable[[Path], CanonicalEnvelope]
    _raise_if_stopped: Callable[[], None]

    def __init__(
        self,
        *,
        fixture_paths: tuple[Path, ...],
        enabled: bool,
        raise_if_stopped: Callable[[], None],
        load_fixture: Callable[[Path], CanonicalEnvelope],
    ) -> None:
        self._fixture_paths = fixture_paths
        self._enabled = enabled
        self._index = 0
        self._raise_if_stopped = raise_if_stopped
        self._load_fixture = load_fixture

    @override
    def __iter__(self) -> _RedfishFixtureIterator:
        return self

    @override
    def __next__(self) -> CanonicalEnvelope:
        if not self._enabled or self._index >= len(self._fixture_paths):
            raise StopIteration
        self._raise_if_stopped()
        fixture_path = self._fixture_paths[self._index]
        self._index += 1
        return self._load_fixture(fixture_path)
