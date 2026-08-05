"""Create CI relationships and the four Phase 3 service roles."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from scripts.phase2.db import literal

MIGRATION_ID: Final = "m0003_ci_relationships"
ROLES: Final = ("dcim_assets_rw", "dcim_cmdb_rw", "dcim_api_ro", "dcim_analytics_ro")
RELATIONSHIP_TYPES: Final = ("depends_on", "runs_on", "connected_to", "contains", "hosted_on", "part_of", "monitors")


def up(context: Mapping[str, Mapping[str, str]]) -> str:
    """Render the reversible CI-relationship and service-role migration."""
    passwords = context["role_passwords"]
    role_sql = "\n".join(
        f"DO $$ BEGIN CREATE ROLE {role} LOGIN PASSWORD {literal(passwords[role])}; "
        f"EXCEPTION WHEN duplicate_object THEN ALTER ROLE {role} PASSWORD {literal(passwords[role])}; END $$;"
        for role in ROLES
    )
    types = ", ".join(literal(value) for value in RELATIONSHIP_TYPES)
    return f"""CREATE TABLE phase2.ci_relationships (
    relationship_id uuid PRIMARY KEY,
    from_ci uuid NOT NULL REFERENCES phase2.cis(ci_id),
    to_ci uuid NOT NULL REFERENCES phase2.cis(ci_id),
    relationship_type text NOT NULL CHECK (relationship_type IN ({types})),
    valid_from timestamptz,
    valid_to timestamptz,
    source text,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ci_relationships_current_unique
    ON phase2.ci_relationships (from_ci, to_ci, relationship_type)
    WHERE valid_to IS NULL;
{role_sql}
GRANT SELECT, INSERT, UPDATE ON phase2.assets, phase2.aliases TO dcim_assets_rw;
GRANT SELECT, INSERT, UPDATE ON phase2.cis, phase2.ci_relationships TO dcim_cmdb_rw;
GRANT REFERENCES ON phase2.assets TO dcim_cmdb_rw;
GRANT SELECT ON phase2.noc_cards, phase2.events, phase2.dispositions TO dcim_api_ro;
GRANT SELECT ON phase2.events, phase2.dispositions, phase2.run_manifests, phase2.noc_cards TO dcim_analytics_ro;
"""


def down() -> str:
    """Drop m0003 objects in dependency order."""
    return """DROP TABLE phase2.ci_relationships;
DROP ROLE IF EXISTS dcim_analytics_ro;
DROP ROLE IF EXISTS dcim_api_ro;
DROP ROLE IF EXISTS dcim_cmdb_rw;
DROP ROLE IF EXISTS dcim_assets_rw;
"""
