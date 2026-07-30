"""Strict Pydantic mirror of the canonical event-envelope JSON Schema.

The plan labels redfish.server-health and snmpv3.network-utilization describe
flows, not event types. Typed payload rules therefore bind only to the actual
fixture event types ``server.health.degraded`` and
``network.interface.utilization``.
"""

from __future__ import annotations

from datetime import datetime
import re
from typing import Annotated, Final, Literal, Self, assert_never
from uuid import UUID

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_serializer,
    model_validator,
)
from pydantic_core import PydanticCustomError
from typing_extensions import TypeAliasType

_UTC_TIMESTAMP: Final = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)
JsonValue = TypeAliasType(
    "JsonValue",
    str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"],
)
JsonObject = TypeAliasType("JsonObject", dict[str, JsonValue])


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
        allow_inf_nan=False,
    )


class LineageEntry(_StrictModel):
    step: str = Field(min_length=1)
    at: str
    result: str | None = None

    @field_validator("at")
    @classmethod
    def validate_at(cls, value: str) -> str:
        return _validate_utc_timestamp(value)

    @field_validator("result")
    @classmethod
    def reject_null_result(cls, value: str | None) -> str:
        if value is None:
            raise PydanticCustomError("string_type", "Input should be a valid string")
        return value

    @model_serializer
    def serialize_model(self) -> JsonObject:
        value: JsonObject = {"step": self.step, "at": self.at}
        if "result" in self.model_fields_set:
            value["result"] = self.result
        return value


class Source(_StrictModel):
    system: str = Field(min_length=1)
    instance: str = Field(min_length=1)
    connector: str = Field(min_length=1)
    transport: Literal["fixture", "redfish", "snmpv3", "syslog", "rest", "stream"]
    native_event_id: str | None = None

    @model_serializer
    def serialize_model(self) -> JsonObject:
        value: JsonObject = {
            "system": self.system,
            "instance": self.instance,
            "connector": self.connector,
            "transport": self.transport,
        }
        if "native_event_id" in self.model_fields_set:
            value["native_event_id"] = self.native_event_id
        return value


class Enrichment(_StrictModel):
    validation_status: Literal["accepted", "quarantined", "duplicate"]
    lineage: list[LineageEntry] = Field(min_length=1)
    asset_identity: str | None = None
    ci_identity: str | None = None
    quality_flags: list[str] | None = None

    @field_validator("quality_flags")
    @classmethod
    def reject_null_quality_flags(cls, value: list[str] | None) -> list[str]:
        if value is None:
            raise PydanticCustomError("list_type", "Input should be a valid list")
        return value

    @model_serializer
    def serialize_model(self) -> JsonObject:
        value: JsonObject = {
            "validation_status": self.validation_status,
            "lineage": [
                item.model_dump(mode="json", round_trip=True) for item in self.lineage
            ],
        }
        if "asset_identity" in self.model_fields_set:
            value["asset_identity"] = self.asset_identity
        if "ci_identity" in self.model_fields_set:
            value["ci_identity"] = self.ci_identity
        if "quality_flags" in self.model_fields_set:
            flags: list[JsonValue] = []
            if self.quality_flags is not None:
                flags.extend(self.quality_flags)
            value["quality_flags"] = flags
        return value


class _ServerHealthPayload(_StrictModel):
    health: str
    component: str
    message: str


def _require_exact_float(value: JsonValue) -> float:
    match value:
        case float() as number:
            return number
        case str() | int() | bool() | list() | dict() | None:
            raise PydanticCustomError("float_type", "Input should be a valid float")
        case unreachable:
            assert_never(unreachable)


class _NetworkUtilizationPayload(_StrictModel):
    interface_alias: str
    utilization_percent: Annotated[float, BeforeValidator(_require_exact_float)]
    sample_window_seconds: int


class Envelope(_StrictModel):
    schema_version: Literal["0.1.0"]
    event_id: str
    occurred_at: str
    observed_at: str
    source: Source
    event_type: str = Field(pattern=r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
    priority: Literal["P1", "P2", "P3"]
    correlation_id: str
    payload: JsonObject
    enrichment: Enrichment

    @field_validator("event_id", "correlation_id")
    @classmethod
    def validate_uuid(cls, value: str) -> str:
        try:
            UUID(value)
        except ValueError as error:
            raise PydanticCustomError("uuid_parsing", "Input should be a valid UUID") from error
        return value

    @field_validator("occurred_at", "observed_at")
    @classmethod
    def validate_timestamp(cls, value: str) -> str:
        return _validate_utc_timestamp(value)

    @model_validator(mode="after")
    def validate_typed_payload(self) -> Self:
        try:
            if self.event_type == "server.health.degraded":
                _ServerHealthPayload.model_validate(self.payload, strict=True)
            if self.event_type == "network.interface.utilization":
                _NetworkUtilizationPayload.model_validate(self.payload, strict=True)
        except ValidationError as error:
            raise PydanticCustomError(
                "payload_invalid", "Payload does not match its event type"
            ) from error
        return self


def _validate_utc_timestamp(value: str) -> str:
    if _UTC_TIMESTAMP.fullmatch(value) is None:
        raise PydanticCustomError(
            "datetime_parsing", "Input should be an ISO-8601 UTC timestamp ending in Z"
        )
    try:
        datetime.fromisoformat(f"{value[:-1]}+00:00")
    except ValueError as error:
        raise PydanticCustomError(
            "datetime_parsing", "Input should be a semantically valid timestamp"
        ) from error
    return value
