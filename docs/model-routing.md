# Model Routing

Agents in this system are *roles*, not models. Which model backs a role is a
separate, deliberate decision — and it is a cost decision as much as a quality
one. A delivery system that routes every phase to a frontier model works
beautifully in a demo and gets shut down the first time someone reads the
invoice. The routing policy below is what makes the pattern economically
sustainable in continuous operation.

## The principle: a thin judgment layer

The frontier model is a **thin orchestration and judgment layer**, not the
workhorse. It plans, decomposes, delegates, reviews what came back, owns
cross-source reconciliation, and renders final verdicts. Everything mechanical —
discovery sweeps, file builds, exports, runbook execution, simple lookups — is
delegated down to cheaper tiers that are entirely adequate for bounded,
procedural work.

Two rules keep the judgment layer thin:

1. **The orchestrator does not bulk-read what a subagent can summarize.**
   Reading forty files to answer one question is retrieval work; it burns
   frontier-model context on mechanical scanning. Dispatch it, get the summary
   back, keep the judgment layer's context for judgment.
2. **Anything irreversible or human-facing passes through the judgment layer
   first.** Cheap tiers produce; the judgment layer reviews before anything is
   promoted, logged as complete, or shown to the human at the gate.

## The tiers

| Tier | What runs here | Model class (example) |
|---|---|---|
| **Judgment** | Planning, decomposition, review of subagent output, cross-source reconciliation, final verdicts, everything at the approval gate | Frontier (Fable/Opus-class) |
| **Procedural** | Multi-step mechanical work: discovery sweeps, applying an approved plan, running a runbook, building files, executing the verification suite | Mid-tier (Sonnet-class) |
| **Retrieval** | Single-purpose searches, file reads, simple lookups with a narrow, verifiable answer | Small (Haiku-class) |

## Routing by role

| Role | Tier | Why |
|---|---|---|
| [Orchestrator](../agents/orchestrator.md) | Judgment | Every responsibility it has — plan, gate, review, verdict — is judgment work. It is also the *only* role that needs the frontier model. |
| [Investigator](../agents/investigator.md) | Procedural | Context gathering is a bounded sweep with a defined deliverable. Its simple lookups route further down to retrieval. |
| [Execution Engine](../agents/execution-engine.md) | Procedural | It applies an *approved* plan exactly as written. The judgment already happened at the gate; execution is deliberately mechanical. |
| [Verification Analyst](../agents/verification-analyst.md) | Procedural | The checks are declarative and the harness is deterministic — running them is procedural. The *interpretation* of the result is not (see below). |

## Escalation rules

Route **up** to the judgment layer when:

- a subagent hits ambiguity, contradiction between sources, or anything the plan
  did not anticipate — procedural tiers report deviations, they do not resolve
  them;
- a step is irreversible, human-facing, or touches the approval gate;
- results from independent subagents must be reconciled into one conclusion.

Never route **down**: plan authorship, approval-gate interactions, rollback
decisions, or the final pass/fail verdict on a run.

## The skepticism rule

The most important operational lesson in this document: **treat a cheap model's
"no gaps / all clear" conclusion with extra skepticism.** Smaller models are
reliable at finding what is there and unreliable at noticing what is missing —
an absence-of-evidence claim is exactly the shape of work they are worst at. So
a procedural-tier "all checks pass" or "nothing relevant found" is an input to
the judgment layer's review, never a terminal state. This is also why the
Verification Analyst's harness is deterministic code rather than model
judgment: the machine decides whether row counts reconcile; the judgment layer
decides what a failure means.

## What this buys

The frontier model's context window stays reserved for the decisions only it
can make, per-task cost drops by an integer factor (most tokens in a delivery
task are procedural), and — the underrated part — the review checkpoint that
cost-routing forces on you is the same checkpoint good governance wanted
anyway. Routing down without reviewing is how cheap mistakes become expensive;
the tier boundary and the judgment checkpoint are one mechanism, not two.
