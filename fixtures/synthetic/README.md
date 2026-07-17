# Synthetic Fixtures

Everything in this directory is invented for public contract and integration tests. Reserved `.invalid` domains and explicit `SYNTHETIC-*` identifiers are used deliberately.

Do not replace these fixtures with captures from office/Production systems. Reproduce new cases by constructing the minimum synthetic payload that demonstrates the behavior and document its expected outcome.

Sanitization contract memakai input/expected pair pada `sanitization/` dengan supplied synthetic test salt `phase0-fixture-salt-v1`. Salt ini hanya test vector, bukan runtime salt atau credential.
