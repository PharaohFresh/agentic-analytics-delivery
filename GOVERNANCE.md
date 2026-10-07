# Governance and implementation scope

## Current executable scope

The program changes only synthetic JSON files inside a local sandbox. Catalog `prod`/`dev` values describe invented metadata; they are not connected workspaces. No production, cloud or employer adapter is implemented.

Execution requires an unchanged exact plan and a matching explicit approval file. The sample demo creates a clearly labeled synthetic approver record. This attestation binds reviewed content, but does not authenticate identity or supply production authorization.

## Enterprise promotion pattern

Real development and production are separate targets. Develop and verify in a sandbox, attach the exact plan and diff to a PR, obtain human review and promote only through the authorized production pipeline. A runtime flag or a passing test is not owner permission to deploy. No self-merge to production is included in the local demonstration.

## Evidence and data integrity

Source manifests use content hashes. Historical before states, approved plans, failed candidates and final receipts are retained. Current working fixture/checkpoint files are mutable; completed evidence is not overwritten.

The separate SQL harness checks row counts, key integrity/coverage, orphan items, null prices and item values/parent mappings by key. It does not prove every business calculation or an unobserved downstream outcome. Failed checks remain failures.

## Rollback and partial outcomes

A failed final local verification retains the failed catalog and restores the current working fixture to its before snapshot. A retry-exhausted run remains partial. Crash-window recovery requires the exact write-ahead event and expected catalog state. Historical evidence stays intact.

Cloud effects may need provider-specific compensation and may not be reversible atomically. Do not describe a local restore or a commit revert as proof that external production state was restored.

## Credentials and disclosure

No credentials, private identifiers or employer data belong in repository files. A future adapter consumes credentials through its environment or managed tooling without logging secret values. Public fixtures, plans and receipts must remain synthetic.

Hash chaining detects changes against a retained known receipt. It does not secure editable local files against an attacker who can rewrite both journal and receipt. A real service needs independently protected approval and evidence stores.
