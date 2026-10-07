# Changelog

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
