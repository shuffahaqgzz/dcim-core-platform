# GitHub Repository Setup Runbook

Repository: `shuffahaqgzz/dcim-core-platform`  
Milestone: Dev Platform Bootstrap v0.1  
Owner: `@shuffahaqgzz`

This runbook covers GitHub controls that cannot be enforced by committed files alone. Apply it after the bootstrap pull request has produced its first successful checks and before merging substantive implementation work.

## 1. Confirm repository identity and visibility

In **Settings → General**:

- repository name: `dcim-core-platform`;
- visibility: Public, as already decided for generic code and synthetic evidence;
- default branch: `main`;
- description: `Public-safe Development bootstrap for the DCIM Core Platform`;
- suggested topics: `dcim`, `infrastructure-management`, `observability`, `event-driven`, `docker-compose`, `prototype`.

Keep Issues enabled. Keep Wiki and Discussions disabled until an owner decision defines their moderation and data-handling model. Projects may be enabled only when it has a named owner and no private operational content.

## 2. Configure merge behavior

Under **Settings → General → Pull Requests**:

- enable **Allow squash merging**;
- disable merge commits and rebase merging for the current owner-led phase;
- set the squash commit title to the pull-request title or Conventional Commit title;
- enable automatic deletion of head branches;
- keep auto-merge disabled during prototype/alpha Development;
- require every change after the bootstrap to use a pull request.

Reason: a focused squash history is easier to audit, revert, and hand over. Auto-merge would weaken the explicit Development owner gate.

## 3. Create an active branch ruleset for `main`

In **Settings → Rules → Rulesets**, create `main-development-gate` targeting the default branch.

Enable:

- restrict deletions;
- block force pushes;
- require a pull request before merging;
- require conversation resolution;
- require status checks to pass;
- require branches to be up to date before merging;
- require linear history;
- prevent bypass except for the repository owner during an explicitly recorded recovery event.

After the bootstrap PR has run once, select these required checks by their exact job names:

- `preflight`;
- `gitleaks`;
- `dependency-review`.

### Solo-Development review setting

Use **zero required approving reviews** while the owner is the only developer. GitHub does not treat self-review as independent approval, and the agreed Development gate is evidence-backed owner review recorded in the PR. Do not require CODEOWNER approval yet.

At Controlled Handover or Staging entry, change the ruleset to require at least one independent approving review, dismiss stale approvals, require CODEOWNER review for governed paths, and restrict bypass to named authorities.

## 4. Protect Development release tags

Create a tag ruleset targeting `dev-v*`:

- block deletion and update of existing tags;
- restrict tag creation to the owner or future release authority;
- do not create `stable`, `production`, or unqualified `v1.0` tags during this milestone.

A `dev-v0.1.0` tag is eligible only after the evidence and handover gates in the Development baseline pass.

## 5. Enable security features

In **Settings → Security & analysis** enable:

- dependency graph;
- Dependabot alerts;
- Dependabot security updates;
- secret scanning;
- push protection for supported secrets;
- private vulnerability reporting.

Do not add a broad CodeQL workflow until OD-07 selects the service language/framework and the workflow can be scoped and tested. Add CodeQL in the first implementation PR for each supported language.

Review the repository’s public commit history after the bootstrap. If suspected live data or a secret is found, rotate/revoke first, then follow the governed history-cleanup process in `DATA-HANDLING.md`.

## 6. Restrict GitHub Actions

In **Settings → Actions → General**:

- allow only GitHub-authored and explicitly reviewed third-party actions;
- require actions to be pinned to immutable commit SHAs;
- set workflow `GITHUB_TOKEN` permissions to **Read repository contents** by default;
- do not allow Actions to create or approve pull requests globally;
- retain workflow logs/artifacts only as long as needed for Development evidence;
- do not register a self-hosted runner connected to office/Production networks.

The committed workflows declare least-privilege permissions and use synthetic repository content only. Any future job that needs a write token, environment secret, artifact upload, or external service must have a separate issue and threat review.

## 7. Environments and secrets

Create no `production` environment during this milestone.

Optional GitHub environments may be created for metadata only:

- `dev-build` — synthetic build/test, no office secrets;
- `dev-demo` — synthetic or approved sanitized data only.

`dev-integration-ro` remains a private, manually promoted runtime plane outside GitHub-hosted CI. Do not store office endpoints, source credentials, certificates, raw payloads, or topology as repository/environment secrets merely to make Actions reach that plane.

The expected initial repository secret count is **zero**.

## 8. Collaborators and ownership

During solo Development:

- owner/admin: `@shuffahaqgzz`;
- no anonymous write access;
- no automation account with admin scope;
- `CODEOWNERS` documents ownership but is not an independent approval gate.

Before multi-team Staging, replace the single owner with named teams for Product/Architecture, Platform/SRE, Data/Integration, Security, QA/UAT, and domain ownership. Review every bot/app permission at that transition.

## 9. Issue, milestone, and label setup

Create milestone `Dev Platform Bootstrap v0.1` with no Production claim. Recommended labels:

- `area:repo`, `area:platform`, `area:connector`, `area:data-contract`, `area:asset-cmdb`, `area:dashboard`, `area:workflow`, `area:hermes`;
- `type:task`, `type:adr`, `type:bug`, `type:security`;
- `priority:p1`, `priority:p2`;
- `gate:blocked`, `gate:evidence-needed`, `public-safe`.

Do not encode a private source name, site, device, incident, or topology in labels, milestones, issue titles, or project fields.

## 10. Verification record

Record a public-safe comment in the repository-settings issue containing:

- date/time in UTC;
- settings reviewer;
- active ruleset names and target patterns;
- exact required status-check names;
- enabled security features;
- Actions default token posture;
- repository secret count, without listing secret names;
- self-hosted runner count;
- deviations and expiry for any temporary exception.

Close C-02 only after the bootstrap PR is merged, the settings above are verified, `make preflight` passes on `main`, and a public-history review finds no prohibited material.
