#!/usr/bin/env bash

set -u

original_hosts=""
updated_hosts=""
restore_required=0

fail() {
  local message=$1
  local status=${2:-1}
  printf '%s\n' "kafka-host: FAIL: ${message}" >&2
  exit "$status"
}

cleanup() {
  local status=$?
  trap - EXIT HUP INT TERM
  if [[ $restore_required -eq 1 ]]; then
    if ! sudo -n tee -- /etc/hosts < "$original_hosts" >/dev/null 2>/dev/null; then
      status=1
    fi
  fi
  if [[ -n $original_hosts ]]; then
    rm -f -- "$original_hosts" >/dev/null 2>&1 || status=1
  fi
  if [[ -n $updated_hosts ]]; then
    rm -f -- "$updated_hosts" >/dev/null 2>&1 || status=1
  fi
  exit "$status"
}

trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

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

umask 077
original_hosts=$(mktemp "${TMPDIR:-/tmp}/dcim-kafka-host.original.XXXXXX") || fail "temporary hosts backup could not be created"
updated_hosts=$(mktemp "${TMPDIR:-/tmp}/dcim-kafka-host.updated.XXXXXX") || fail "temporary hosts output could not be created"

cp -- /etc/hosts "$original_hosts" 2>/dev/null || fail "hosts file could not be copied"

kafka_state=$(timeout 10 docker inspect --format '{{.State.Status}}' dcim-build-kafka-1 2>/dev/null) || fail "Kafka container state unavailable"
case "$kafka_state" in
  running)
    inspect_format='{{range .NetworkSettings.Networks}}{{println .IPAddress}}{{end}}'
    kafka_ip=$(timeout 10 docker inspect --format "$inspect_format" dcim-build-kafka-1 2>/dev/null) || fail "Kafka container address unavailable"

    helper="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/kafka_host.py"
    python3 "$helper" "$kafka_ip" "$original_hosts" "$updated_hosts" >/dev/null 2>&1 || fail "hosts mapping validation failed"

    if ! cmp -s -- "$original_hosts" "$updated_hosts"; then
      restore_required=1
      sudo -n tee -- /etc/hosts < "$updated_hosts" >/dev/null 2>/dev/null || fail "temporary hosts mapping could not be installed"
    fi
    ;;
  stopped|exited|created|dead)
    ;;
  *)
    fail "Kafka container state unavailable"
    ;;
esac

DCIM_KAFKA_BOOTSTRAP="kafka:9092" "$@"
exit $?
