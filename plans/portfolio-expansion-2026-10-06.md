# Portfolio expansion implementation plan

Implementation authority: the owner requested adding the identified portfolio projects with thorough documentation on October 6, 2026. Work is scoped to original public demonstration code, synthetic fixtures, tests and documentation. Employer and private personal source repositories remain read-only.

## Changes

1. Strengthen the independent SQLite audit with key, value and parent-mapping checks.
2. Implement SQL lineage and environment auditing against synthetic platform definitions.
3. Demonstrate an exact-plan approval gate, local sandbox execution, bounded retries, checkpoints, independent readback and an append-only receipt chain.
4. Write recruiter-oriented README navigation, engineering documentation, executable examples and CI.
5. Prepare the feature branch for independent review and scoped GitHub delivery. Existing protected-branch promotion remains a human-reviewed step.

## Verification

- Seeded missing/duplicate/null/wrong-value/wrong-parent defects fail the appropriate checks.
- CTEs, aliases, comments, nested views, missing assets and cycles have explicit lineage behavior.
- An unapproved, modified or out-of-scope plan cannot execute.
- Partial execution can resume without repeating completed changes; unrelated state drift halts it.
- Failed verification restores the working fixture and retains immutable before/after evidence.
- A journal edit, deletion or reorder is detected.
- Default demos run locally without credentials, paid model calls, employer systems or external messages.

## Source and release boundaries

No employer code, SQL, identifiers, raw reports or source paths enter the repository. Generated examples identify their synthetic origin. The local fixture approval record is an attestation, not an authenticated production authorization service. No cloud adapter or production deployment is implied by this implementation.
