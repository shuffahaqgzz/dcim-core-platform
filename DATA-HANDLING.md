# Data Handling — Public Repository

## Purpose

This file defines the enforceable boundary between public development artifacts and private runtime/operations material.

## Allowed in Git

- generic source code and configuration templates;
- generic JSON/Avro schemas;
- synthetic fixtures using reserved domains or invented identifiers;
- sanitized architecture diagrams without real topology;
- public-safe test evidence with identifiers and payloads removed;
- generic deployment and runbook templates.

## Prohibited in Git, Issues, PRs, Actions logs, agent prompts, and demos

- credentials, tokens, keys, certificates, passwords, SNMP community strings;
- real IP addresses, hostnames, FQDNs, serial numbers, asset tags, rack/site/camera names;
- source inventories, firewall matrices, management-network details, or office topology;
- raw Redfish/SNMP/ISAPI/syslog payloads, packet captures, logs, traces, database dumps, backups;
- unredacted screenshots, recordings, tickets, incident text, or model prompts containing operational evidence;
- video footage or exported camera content;
- any material whose authorization or classification is unknown.

## Logical planes

1. **DEV-BUILD / SIMULATION** — mutable code and synthetic fixtures.
2. **DEV-INTEGRATION-RO** — manually promoted, pinned images; dedicated read-only credentials; restricted network and egress; private runtime storage.
3. **DEV-DEMO** — synthetic or approved sanitized snapshots only.

The planes use separate Compose project names, networks, volumes, environment files, and credentials. Runtime material stays outside the repository.

## Sanitization rule

Sanitization must remove or irreversibly replace direct identifiers, quasi-identifiers, endpoint details, topology, free-text secrets, and unique operational patterns. Aggregation alone is not sufficient when small populations could reveal a device or site.

A second-person review is required before public release once the project moves beyond solo Development. During solo Development, the owner records the sanitization method and runs automated public-safety checks.

## Stop conditions

Stop the task immediately and notify the owner when:

- live or suspected live data appears in the workspace;
- a connector can perform write/control operations;
- a prompt or tool proposes sending office data to an external service;
- source authorization is missing;
- the collector or Hermes access cannot be stopped quickly;
- sanitization cannot be proven.

## Incident response for accidental publication

1. Stop further pushes and disable affected automation.
2. Revoke/rotate exposed credentials before history cleanup.
3. Preserve a private incident record; do not copy the secret into a public issue.
4. Remove the material from current Git history using an approved history-rewrite procedure.
5. Re-run secret/public-safety scans and review forks/caches.
6. Document a sanitized post-incident action and prevention control.
