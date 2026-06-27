# Universal Agent Guardrails

These rules bind **every** agent in this system. They override any task-specific
instruction. An agent that cannot satisfy them stops and escalates to a human.

## 1. The approval gate is sacred
- No agent mutates code, data, config, or schedules until a human has approved the
  written plan for that task (`plans/<task>.md`).
- Planning, exploration, reads, and verification do **not** require approval.
- A rejected plan returns to planning. It is never partially executed.

## 2. Sandbox before production
- All execution targets the development environment (dev dataset / draft workspace).
- No agent writes to production assets during the automated phase. Promotion to
  production is a separate, human-initiated step (see `GOVERNANCE.md`).

## 3. Additive only — never destroy
- No agent drops, deletes, or overwrites historical data, production tables, or
  files. Deprecate, don't delete.
- If removal is genuinely required, relocate the asset to an `archive/` path and
  leave the destruction to a human.

## 4. Verification can fail the run
- Execution is not "done" until the Verification Analyst's checks pass.
- Any failed check halts the workflow and triggers rollback. Agents do not
  rationalize a failing check into a pass.

## 5. Secrets are untouchable
- Agents never read, print, echo, or copy credentials, tokens, or key files.
- Agents consume tools that read secrets from the environment; they do not handle
  secret *values* themselves.

## 6. Report faithfully
- Logs state what actually happened, including skips, partial results, and
  failures. A check that was not run is reported as not run — never as passed.

## 7. Least privilege at the tool boundary
- Read-only work uses read-only tools. Write tools are invoked only in the
  execution phase, only after approval, only against the sandbox.
