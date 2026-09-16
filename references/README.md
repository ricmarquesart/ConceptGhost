# ConceptGhost Reference Sources

This directory defines the permanent upstream evidence used by ConceptGhost.

## Baseline-first rule

For every stage that depends on camera solving, depth, geometry, mesh generation, DCC export, or perspective matching, ConceptGhost must identify an existing public implementation, pin the exact upstream revision, and test that original baseline before adding project-specific adapters.

The authoritative machine-readable index is `SOURCE_LOCK.json`.

## Storage model

- **GitHub ConceptGhost** stores the source lock, audit notes, collectors, verifier, tests, and links.
- **Google Drive** stores frozen physical mirrors under `G:\My Drive\ConceptGhost\References\Upstream_Code`.
- `G:\My Drive\ConceptGhost\References\Audit_and_Videos` stores verification reports and evidence notes.

The Google Drive mirrors are not runtime dependencies. They are an archival and audit layer so the exact code used as a reference remains available even if upstream changes.

## Do not vendor upstream projects into this repository

Do not vendor complete third-party repositories into ConceptGhost merely for convenience. Keep their source code in the frozen Google Drive mirror and keep only the immutable source metadata, integration notes, and project-owned adapters here. This keeps licensing, attribution, repository size, and ownership boundaries clear.

## Required workflow before a new stage

1. Read the relevant entry in `SOURCE_LOCK.json`.
2. Run `tools\VERIFY_REFERENCE_CODE.bat` and confirm the source exists at the locked revision.
3. Identify the original upstream workflow/example that demonstrates the needed behavior.
4. Run the upstream baseline unchanged whenever practical.
5. Record the baseline result.
6. Only then implement a ConceptGhost adapter or hybrid workflow.

If a required reference is missing or its revision differs from the lock, stop that stage until the reference is restored or the lock is deliberately reviewed and updated.

## Updating a pin

A pin is not updated casually. A change requires:

- a reason for moving from the old revision;
- re-audit of the affected workflow/example;
- compatibility check against the current ConceptGhost environment;
- update to `SOURCE_LOCK.json` and the collector in the same change;
- passing CI.

This makes the reference set reproducible instead of silently following upstream `main` branches.
