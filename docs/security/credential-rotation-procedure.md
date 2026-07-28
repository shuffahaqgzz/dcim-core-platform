# Credential Rotation Procedure

This document defines the inventory and rotation procedure for the DCIM Core Platform. It contains no secret values, no endpoints, no identifiers, and no scan output — only procedure and template shape.

## Scope

- Covers `dcim-core-platform` service identities, signing material, and integration credentials only.
- Satellite repositories (data-collection adapter, wiki, and future connector runbooks) maintain their own rotation workstreams. This document references them only as separate workstreams.
- Filled authorization and credential-control records live outside Git in the owner-managed private store, per the C-04 owner direction in [`CONDITIONS-REGISTER.md`](../governance/CONDITIONS-REGISTER.md).

## Related policy and handling

- [`DATA-HANDLING.md`](../../DATA-HANDLING.md)
- [`SECURITY.md`](../../SECURITY.md)
- [`docs/templates/private-source-authorization-register.template.md`](../templates/private-source-authorization-register.template.md)
- [`docs/governance/CONDITIONS-REGISTER.md`](../governance/CONDITIONS-REGISTER.md) — C-04 remains OPEN; this procedure does not close it.

## Inventory procedure

Maintain a private credential-control record keyed by name only. The record must list the following fields for each credential, never the value.

| Field | Description |
|---|---|
| Credential key name | Stable identifier used in code and configuration; the value is in the private store. |
| Owning component | Service, plane, or connector that consumes the credential. |
| Type or class | Identity class, for example database identity, service account, client secret, signing key, API key, or read-only SNMP community reference. |
| Rotation owner | Person or role responsible for the rotation. |
| Expiry or review date | Maximum lifetime or next review date. |

Enumeration order:

1. Foundation data plane — database identity, messaging identity, internal signing or trust material used by core services.
2. Observability plane — metrics and logs scrape identity, dashboard service account.
3. Integration identities — dedicated read-only source credentials and external adapter credentials.

## Rotation ordering

When a rotation window is approved, rotate in this order.

1. Foundation data plane first.
2. Observability plane second.
3. Integration identities last.

Within each plane, rotate the least-privileged identities before broader ones, and rotate the credential with the nearest expiry first.

## Revocation

1. Issue a new identity through the approved private identity provider or control plane.
2. Update the consuming component with the new credential key name via the private configuration store.
3. Verify the component starts and behaves correctly with the new identity.
4. Disable or revoke the old identity.
5. Confirm no active session or token remains for the old identity.
6. Delete the old identity only after the safety retention window has passed.

## Post-rotation verification

1. Run the public-safety scanner against the repository and confirm no credential value appears.
2. Run the relevant unit and integration tests for the affected plane.
3. Verify the read-only scope for integration identities; negative tests must prove write and control classes remain unreachable.
4. Confirm the private credential-control record has been updated with the new key name, rotation owner, and expiry.
5. Record the rotation reference in the private register, not in this repository.

## Record location

Filled records and authorization registers are stored outside Git in the owner-managed private store. Reference them only by an approved private identifier. The store location is deliberately not recorded in this public repository.

## C-04 status

C-04 remains OPEN. The public side of this procedure supplies the shape and verification steps; the actual credential-control record and its review remain private and require owner closure.
