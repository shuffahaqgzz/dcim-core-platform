"""Deterministic Phase 2 identity resolution.

ADR-0020 fixes the rules implemented here: native UUID outranks
manufacturer+serial for Assets; source system+native device ID identifies a
CI; strong identifiers outrank hostname/FQDN/IP aliases; IP is never primary;
expired aliases cannot resolve; confidence then latest ``valid_from`` breaks
alias conflicts; unresolved and strong-identifier conflicts are quarantined;
merges require two matching strong identifiers and add lineage to both sides;
splits are operator-only.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Final, Literal, NotRequired, TypedDict
import unicodedata
import uuid


IDENTITY_NAMESPACE: Final = uuid.UUID("7d4e2c10-5f3a-4b8c-9d6e-1a2b3c4d5e6f")


class IdentityInputError(ValueError):
    pass


class OperatorOnlyError(PermissionError):
    pass


class AliasClaim(TypedDict):
    identity: dict[str, str]
    type: Literal["hostname", "fqdn", "ip"]
    value: str
    valid_from: str
    valid_to: NotRequired[str | None]
    source_confidence: NotRequired[int]


class IdentityConflictDetail(TypedDict):
    reason: Literal["identity_conflict"]
    conflicting_identifiers: tuple[str, ...]


class Resolution(TypedDict, total=False):
    status: Literal["resolved", "not_found", "quarantined"]
    identity: dict[str, str]
    reason: IdentityConflictDetail


class LineageEntry(TypedDict):
    action: Literal["merge"]
    at: str
    peer_identity: str


class IdentityRecord(TypedDict):
    identity: dict[str, str]
    lineage: list[LineageEntry]


def _component(value: str | int | bool | None, field: str) -> str:
    if not isinstance(value, str):
        raise IdentityInputError(f"{field} must be a string")
    normalized = unicodedata.normalize("NFC", value).strip()
    if not normalized:
        raise IdentityInputError(f"{field} must not be empty")
    return normalized


def _asset_name(identity: Mapping[str, str]) -> str:
    if "native_uuid" in identity:
        raw_uuid = _component(identity["native_uuid"], "native_uuid")
        try:
            canonical_uuid = str(uuid.UUID(raw_uuid))
        except ValueError as error:
            raise IdentityInputError("native_uuid must be a UUID") from error
        return f"asset|native_uuid|{canonical_uuid.lower()}"
    if "manufacturer" in identity or "serial_number" in identity:
        if "manufacturer" not in identity or "serial_number" not in identity:
            raise IdentityInputError(
                "manufacturer and serial_number must be supplied together"
            )
        manufacturer = _component(identity["manufacturer"], "manufacturer").casefold()
        serial = _component(identity["serial_number"], "serial_number").casefold().upper()
        return f"asset|mfr_serial|{manufacturer}|{serial}"
    if "ip" in identity:
        raise IdentityInputError("IP is never a primary identity")
    raise IdentityInputError("asset requires native_uuid or manufacturer and serial_number")


def derive_asset_id(identity: Mapping[str, str]) -> uuid.UUID:
    """Derive the ADR-0028 UUIDv5 for an Asset strong identity."""
    return uuid.uuid5(IDENTITY_NAMESPACE, _asset_name(identity))


def derive_ci_id(source_system: str, native_device_id: str) -> uuid.UUID:
    """Derive the ADR-0028 UUIDv5 for a CI strong identity."""
    return uuid.uuid5(IDENTITY_NAMESPACE, _ci_name(source_system, native_device_id))


def _ci_name(source_system: str, native_device_id: str) -> str:
    source = _component(source_system, "source_system").casefold()
    device = _component(native_device_id, "native_device_id")
    return f"ci|{source}|{device}"


def _strong_names(identity: Mapping[str, str]) -> tuple[str, ...]:
    ci_fields = "source_system" in identity or "native_device_id" in identity
    asset_fields = any(
        field in identity for field in ("native_uuid", "manufacturer", "serial_number")
    )
    if ci_fields and asset_fields:
        raise IdentityInputError("identity cannot mix Asset and CI strong identifiers")
    if ci_fields:
        if "source_system" not in identity or "native_device_id" not in identity:
            raise IdentityInputError(
                "source_system and native_device_id must be supplied together"
            )
        return (_ci_name(identity["source_system"], identity["native_device_id"]),)

    names: list[str] = []
    if "native_uuid" in identity:
        names.append(_asset_name({"native_uuid": identity["native_uuid"]}))
    if "manufacturer" in identity or "serial_number" in identity:
        names.append(
            _asset_name(
                {
                    field: identity[field]
                    for field in ("manufacturer", "serial_number")
                    if field in identity
                }
            )
        )
    if not names:
        _ = _asset_name(identity)
    return tuple(names)


def _instant(value: str, field: str) -> datetime:
    raw = _component(value, field)
    try:
        instant = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise IdentityInputError(f"{field} must be an ISO-8601 timestamp") from error
    if instant.tzinfo is None:
        raise IdentityInputError(f"{field} must include a UTC offset")
    return instant.astimezone(timezone.utc)


def alias_is_eligible(claim: AliasClaim, fixed_clock: str) -> bool:
    """Return whether an alias validity window contains the fixed clock."""
    clock = _instant(fixed_clock, "fixed_clock")
    valid_from = _instant(claim["valid_from"], "valid_from")
    valid_to_raw = claim.get("valid_to")
    valid_to = None if valid_to_raw is None else _instant(valid_to_raw, "valid_to")
    if valid_to is not None and valid_to < valid_from:
        raise IdentityInputError("valid_to must not precede valid_from")
    return valid_from <= clock and (valid_to is None or clock <= valid_to)


def _confidence(claim: AliasClaim) -> int:
    value: int | str | None = claim.get("source_confidence", 50)
    if type(value) is not int or not 0 <= value <= 100:
        raise IdentityInputError("source_confidence must be an integer from 0 to 100")
    return value


def resolve_alias(claims: Sequence[AliasClaim], fixed_clock: str) -> Resolution:
    """Resolve live claims by confidence and latest validity, or quarantine."""
    alias_groups = {(claim["type"], claim["value"]) for claim in claims}
    if len(alias_groups) > 1:
        raise IdentityInputError("alias claims must share the same type and value")
    eligible = tuple(claim for claim in claims if alias_is_eligible(claim, fixed_clock))
    if not eligible:
        return {"status": "not_found"}

    ranked = sorted(
        eligible,
        key=lambda claim: (_confidence(claim), _instant(claim["valid_from"], "valid_from")),
        reverse=True,
    )
    top_rank = (_confidence(ranked[0]), _instant(ranked[0]["valid_from"], "valid_from"))
    leaders = tuple(
        claim
        for claim in ranked
        if (_confidence(claim), _instant(claim["valid_from"], "valid_from")) == top_rank
    )
    return _resolve_strong(tuple(claim["identity"] for claim in leaders))


def _resolve_strong(strong_identities: Sequence[dict[str, str]]) -> Resolution:
    signatures = tuple(_strong_names(identity) for identity in strong_identities)
    identifiers = tuple(sorted({name for names in signatures for name in names}))
    shared = set(signatures[0]).intersection(*signatures[1:])
    native_count = sum(name.startswith("asset|native_uuid|") for name in identifiers)
    serial_count = sum(name.startswith("asset|mfr_serial|") for name in identifiers)
    ci_count = sum(name.startswith("ci|") for name in identifiers)
    class_count = int(native_count > 0 or serial_count > 0) + int(ci_count > 0)
    conflicts = (
        class_count > 1
        or native_count > 1
        or serial_count > 1
        or ci_count > 1
        or (len(signatures) > 1 and not shared)
    )
    if conflicts:
        return {
            "status": "quarantined",
            "reason": {
                "reason": "identity_conflict",
                "conflicting_identifiers": identifiers,
            },
        }
    selected = max(
        strong_identities,
        key=lambda identity: (len(_strong_names(identity)), tuple(sorted(identity.items()))),
    )
    return {"status": "resolved", "identity": selected}


def resolve_identity(
    strong_identities: Sequence[dict[str, str]],
    alias_claims: Sequence[AliasClaim],
    fixed_clock: str,
) -> Resolution:
    """Resolve strong evidence before aliases and quarantine strong conflicts."""
    _ = _instant(fixed_clock, "fixed_clock")
    if strong_identities:
        return _resolve_strong(strong_identities)
    return resolve_alias(alias_claims, fixed_clock)


def merge_identities(
    left: IdentityRecord, right: IdentityRecord, at: str
) -> tuple[IdentityRecord, IdentityRecord]:
    """Merge only records whose native UUID and manufacturer+serial both match."""
    _ = _instant(at, "at")
    left_identity = left["identity"]
    right_identity = right["identity"]
    required = ("native_uuid", "manufacturer", "serial_number")
    if not all(field in left_identity and field in right_identity for field in required):
        raise IdentityInputError("merge requires two matching strong identifiers")
    native_matches = _asset_name(
        {"native_uuid": left_identity["native_uuid"]}
    ) == _asset_name({"native_uuid": right_identity["native_uuid"]})
    serial_matches = _asset_name(
        {
            "manufacturer": left_identity["manufacturer"],
            "serial_number": left_identity["serial_number"],
        }
    ) == _asset_name(
        {
            "manufacturer": right_identity["manufacturer"],
            "serial_number": right_identity["serial_number"],
        }
    )
    if not native_matches or not serial_matches:
        raise IdentityInputError("conflicting strong identifiers require quarantine")
    left_name = _asset_name(left_identity)
    right_name = _asset_name(right_identity)
    return (
        {
            "identity": dict(left_identity),
            "lineage": [
                *left["lineage"],
                {"action": "merge", "at": at, "peer_identity": right_name},
            ],
        },
        {
            "identity": dict(right_identity),
            "lineage": [
                *right["lineage"],
                {"action": "merge", "at": at, "peer_identity": left_name},
            ],
        },
    )


def split_identity() -> None:
    """Reject automated splits; only the governed operator workflow may split."""
    raise OperatorOnlyError("identity splits are operator-only")
