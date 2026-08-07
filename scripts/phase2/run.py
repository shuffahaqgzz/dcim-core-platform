#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic==2.9.2"]
# ///

# ─── How to run ───
# 1. Install uv (if not installed):
#      curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. Run directly:
#      uv run scripts/phase2/run.py --run-id ID --fixtures-dir DIR --fixed-clock UTC
# 3. Or make executable and run through the uv shebang:
#      chmod +x scripts/phase2/run.py && ./scripts/phase2/run.py --help
# ──────────────────
"""Run the synthetic Phase 2 fixture pipeline transactionally."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import json
from pathlib import Path
import sys
from typing import Final, Protocol

from pydantic import ValidationError


ROOT: Final = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contracts.python.dcim_contracts.disposition import JsonValue  # noqa: E402
from scripts.phase2.db import (  # noqa: E402
    DatabaseCommandError,
    JsonExtractionError,
)
from scripts.phase2.errors import (  # noqa: E402
    KillSwitchEngaged,
    Phase2Error,
)
from scripts.phase2.execution import (  # noqa: E402
    begin_execution,
    reconcile_execution,
    ReconciliationError,
)
from scripts.phase2.ledger import DispositionLedger  # noqa: E402
from scripts.phase2.persist import (  # noqa: E402
    IdentityQuarantined,
    PersistenceError,
    PostgresClaimStore,
    QuarantineInput,
    persist_quarantine,
)
from scripts.phase2.runner_input import (  # noqa: E402
    adapt_input,
    build_manifest,
    input_paths,
    RunnerInputError,
)
from scripts.phase2.validate import DispositionEngine  # noqa: E402


DURABILITY_GUARANTEE: Final = (
    "durable per input from the moment its disposition transaction is "
    "acknowledged; loss before that point is detectable by reconciling "
    "manifest source_count against persisted dispositions per execution "
    "(scripts/phase2/reconcile.py)"
)
NORMALIZED_TOPIC: Final = "dcim.normalized.events"
DLQ_TOPIC: Final = "dcim.dlq.synthetic"
STREAM_FLUSH_TIMEOUT_SECONDS: Final = 30.0


class StreamProducer(Protocol):
    """Producer surface the stream branch needs from its Kafka boundary."""

    def produce_envelope(
        self,
        topic: str,
        key: str | None,
        value: bytes,
        headers: Mapping[str, str],
    ) -> None: ...

    def flush(self, timeout: float) -> None: ...


def execute(run_id: str, fixtures_dir: Path, fixed_clock: str) -> dict[str, JsonValue]:
    """Execute one manifest-first batch and return its reconciled summary."""
    manifest = build_manifest(run_id, fixtures_dir, fixed_clock, ROOT)
    context = begin_execution(manifest)
    ledger = DispositionLedger()

    for input_ordinal, path in enumerate(input_paths(manifest, fixtures_dir)):
        ledger.record("received")
        candidate: dict[str, JsonValue] = {}
        try:
            candidate = dict(adapt_input(path, fixtures_dir, fixed_clock))
            engine_ledger = DispositionLedger()
            store = PostgresClaimStore(context, candidate, input_ordinal)
            disposition = DispositionEngine(store, engine_ledger).handle(candidate)
        except (DatabaseCommandError, JsonExtractionError, PersistenceError):
            raise
        except KillSwitchEngaged:
            persist_quarantine(
                context,
                QuarantineInput(
                    candidate=candidate,
                    reason="kill_switch_engaged",
                    detail="kill_switch_engaged before fixture processing",
                ),
                input_ordinal,
            )
            ledger.record("quarantined")
            raise
        except RunnerInputError as error:
            persist_quarantine(
                context,
                QuarantineInput(
                    candidate={},
                    reason="schema_invalid",
                    detail=f"{error.error_type}:{error.detail}",
                ),
                input_ordinal,
            )
            ledger.record("quarantined")
            continue
        except IdentityQuarantined:
            ledger.record("quarantined")
            continue
        except ValidationError as error:
            validation_types = sorted(
                {str(item["type"]) for item in error.errors(include_url=False)}
            )
            reason = (
                "payload_invalid"
                if "payload_invalid" in validation_types
                else "schema_invalid"
            )
            persist_quarantine(
                context,
                QuarantineInput(
                    candidate=candidate,
                    reason=reason,
                    detail=",".join(validation_types),
                ),
                input_ordinal,
            )
            ledger.record("quarantined")
            continue
        except Exception as error:  # noqa: BROAD_EXCEPT_OK
            persist_quarantine(
                context,
                QuarantineInput(
                    candidate=candidate,
                    reason="unexpected_input_error",
                    detail=type(error).__name__,
                ),
                input_ordinal,
            )
            ledger.record("quarantined")
            continue
        ledger.record(disposition.status)

    ledger.assert_balanced()
    counts = reconcile_execution(context)
    if counts != ledger.to_json():
        raise ReconciliationError(run_id, context.execution_sequence)
    return {
        "run_id": run_id,
        "counts": counts,
        "manifest_sha256": manifest.manifest_sha256,
        "execution_sequence": context.execution_sequence,
        "reconciled": True,
        "durability_guarantee": DURABILITY_GUARANTEE,
    }


def _publish_stream_dlq(
    producer: StreamProducer,
    path: Path,
    run_id: str,
    reason: str,
    detail: str,
) -> None:
    """Publish one rejected raw input to the synthetic DLQ with its reason."""
    producer.produce_envelope(
        topic=DLQ_TOPIC,
        key=None,
        value=path.read_bytes(),
        headers={
            "reason": reason,
            "detail": detail,
            "source_fixture": path.name,
            "source_run_id": run_id,
        },
    )


def execute_stream(
    run_id: str, fixtures_dir: Path, fixed_clock: str
) -> dict[str, int]:
    """Validate fixtures and publish them; the consumer owns persistence.

    The manifest is built in memory only: stream mode performs no
    ``begin_execution`` and no database writes at all. Valid envelopes go to
    ``dcim.normalized.events``; every adaptation or validation failure goes to
    ``dcim.dlq.synthetic`` with the batch quarantine reason vocabulary.
    ``confluent_kafka`` is imported lazily by this branch only.
    """
    from contracts.python.dcim_contracts.envelope import Envelope  # noqa: PLC0415
    from scripts.phase2.kafka_producer import (  # noqa: PLC0415
        KafkaEnvelopeProducer,
    )

    manifest = build_manifest(run_id, fixtures_dir, fixed_clock, ROOT)
    producer: StreamProducer = KafkaEnvelopeProducer()
    ledger = DispositionLedger()

    for input_ordinal, path in enumerate(input_paths(manifest, fixtures_dir)):
        ledger.record("received")
        candidate: dict[str, JsonValue] = {}
        try:
            candidate = dict(adapt_input(path, fixtures_dir, fixed_clock))
            envelope = Envelope.model_validate(candidate, strict=True)
        except KillSwitchEngaged:
            _publish_stream_dlq(
                producer,
                path,
                run_id,
                "kill_switch_engaged",
                "kill_switch_engaged before fixture processing",
            )
            ledger.record("quarantined")
            raise
        except RunnerInputError as error:
            _publish_stream_dlq(
                producer,
                path,
                run_id,
                "schema_invalid",
                f"{error.error_type}:{error.detail}",
            )
            ledger.record("quarantined")
            continue
        except ValidationError as error:
            validation_types = sorted(
                {str(item["type"]) for item in error.errors(include_url=False)}
            )
            reason = (
                "payload_invalid"
                if "payload_invalid" in validation_types
                else "schema_invalid"
            )
            _publish_stream_dlq(
                producer, path, run_id, reason, ",".join(validation_types)
            )
            ledger.record("quarantined")
            continue
        except Exception as error:  # noqa: BROAD_EXCEPT_OK
            _publish_stream_dlq(
                producer,
                path,
                run_id,
                "unexpected_input_error",
                type(error).__name__,
            )
            ledger.record("quarantined")
            continue
        canonical = envelope.model_dump(mode="json", round_trip=True)
        producer.produce_envelope(
            topic=NORMALIZED_TOPIC,
            key=envelope.event_id,
            value=json.dumps(
                canonical,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8"),
            headers={
                "schema_version": envelope.schema_version,
                "source_run_id": run_id,
                "input_ordinal": str(input_ordinal),
            },
        )
        ledger.record("accepted")

    producer.flush(STREAM_FLUSH_TIMEOUT_SECONDS)
    ledger.assert_balanced()
    return {
        "received": ledger.received,
        "published": ledger.accepted,
        "dlq": ledger.quarantined,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--fixtures-dir", required=True, type=Path)
    parser.add_argument("--fixed-clock", required=True)
    parser.add_argument(
        "--mode",
        choices=("batch", "stream"),
        default="batch",
        help="batch persists via the frozen claim path; stream only publishes",
    )
    return parser


def run(argv: list[str] | None = None) -> int:
    """Parse the exact CLI contract, execute, and print success JSON."""
    arguments = _parser().parse_args(argv)
    if arguments.mode == "stream":
        summary: dict[str, JsonValue] = execute_stream(
            arguments.run_id, arguments.fixtures_dir, arguments.fixed_clock
        )
    else:
        summary = execute(
            arguments.run_id, arguments.fixtures_dir, arguments.fixed_clock
        )
    print(
        json.dumps(
            summary,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    )
    return 0


def main() -> int:
    """Translate expected failures into nonzero output without a success summary."""
    try:
        return run()
    except (DatabaseCommandError, JsonExtractionError, Phase2Error) as error:
        print(
            f"phase2 batch failed: {type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return 1
    except Exception as error:  # noqa: BROAD_EXCEPT_OK
        print(f"phase2 batch failed: {type(error).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
