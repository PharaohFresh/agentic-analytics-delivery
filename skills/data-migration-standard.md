---
name: data-migration-standard
description: Move an analytical model between environments with strict, grain-preserving integrity verification.
version: 1.0.0
scope: data_warehouse
---

# Objectives
Relocate an analytical model from a source to a target environment while
preserving row grain, column types, and downstream report connections. The
migration is not complete until the target is provably equivalent to the source.

# Verification Criteria
- Source row count equals target row count exactly.
- The model's declared grain key is unique and non-null in the target.
- Join keys to parent tables have zero orphan records.
- Date/timestamp fields parse without producing nulls that were not null at source.

# Procedure
1. **Analyze schema** — capture source column types and nullability (Investigator).
2. **Plan** — write the migration plan to `plans/`; submit for approval.
3. **Deploy to sandbox** — build the model into the development environment only.
4. **Verify** — run the reconciliation checks above against source vs. target.
5. **Log** — record row counts, timestamps, and the pass verdict to the CHANGELOG.

# Troubleshooting
- *Type mismatch*: map source→target types explicitly with an explicit cast in the
  model; never rely on implicit coercion.
- *Row discrepancy*: full-outer-join on the grain key to isolate orphaned or
  duplicated rows, then fix the join logic — do not adjust the check.
- *Unexpected nulls*: trace the column to its staging transform; a silent cast
  failure is the usual cause.
