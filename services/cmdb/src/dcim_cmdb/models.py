"""Typed request and response models for the canonical CI contract."""

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


class RelationshipType(StrEnum):
    DEPENDS_ON = "depends_on"
    RUNS_ON = "runs_on"
    CONNECTED_TO = "connected_to"
    CONTAINS = "contains"
    HOSTED_ON = "hosted_on"
    PART_OF = "part_of"
    MONITORS = "monitors"


class Alias(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    type: AliasType
    value: Annotated[str, Field(min_length=1)]
    valid_from: datetime
    valid_to: datetime | None = None
    source: Annotated[str, Field(min_length=1)]
    confidence: Annotated[float, Field(ge=0, le=1)]


class CI(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    ci_id: UUID
    source_system: Annotated[str, Field(min_length=1)]
    native_device_id: Annotated[str, Field(min_length=1)]
    ci_type: Annotated[str, Field(min_length=1)]
    aliases: tuple[Alias, ...]
    asset_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class CICreate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    ci_id: UUID | None = None
    source_system: Annotated[str, Field(min_length=1)]
    native_device_id: Annotated[str, Field(min_length=1)]
    ci_type: Annotated[str, Field(min_length=1)]
    aliases: tuple[Alias, ...]
    asset_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class Relationship(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    relationship_id: UUID
    from_ci: UUID
    to_ci: UUID
    relationship_type: RelationshipType
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    source: str | None = None
    created_at: datetime | None = None


class RelationshipCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    relationship_id: UUID
    from_ci: UUID
    to_ci: UUID
    relationship_type: RelationshipType
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    source: str | None = None
