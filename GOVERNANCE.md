# Governance

The guardrails that make automated change *trustworthy*. The point isn't
ceremony — it's that a data team can rely on what the system ships.

## Environments
- **dev** and **prod** are separate targets (separate datasets/workspaces),
  selected by configuration.
- All automated work happens against **dev**. The execution phase never writes to
  prod.

## Promotion (dev → prod)
1. Build and verify in dev: every check in the runbook's *Verification Criteria*
   must pass.
2. Open a PR. The diff and the approved plan travel together.
3. **Human approval gate** — a reviewer signs off. No self-merge to prod.
4. Prod builds run only from the protected `main` branch via the approved pipeline.

## No-deletion policy
- Models/reports are deprecated, not dropped, on first pass. Renames go through a
  deprecation alias for one cycle.
- Snapshots and history are append-only and never rebuilt destructively.
- If removal is genuinely required, assets are relocated to `archive/` for a human
  to destroy — automation never deletes.

## Data integrity
- Every source has tests; every fact asserts its grain (unique + not-null key).
- `scripts/run_audit.py` reconciles counts independently of the agent that built
  the data — trust, but verify.

## Secrets
- Credentials live only in the environment / a gitignored config. `*.example`
  files are the templates.
- No keys, tokens, or account identifiers are ever committed. Agents never read
  secret values.

## Rollback
- Because promotion is PR-based and prod is rebuildable from version-controlled
  code, rollback = revert the commit and rerun the pipeline. A failed verification
  pass triggers this automatically before prod is ever touched.
