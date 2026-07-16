#!/usr/bin/env bash
set -euo pipefail
umask 077

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
runtime_root="${DCIM_RUNTIME_ROOT:-$(dirname "$repo_root")/dcim-runtime}"
runtime_root="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$runtime_root")"

case "$runtime_root/" in
  "$repo_root/"*)
    printf 'ERROR: runtime root must be outside the public repository: %s\n' "$runtime_root" >&2
    exit 1
    ;;
esac

for command in git python3 make; do
  command -v "$command" >/dev/null 2>&1 || {
    printf 'ERROR: required command not found: %s\n' "$command" >&2
    exit 1
  }
done

mkdir -p \
  "$runtime_root/dev-build" \
  "$runtime_root/integration-ro" \
  "$runtime_root/demo"
chmod 700 "$runtime_root" "$runtime_root/dev-build" "$runtime_root/integration-ro" "$runtime_root/demo"

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  docker_status="available"
else
  docker_status="not installed or Compose plugin unavailable (required from Day 2)"
fi

if [[ -d "$repo_root/.git" ]]; then
  hook="$repo_root/.git/hooks/pre-commit"
  if [[ ! -e "$hook" ]]; then
    cat >"$hook" <<'HOOK'
#!/usr/bin/env bash
set -euo pipefail
exec make preflight
HOOK
    chmod 700 "$hook"
    hook_status="installed"
  else
    hook_status="kept existing hook"
  fi
else
  hook_status="skipped (bundle is not a Git checkout)"
fi

cat <<EOF
DCIM Development workspace prepared.
Repository:   $repo_root
Runtime root: $runtime_root
Docker:       $docker_status
Pre-commit:   $hook_status

Next:
  cd "$repo_root"
  make preflight

Do not copy office/Production environment files or data into this repository.
EOF
