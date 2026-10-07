# Delivery architecture and contracts

## Implemented components

The independent SQLite audit checks counts, key integrity, coverage and selected values/parent mappings. The `delivery` module parses static SQL dependencies, combines them with declared platform references, prepares an exact environment repair, requires a content-bound local approval and executes only against synthetic local files.

LLM inference, autonomous agent scheduling, MCP access, cloud deployment, real refresh monitoring and rendered BI validation are not implemented. Role/runbook files describe integration interfaces, not executed model calls.

## Catalog and lineage

Every asset has a unique ID, kind, environment and logical name. Kinds are source, table, view, pipeline and report. View definitions contain one static BigQuery-style query; platform dependencies are distinct asset IDs. SQLGlot scope analysis distinguishes physical references from CTE/subquery sources.

Named references are resolved against the catalog. Unknown assets, parser failures and cycles stay visible. A production-labeled node referencing a development-labeled node raises an environment issue. Reverse impact is reported for downstream reports, while source categories remain explicitly declared metadata.

External/computed table references and table-valued functions require explicit lineage and are rejected by this parser path. Dynamic SQL and templated model definitions must be resolved before catalog auditing; they are not silently treated as source-free healthy views.

Planning supports only declared dependency-list repairs to one unique same-kind/logical-name production counterpart. It does not guess at ambiguous mappings, perform string replacement inside SQL, infer effective permissions or remediate every possible issue.

## Plan and approval

The plan contains the full before catalog, its hash, every operation, the initial audit and expected after hash. Validation regenerates the plan from its before state. Approval binds the canonical plan SHA-256. Modified plans and unsupported execution targets fail before writes.

The approver label is a local attestation. The program does not authenticate who created it. Real authority needs a trusted store and identity outside the caller's editable files.

## Execution and recovery

Each change has a stable operation ID. Before an attempt, execution appends a write-ahead event. It writes the next expected catalog atomically, reads it back, records the applied operation and checkpoints it. Retryable failure injection exercises a bounded attempt loop.

On resume, the current catalog must equal the approved before state plus checkpointed changes. For a crash between a write and checkpoint, recovery accepts exactly the next operation only if the last started, applied or recovered journal event identifies that approved plan/operation and the complete catalog matches its expected result. Started events must bind the expected before hash; applied events must bind the observed after hash. Repeated crashes before the execution or recovery checkpoint are covered by regression tests. Unrelated drift fails.

Final verification independently reads the catalog, checks its approved expected hash and re-runs the graph audit. Failure retains the candidate, restores the current working fixture, resets its checkpoint and logs restoration. This is local rollback only; a cloud API may require a different compensating action.

## Integrity

A source manifest records bytes and SHA-256 for files within a resolved root. Paths escaping the root fail. A content change of unchanged size still fails verification.

Journal records contain sequence, prior-record hash, event and payload. The final receipt retains the expected count and tip hash. Verification detects edited, reordered, deleted or appended records against that known tip. Hash chaining supplies integrity evidence, not authentication or an independently secured immutable store.

## Data audit scope

The eleven SQL checks cover the fields explicitly present in the tiny fixture. They do not establish freshness, comprehensive type/cast safety, every downstream financial formula or full warehouse equivalence. New domains need new contracts and negative-path cases; a green harness is evidence for its checks, not a universal business verdict.

## Production adaptation

Bind live resource identity and approved scope, use least-privilege credentials, test the actual provider's retry/idempotency behavior, enforce concurrency control, protect approvals and receipts independently, and perform final readback at the affected data/model/report layer. Keep production promotion a separate reviewed action.

The SQL parser uses the [SQLGlot scope interface](https://sqlglot.com/sqlglot/optimizer/scope.html). Only the documented static-query and named-asset scope is represented here.
