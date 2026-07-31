"""Create the Phase 2 core schema.

``dispositions.event_id`` is deliberately nullable and has no foreign key:
quarantined inputs may omit an event ID, carry a non-UUID identifier, or name
an event that was never stored. Such inputs have no guaranteed referential
target, while their disposition must still be retained.
"""

from __future__ import annotations


MIGRATION_ID = "m0001_phase2_core"


def up() -> str:
    """Return SQL that creates the complete Phase 2 core schema."""
    return """
CREATE SCHEMA IF NOT EXISTS phase2;

CREATE TABLE phase2.schema_migrations (
    migration_id text PRIMARY KEY,
    applied_at timestamptz
);

CREATE TABLE phase2.run_manifests (
    run_id text PRIMARY KEY,
    fixed_clock timestamptz,
    source_count int,
    manifest_sha256 text,
    created_at timestamptz
);

CREATE TABLE phase2.events (
    event_id uuid PRIMARY KEY,
    run_id text REFERENCES phase2.run_manifests(run_id),
    envelope jsonb,
    content_sha256 text NOT NULL,
    ingested_at timestamptz
);

CREATE TABLE phase2.dispositions (
    disposition_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id uuid NULL,
    run_id text NOT NULL REFERENCES phase2.run_manifests(run_id),
    status text CHECK (status IN ('accepted', 'quarantined', 'duplicate')),
    reason text,
    lineage jsonb,
    decided_at timestamptz
);

CREATE TABLE phase2.assets (
    asset_id uuid PRIMARY KEY,
    identity jsonb,
    asset_type text,
    created_at timestamptz,
    updated_at timestamptz
);

CREATE TABLE phase2.cis (
    ci_id uuid PRIMARY KEY,
    asset_id uuid NULL REFERENCES phase2.assets(asset_id),
    source_system text,
    native_device_id text,
    ci_type text,
    created_at timestamptz,
    updated_at timestamptz
);

CREATE TABLE phase2.aliases (
    alias_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    owner_type text CHECK (owner_type IN ('asset', 'ci')),
    owner_id uuid,
    type text,
    value text,
    valid_from timestamptz,
    valid_to timestamptz NULL,
    source text,
    confidence int
);

CREATE TABLE phase2.noc_cards (
    run_id text NOT NULL REFERENCES phase2.run_manifests(run_id),
    kind text NOT NULL,
    subject_key text NOT NULL,
    payload jsonb,
    generated_at timestamptz,
    PRIMARY KEY (run_id, kind, subject_key)
);
"""


def down() -> str:
    """Return SQL that removes the complete Phase 2 schema."""
    return "DROP SCHEMA phase2 CASCADE;\n"
