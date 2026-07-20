#!/usr/bin/env bash
set -euo pipefail

monitor_value="$(tr -d '\r\n' </run/secrets/postgres-monitor-password)"
smoke_value="$(tr -d '\r\n' </run/secrets/postgres-smoke-password)"

psql --set=ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=credential_clause=PASSWORD \
  --set=monitor_value="$monitor_value" --set=smoke_value="$smoke_value" <<'SQL'
CREATE ROLE dcim_monitor LOGIN :credential_clause :'monitor_value';
GRANT pg_monitor TO dcim_monitor;
GRANT CONNECT ON DATABASE dcim_foundation TO dcim_monitor;
CREATE ROLE dcim_smoke LOGIN :credential_clause :'smoke_value';
GRANT CONNECT ON DATABASE dcim_foundation TO dcim_smoke;
CREATE SCHEMA foundation AUTHORIZATION dcim_smoke;
SQL
