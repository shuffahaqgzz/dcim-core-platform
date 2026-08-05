"""Create the advisory workflow draft store and its least-privilege role."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from scripts.phase2.db import literal


MIGRATION_ID: Final = "m0004_workflow_drafts"
DRAFT_TYPES: Final = ("notification", "ticket_draft", "approval_request")
STATUSES: Final = ("draft", "simulated_approved", "simulated_rejected")


def up(context: Mapping[str, Mapping[str, str]]) -> str:
    """Render the workflow draft table, role, and exact grants."""
    credential_literal = literal(context["role_passwords"]["dcim_workflow_rw"])
    draft_types = ", ".join(literal(value) for value in DRAFT_TYPES)
    statuses = ", ".join(literal(value) for value in STATUSES)
    return f"""CREATE TABLE phase2.workflow_drafts (
    draft_id uuid PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    event_id uuid NULL REFERENCES phase2.events(event_id),
    draft_type text NOT NULL CHECK (draft_type IN ({draft_types})),
    payload jsonb NOT NULL,
    status text NOT NULL CHECK (status IN ({statuses})),
    audit jsonb NOT NULL
);
DO $$ BEGIN CREATE ROLE dcim_workflow_rw LOGIN PASSWORD {credential_literal};
EXCEPTION WHEN duplicate_object THEN ALTER ROLE dcim_workflow_rw PASSWORD {credential_literal}; END $$;
GRANT SELECT, INSERT, UPDATE ON phase2.workflow_drafts TO dcim_workflow_rw;
GRANT SELECT ON phase2.events TO dcim_workflow_rw;
GRANT REFERENCES ON phase2.events TO dcim_workflow_rw;
"""


def down() -> str:
    """Drop m0004 objects in dependency order."""
    return """DROP TABLE phase2.workflow_drafts;
REVOKE SELECT, REFERENCES ON phase2.events FROM dcim_workflow_rw;
DROP ROLE IF EXISTS dcim_workflow_rw;
"""
