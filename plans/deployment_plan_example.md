# Deployment Plan — Add `mart_product_category_margin`

This is an illustrative historical-format example. The approver label and approval
date below are fictional demonstration text. Use `python -m delivery plan` and
the explicit approve/execute commands for a current content-bound local demo.

> **Status: APPROVED** ✅ — approved by `@data-lead` on 2026-06-20.
> This is the artifact the human approval gate operates on. Nothing in the
> Execution phase runs until this reads APPROVED.

## Task
Add a finance mart reporting revenue, gross margin, and return rate by product
category and department, sourced from the existing order-item fact.

## Context (from Investigator)
- Source: `fct_order_items` (grain: one row per order item). Carries `sale_price`,
  `unit_cost`, `is_returned`, `category`, `department`.
- No existing mart covers category-level margin; closest is revenue-by-channel.
- Downstream: one BI report will bind to this mart after it lands (separate task).

## Change
- New model `models/marts/finance/mart_product_category_margin.sql`,
  grain `(department, category)`, materialized as a table.
- New tests: `not_null` on `total_revenue`; grain uniqueness on the composite key.

## Runbook
`skills/data-migration-standard` (new-model variant).

## Verification criteria
- Grain `(department, category)` is unique and non-null.
- `sum(total_revenue)` reconciles to `sum(sale_price)` from `fct_order_items`.
- `return_rate` is within `[0, 1]` for every row.

## Rollback
Revert the commit; the mart is additive, so no downstream asset depends on it yet.

## Scope boundary
Sandbox (`dev`) only. No production build, no BI rebind in this task.
