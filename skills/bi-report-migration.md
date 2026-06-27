---
name: bi-report-migration
description: Rebind a BI report to a new/updated semantic model and validate it renders with correct numbers.
version: 1.0.0
scope: bi_platform
---

# Objectives
Point an existing BI report at a new or restructured underlying model without
changing the numbers the report shows or breaking any visual.

# Verification Criteria
- Every field the report references resolves in the new model (no broken bindings).
- Headline metrics match the pre-migration values within tolerance (ideally exact).
- The data refresh completes successfully and freshness is current.

# Procedure
1. **Capture baseline** — read the current report definition and record its
   headline metric values (Investigator).
2. **Plan** — document the rebind + field mapping; submit for approval.
3. **Rebind in a draft copy** — never edit the live report during execution.
4. **Trigger refresh** — refresh the draft against the new model.
5. **Verify** — confirm all fields bind, metrics match baseline, refresh is green.
6. **Promote** — publish the draft over the live report only after human sign-off.

# Troubleshooting
- *Broken field binding*: the new model renamed/dropped a column — add a mapping or
  a backward-compatible alias rather than editing every visual.
- *Metric drift*: diff the new model's grain against the old; a changed grain
  double-counts. Reconcile at the warehouse layer before touching the report.
