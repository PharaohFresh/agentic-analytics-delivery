# Skills / Runbooks

A skill is a **declarative runbook** an agent executes — not a script. It states
the objective, the conditions that define success, the ordered procedure, and the
known failure modes. Agents read the runbook and carry it out; the determinism
lives in the *Verification Criteria*, not in brittle imperative code.

## Format

Each runbook is a Markdown file with YAML frontmatter:

| Field | Meaning |
|---|---|
| `name` | Unique, generic identifier |
| `description` | One-line summary of what it does |
| `version` | Semantic version of the runbook |
| `scope` | Target system category (e.g. `data_warehouse`, `bi_platform`) |

…followed by four required sections:

- **`# Objectives`** — the goal and context, in the abstract.
- **`# Verification Criteria`** — hard, checkable conditions for success. These map
  to the checks the Verification Analyst runs.
- **`# Procedure`** — the ordered steps the executing agent follows.
- **`# Troubleshooting`** — known exceptions and their remediation.

## Inventory

| Runbook | Purpose |
|---|---|
| [`data-migration-standard`](data-migration-standard.md) | Move a model between environments with grain-preserving integrity checks |
| [`bi-report-migration`](bi-report-migration.md) | Rebind a BI report to a new model and validate it |
| [`issue-sync`](issue-sync.md) | Reconcile local task state with the issue tracker |
