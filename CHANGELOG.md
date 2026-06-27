# Changelog

A running log of delivered changes — the artifact the logging phase appends to.
Newest first. Each entry pairs the technical change with its verification result.

## 2026-06-27
- **Initial public release.** Sanitized reference architecture for the governed
  agentic analytics-engineering delivery pattern: four single-responsibility
  agents, MCP tool wiring by capability, declarative runbooks, a human approval
  gate, and an independent verification harness that runs against a SQLite demo
  fixture.
- Verification: `run_audit.py --demo` passes all checks.
