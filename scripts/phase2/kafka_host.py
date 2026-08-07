from __future__ import annotations

import ipaddress
from typing import Final


KAFKA_STATIC_ADDRESS: Final = "192.0.2.2"
KAFKA_PORT: Final = 9092


class KafkaHostError(ValueError):
    def __str__(self) -> str:
        return "Kafka bootstrap address is outside the synthetic contract"


def bootstrap_servers(address: str = KAFKA_STATIC_ADDRESS) -> str:
    try:
        normalized = str(ipaddress.ip_address(address))
    except ValueError as error:
        raise KafkaHostError from error
    if normalized != KAFKA_STATIC_ADDRESS:
        raise KafkaHostError
    return f"{normalized}:{KAFKA_PORT}"
