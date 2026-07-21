#!/usr/bin/env bash
set -euo pipefail

psql --set=ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=credential_clause=PASSWORD \
  <<'SQL'
\set monitor_value `tr -d '\r\n' </run/secrets/postgres-monitor-password`
\set smoke_value `tr -d '\r\n' </run/secrets/postgres-smoke-password`
CREATE ROLE dcim_monitor LOGIN :credential_clause :'monitor_value';
GRANT pg_monitor TO dcim_monitor;
GRANT CONNECT ON DATABASE dcim_foundation TO dcim_monitor;
CREATE ROLE dcim_smoke LOGIN :credential_clause :'smoke_value';
GRANT CONNECT ON DATABASE dcim_foundation TO dcim_smoke;
CREATE SCHEMA foundation AUTHORIZATION dcim_smoke;
SQL
