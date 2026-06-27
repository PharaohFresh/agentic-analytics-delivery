---
name: issue-sync
description: Reconcile local task/TODO state with the remote issue tracker, additively.
version: 1.0.0
scope: issue_tracker
---

# Objectives
Keep the local task ledger and the remote issue tracker in agreement: completed
work is reflected, new work is registered, and nothing is silently dropped.

# Verification Criteria
- Every local task maps to exactly one tracker item (no duplicates created).
- Status changes are reflected as comments/updates, not destructive edits.
- No tracker item is deleted by automation.

# Procedure
1. **Read both sides** — local task file and the tracker backlog (Investigator).
2. **Diff** — classify each item: new, updated, already-synced.
3. **Plan** — list the creates/comments to be made; submit for approval.
4. **Apply** — create missing items; append structured status comments.
5. **Log** — record the sync result and the mapping in the CHANGELOG.

# Troubleshooting
- *Duplicate risk*: match on a stable external key before creating; if unsure,
  surface for human review rather than creating a possible duplicate.
- *Ambiguous mapping*: never guess across many candidates — escalate.
