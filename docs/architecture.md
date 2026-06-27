# Architecture

A deeper write-up of the delivery pattern. The [README](../README.md) is the
overview; this is the design rationale, sanitized to the pattern only.

## 1. System overview

The system automates the lifecycle of analytics-engineering changes — data model
deployments, BI report updates, and issue-tracker sync — through structured,
single-responsibility agents operating under a strict human-in-the-loop contract.
It moves sequentially: an autonomous planning phase produces an artifact, a human
approves it, and only then does the orchestrator coordinate execution against a
sandbox, an independent verification pass, and logging. Separating planning,
execution, and verification is what makes the changes reliable and governed.

## 2. Agents

Four single-responsibility roles (full definitions in [`agents/`](../agents)):

- **Orchestrator** — owns the task, writes the plan, holds the approval gate,
  delegates, compiles logs. Plans and coordinates; does not mutate directly.
- **Investigator** — read-only context gathering across repo, schemas, docs, and
  references. Planning phase only.
- **Execution Engine** — applies the approved plan to the sandbox. The only agent
  that mutates, and only after approval.
- **Verification Analyst** — independent, read-only audits whose verdict gates
  completion.

## 3. MCP servers / tools

Tool access is via MCP servers grouped by the *category* of system they connect to
(template: [`configs/mcp_config.example.json`](../configs/mcp_config.example.json)).
Every tool is explicitly read-only or write, so least-privilege is auditable:

| Category | Read-only | Write |
|---|---|---|
| Data warehouse | `execute_query`, `list_schemas_and_tables` | `deploy_view_definition` |
| BI / visualization | `list_reports`, `get_report_definition` | `rebind_report_datasource`, `trigger_model_refresh` |
| Issue tracker | `list_backlog_items`, `get_task_details` | `create_task`, `append_task_comment` |
| Object storage | `list_storage_contents`, `read_storage_file` | `write_storage_file`, `archive_storage_file` |

Note there is no `delete` anywhere — the closest write verb is `archive`, by design
(see Governance).

## 4. Skills / runbooks

Behavior lives in declarative runbooks ([`skills/`](../skills)), not imperative
scripts. Each states objectives, **verification criteria** (the checkable
definition of success), an ordered procedure, and known failure modes. Because the
success criteria are declarative, the same runbook is portable across targets and
the determinism sits in verification rather than brittle step code.

## 5. Orchestration & human-in-the-loop

```
intake -> [plan: autonomous] -> write plan -> {HUMAN APPROVAL GATE}
        -> [execute: autonomous, sandbox] -> [verify: autonomous]
        -> pass? -> [log + sync: autonomous]  |  fail? -> halt + rollback
```

**Requires approval:** any mutation of code, data, deployment config, or
schedules.
**Runs autonomously:** exploration, reads, planning, sandbox execution of an
approved plan, verification, logging.

## 6. Verification layer

Conceptually, the checks ([`scripts/checks.yml`](../scripts/checks.yml)) cover:

- **Row-count reconciliation** — source vs. target counts match exactly; nothing
  lost or duplicated.
- **Grain & join integrity** — the declared key is unique/non-null; no orphan rows
  or accidental Cartesian products.
- **Type & null safety** — casts (dates, numerics) did not silently produce nulls.
- **Freshness & completeness** — the pipeline ran to completion and the target is
  current.

Decision rule: a **zero-tolerance** policy on grain duplication and dropped rows.
Any failure marks the run FAILED, triggers rollback, and halts before prod.

## 7. Governance

Environment separation (dev vs. prod), an additive-only / no-deletion policy,
revert-based rollback, and PR-based promotion behind a human gate. Full detail in
[`GOVERNANCE.md`](../GOVERNANCE.md).

## 8. Repo layout

See the tree in the [README](../README.md#whats-in-here).

## 9. Tech stack

Agent runtime with Model Context Protocol for tool access; Python for the
verification harness; dbt + a SQL warehouse as the transformation/target layer;
Markdown + YAML for agents, skills, plans, and configuration.
