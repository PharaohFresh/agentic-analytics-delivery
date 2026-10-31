# Changelog

## 2026-10-31

- `delivery verify` now binds the whole `approval.json`. Its SHA-256 is recorded in the first journal record and in the receipt, and verify checks the retained approval against both. Before this, only the approval's plan hash and approver were checked, so editing another field such as `authorization_type` still verified. A receipt without the approval hash now fails verification instead of raising an error. The committed demo report, journal and receipt were regenerated; only the new field and the hashes that depend on it changed.
- `delivery verify` now also checks that the retained `approved-plan.json` and `before-catalog.json` hash to the receipt's plan and before hashes, and that `approval.json`'s plan hash and approver match the receipt and the journal's first approval record. Before this, editing the approver after a successful run still verified. Six new tests cover each check; the 41 existing tests pass, and the committed demo report, journal and receipt regenerate byte-identically.

## 2026-10-06

- Added a runnable synthetic SQL-lineage/environment delivery with exact-plan approval, bounded retries, write-ahead/checkpoint recovery, independent readback, retained failed candidates and hash-chained receipts.
- Expanded the SQLite harness from four to eleven checks, including stable-key value and parent reconciliation. Negative-path harness and delivery/integrity tests pass locally; unknown or computed lineage remains explicit.
- Rewrote the README and architecture/governance/routing documentation around implemented behavior, reviewer navigation, generated proof and explicit source/production boundaries. No live cloud or model adapter is implied.

A running log of delivered changes — the artifact the logging phase appends to.
Newest first. Each entry pairs the technical change with its verification result.

## 2026-06-27
- **Initial public release.** Sanitized reference architecture for the governed
  agentic analytics-engineering delivery pattern: four single-responsibility
  agents, MCP tool wiring by capability, declarative runbooks, a human approval
  gate, and an independent verification harness that runs against a SQLite demo
  fixture.
- Verification: `run_audit.py --demo` passes all checks.
