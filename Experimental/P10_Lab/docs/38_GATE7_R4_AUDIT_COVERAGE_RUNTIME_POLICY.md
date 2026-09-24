# ConceptGhost P10 — Gate 7 r4 Audit + COLMAP Coverage Runtime Policy

Date: 2026-09-24

## Why r3 stopped

The r3 runtime passed the previous native COLMAP binary-model defect, then reached Gate 7.3 and detected that five authored dataset frames were not present in the dense registered sparse model.

This is a different class of condition: COLMAP may legitimately fail to register some generated views. Gate 7 must not invent those views, but it also should not require a mathematically unnecessary 100% registration rate.

## r4 COLMAP policy

Gate 7.3 now uses only the intersection of:

1. authoritative Gate 6 dataset frames;
2. views actually registered by COLMAP;
3. views with valid geometric depth maps;
4. views with valid geometric consistency graphs.

Missing authored views are diagnostic UNKNOWN. They are never interpreted as FREE space.

Fail-closed thresholds:

- usable frame coverage >= 70%;
- qualifying mission coverage >= 70%;
- a mission qualifies when >= 70% of its authored frames are usable;
- at least two independent missions must qualify;
- any COLMAP view outside the authoritative Gate 6 dataset still fails.

The free-space manifest records the exact denominator, registered count, usable count, missing views, per-mission ratios and the final coverage decision.

## Automatic RUN_AUDIT_BUNDLE

The earlier terminal-only audit behavior meant that an exception in Gate 7 node 2400 prevented the downstream audit node from ever executing. r4 removes that blind spot.

Gate 7 now writes an audit automatically:

- success: automatic PASS audit immediately after Gate 7 runtime;
- failure: automatic PARTIAL_FAILURE audit before the exception is re-raised;
- terminal audit node: rebuilds the same audit after visual evidence is available.

Canonical Drive-visible storage:

`G:\My Drive\ConceptGhost\Outputs\ConceptGhost\concept_scene\P10_AUDITS\<P9_RUN>\<P10_ATTEMPT>\`

Files:

- `RUN_AUDIT_BUNDLE.zip`
- `RUN_AUDIT_BUNDLE_manifest.json`

Pointers directly under `concept_scene\P10_AUDITS`:

- `LATEST_AUDIT.txt`
- `LATEST_AUDIT_MANIFEST.txt`
- `LATEST_AUDIT_INDEX.json`

The accepted P9 run remains immutable; the audit is a sibling sidecar tree.

## Authority

P9 camera, geometry and scale are unchanged.
Missing COLMAP views cannot produce FREE evidence.
Gate 8 remains blocked pending real Gate 7 runtime/visual acceptance.
