"""Render validated Phase 2 identity data as PostgreSQL DML."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from typing import TypeAlias

from contracts.python.dcim_contracts.disposition import JsonValue

from .db import literal
from .errors import SqlRenderError
from .identity import (
    derive_asset_id,
    derive_ci_id,
    IdentityInputError,
    resolve_identity,
)


JsonObject: TypeAlias = dict[str, JsonValue]

__all__ = (
    "IdentityOmitted",
    "IdentityPreparation",
    "IdentityRejected",
    "JsonObject",
    "literal",
    "PreparedIdentity",
    "prepare_identity",
    "render_identity_dml",
    "SqlRenderError",
)


@dataclass(frozen=True, slots=True)
class PreparedIdentity:
    """Identity values proven safe for deterministic SQL rendering."""

    asset_id: str
    ci_id: str
    manufacturer: str
    serial_number: str
    source_system: str
    native_device_id: str
    instance: str
    fixed_clock: str


@dataclass(frozen=True, slots=True)
class IdentityOmitted:
    """A valid event carries no complete identity tuple."""


@dataclass(frozen=True, slots=True)
class IdentityRejected:
    """Identity input cannot be represented as authoritative rows."""


type IdentityPreparation = PreparedIdentity | IdentityOmitted | IdentityRejected


def json_literal(value: JsonObject) -> str:
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return f"{literal(canonical)}::jsonb"


def _prepared_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def prepare_identity(
    canonical: Mapping[str, JsonValue],
    fixed_clock: str,
) -> IdentityPreparation:
    """Parse identity input into a total, render-safe outcome."""
    enrichment = canonical["enrichment"]
    source = canonical["source"]
    if not isinstance(enrichment, dict) or not isinstance(source, dict):
        return IdentityRejected()
    asset_raw = enrichment.get("asset_identity")
    ci_raw = enrichment.get("ci_identity")
    instance = source.get("instance")
    present = tuple(
        value
        for value in (asset_raw, ci_raw, instance, fixed_clock)
        if isinstance(value, str)
    )
    if any("\x00" in value for value in present):
        return IdentityRejected()
    try:
        for value in present:
            _ = value.encode("utf-8")
    except UnicodeEncodeError:
        return IdentityRejected()
    if not all(isinstance(value, str) for value in (asset_raw, ci_raw, instance)):
        return IdentityOmitted()
    asset_text = str(asset_raw)
    ci_text = str(ci_raw)
    instance_text = str(instance)
    manufacturer, separator, serial = asset_text.partition(":")
    source_system, ci_separator, native_device_id = ci_text.partition(":")
    if not separator or not ci_separator:
        return IdentityRejected()
    asset_identity = {"manufacturer": manufacturer, "serial_number": serial}
    ci_identity = {"source_system": source_system, "native_device_id": native_device_id}
    try:
        asset_resolution = resolve_identity((asset_identity,), (), fixed_clock)
        ci_resolution = resolve_identity((ci_identity,), (), fixed_clock)
        asset_id = str(derive_asset_id(asset_identity))
        ci_id = str(derive_ci_id(source_system, native_device_id))
    except IdentityInputError:
        return IdentityRejected()
    if (
        asset_resolution.get("status") != "resolved"
        or ci_resolution.get("status") != "resolved"
    ):
        return IdentityRejected()
    return PreparedIdentity(
        asset_id=asset_id,
        ci_id=ci_id,
        manufacturer=manufacturer,
        serial_number=serial,
        source_system=source_system,
        native_device_id=native_device_id,
        instance=instance_text,
        fixed_clock=fixed_clock,
    )


def render_identity_dml(prepared: PreparedIdentity) -> str:
    """Render only a prepared identity into deterministic DML."""
    asset_identity = {
        "manufacturer": prepared.manufacturer,
        "serial_number": prepared.serial_number,
    }
    identity_json = json.dumps(
        asset_identity,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    clock = _prepared_literal(prepared.fixed_clock)
    return f"""
INSERT INTO phase2.assets
    (asset_id, identity, asset_type, created_at, updated_at)
SELECT {_prepared_literal(prepared.asset_id)}::uuid,
    {_prepared_literal(identity_json)}::jsonb,
    'synthetic-device', {clock}::timestamptz, {clock}::timestamptz
ON CONFLICT (asset_id) DO NOTHING;
INSERT INTO phase2.cis
    (ci_id, asset_id, source_system, native_device_id, ci_type, created_at, updated_at)
SELECT {_prepared_literal(prepared.ci_id)}::uuid,
    {_prepared_literal(prepared.asset_id)}::uuid,
    {_prepared_literal(prepared.source_system)},
    {_prepared_literal(prepared.native_device_id)},
    'synthetic-ci',
    {clock}::timestamptz, {clock}::timestamptz
ON CONFLICT (ci_id) DO NOTHING;
INSERT INTO phase2.aliases
    (owner_type, owner_id, type, value, valid_from, valid_to, source, confidence)
SELECT 'asset', {_prepared_literal(prepared.asset_id)}::uuid, 'hostname',
    {_prepared_literal(prepared.instance)}, {clock}::timestamptz,
    NULL, 'synthetic-fixture', 50
WHERE NOT EXISTS (
    SELECT 1 FROM phase2.aliases
    WHERE owner_type = 'asset'
      AND owner_id = {_prepared_literal(prepared.asset_id)}::uuid
      AND type = 'hostname' AND value = {_prepared_literal(prepared.instance)}
);
"""
