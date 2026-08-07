#!/usr/bin/env bash

set -u

fail() {
  local message=$1
  local status=${2:-1}
  printf '%s\n' "kafka-host: FAIL: ${message}" >&2
  exit "$status"
}

if [[ ${1:-} == "--" ]]; then
  shift
fi
if [[ $# -eq 0 ]]; then
  fail "gate command is required after --" 2
fi
if [[ $1 == */* ]]; then
  [[ -f $1 && -x $1 ]] || fail "gate command could not be launched"
else
  command -v -- "$1" >/dev/null 2>&1 || fail "gate command could not be launched"
fi

kafka_state=$(timeout 10 docker inspect --format '{{.State.Status}}' dcim-build-kafka-1 2>/dev/null) || fail "Kafka container state unavailable"
case "$kafka_state" in
  running|stopped|exited|created|dead)
    ;;
  *)
    fail "Kafka container state unavailable"
    ;;
esac

DCIM_KAFKA_BOOTSTRAP="192.0.2.2:9092" "$@"
exit $?
