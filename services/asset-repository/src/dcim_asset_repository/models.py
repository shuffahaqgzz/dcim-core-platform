"""Pydantic representations of the canonical Asset schema."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AliasType(StrEnum):
    HOSTNAME = "hostname"
    FQDN = "fqdn"
    IP = "ip"
    SOURCE_NATIVE_ID = "source_native_id"
    ASSET_TAG = "asset_tag"
    OTHER = "other"


class NativeUuidIdentity(BaseModel):
    """Asset identity keyed by a source-native UUID."""

    model_config = ConfigDict(extra="forbid")
    native_uuid: UUID


class ManufacturerSerialIdentity(BaseModel):
    """Asset identity keyed by manufacturer and serial number."""

    model_config = ConfigDict(extra="forbid")
    manufacturer: Annotated[str, Field(min_length=1)]
    serial_number: Annotated[str, Field(min_length=1)]


Identity = NativeUuidIdentity | ManufacturerSerialIdentity


class Alias(BaseModel):
    """Time-bounded asset alias with source confidence."""

    model_config = ConfigDict(extra="forbid")
    type: AliasType
    value: Annotated[str, Field(min_length=1)]
    valid_from: datetime
    valid_to: datetime | None = None
    source: Annotated[str, Field(min_length=1)]
    confidence: Annotated[float, Field(ge=0, le=1)]


class Asset(BaseModel):
    """Canonical asset payload matching schemas/asset.schema.json."""

    model_config = ConfigDict(extra="forbid")
    asset_id: UUID
    identity: Identity
    asset_type: Annotated[str, Field(min_length=1)]
    aliases: list[Alias]
    created_at: datetime
    updated_at: datetime


class AssetCreate(BaseModel):
    """Asset creation input, whose client idempotency key is optional."""

    model_config = ConfigDict(extra="forbid")
    asset_id: UUID | None = None
    identity: Identity
    asset_type: Annotated[str, Field(min_length=1)]
    aliases: list[Alias]
    created_at: datetime
    updated_at: datetime
