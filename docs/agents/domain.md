# Domain Docs

How engineering skills consume this repo's domain documentation.

## Before exploring, read these

- **`CONTEXT.md`** at repo root.
- **`CONTEXT-MAP.md`** if it exists; read each relevant context.
- **`docs/adr/`**; read ADRs touching the work area.

If files don't exist, proceed silently. `/domain-modeling` creates them lazily when terms or decisions get resolved.

## File structure

Single-context layout:

```
/
├── CONTEXT.md
├── docs/adr/
└── src/
```

## Use the glossary's vocabulary

Use terms defined in `CONTEXT.md`. Avoid rejected synonyms. Missing concepts may reveal either invented language or a genuine domain-model gap.

## Flag ADR conflicts

Surface contradictions with existing ADRs instead of silently overriding them.
