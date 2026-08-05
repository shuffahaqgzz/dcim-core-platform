"""Thin Kafka producer boundary for the Phase 2 stream pipeline mode.

This module is imported lazily by the stream branch of
``scripts/phase2/run.py`` only; the frozen batch path never imports it, so
``confluent_kafka`` (an exact-pin Development dependency) is loaded solely
when stream mode runs. Delivery is fail-closed: every publish is flushed
synchronously and any broker-reported error raises ``KafkaPublishError``.
"""

from __future__ import annotations

from collections.abc import Mapping
import os
from typing import Any, Final, Protocol

from .errors import KafkaPublishError


DEFAULT_BOOTSTRAP_SERVERS: Final = "kafka:9092"
DELIVERY_TIMEOUT_SECONDS: Final = 30.0
PRODUCER_CONFIG: Final = {
    "acks": "all",
    "enable.idempotence": True,
    "retries": 3,
    "message.max.bytes": 1048576,
}


class ProducerDriver(Protocol):
    """Minimal confluent_kafka.Producer surface used by this boundary."""

    def produce(self, topic: str, **kwargs: Any) -> None: ...

    def flush(self, timeout: float) -> int: ...


def bootstrap_servers() -> str:
    """Return the configured Development broker, defaulting in Compose."""
    return os.environ.get("DCIM_KAFKA_BOOTSTRAP", DEFAULT_BOOTSTRAP_SERVERS)


class KafkaEnvelopeProducer:
    """Publish validated envelopes with synchronous fail-closed delivery."""

    def __init__(
        self,
        bootstrap: str | None = None,
        driver: ProducerDriver | None = None,
    ) -> None:
        if driver is None:
            from confluent_kafka import Producer

            driver = Producer(
                {
                    "bootstrap.servers": bootstrap or bootstrap_servers(),
                    **PRODUCER_CONFIG,
                }
            )
        self._driver = driver

    def produce_envelope(
        self,
        topic: str,
        key: str | None,
        value: bytes,
        headers: Mapping[str, str],
    ) -> None:
        """Publish one message and raise on any delivery failure."""
        failures: list[str] = []

        def _on_delivery(error: object, message: object) -> None:
            cause = error
            if cause is None and message is not None:
                cause = message.error()  # type: ignore[attr-defined]
            if cause is not None:
                failures.append(str(cause))

        try:
            self._driver.produce(
                topic=topic,
                key=key,
                value=value,
                headers=dict(headers),
                on_delivery=_on_delivery,
            )
        except BufferError as error:
            raise KafkaPublishError(
                f"local producer queue is full for topic {topic}"
            ) from error
        remaining = self._driver.flush(DELIVERY_TIMEOUT_SECONDS)
        if remaining:
            raise KafkaPublishError(
                f"delivery to topic {topic} timed out with "
                f"{remaining} message(s) pending"
            )
        if failures:
            raise KafkaPublishError(
                f"delivery to topic {topic} failed: {'; '.join(failures)}"
            )

    def flush(self, timeout: float) -> None:
        """Drain any outstanding messages, raising if any remain."""
        remaining = self._driver.flush(timeout)
        if remaining:
            raise KafkaPublishError(
                f"producer flush left {remaining} message(s) pending"
            )
