# ConceptGhost P10 — Gate 7 Registration, Evidence Fusion & Provenance Plan

Date: 2026-09-23  
Status: IN PROGRESS — source development may proceed while DR9R r15 runtime UX acceptance is being tested. Promotion into a user-facing Gate 7 Preview remains blocked until the current DR9R runtime is accepted.

## Boundary

Gate 7 starts from one completed immutable P10 attempt whose Gate 6 runtime is PASS and whose geometry-quality status is not FAIL.

P9 remains the accepted immutable upstream authority. Gate 7 must not reshape, normalize, rescale, rotate or translate P9 to make P10 easier to fuse.

## Important coordinate decision

Current Gate 6 does not perform a free camera solve. It reconstructs with fixed virtual cameras derived directly from the P9 world.

Therefore Gate 7.1 is **not** a best-fit Sim(3) solve.

The correct first registration contract is:

`KNOWN_CAMERA_P9_WORLD_IDENTITY_REGISTRATION`

If the Gate 6 dataset proves that:
- its camera authority is `P9_BASELINE_WORLD_DERIVED`;
- its Scene Contract matches P9;
- its source P9 run matches the current authoritative P9 run;
- Gate 6 is promotable;
- its coordinate conversion is the frozen ConceptGhost/Maya → COLMAP camera convention;

then P10 reconstruction is already expressed in the P9 canonical metric world and the P10→P9 registration transform is identity.

A new similarity solve is forbidden in this path because it could silently move scale/orientation away from P9 authority.

## Gate 7 bounded subgates

### G7.1 — P10→P9 registration authority
Status: **IMPLEMENTED / CI PENDING**

Inputs:
- authoritative P9 run;
- Gate 6 reconstruction runtime manifest;
- WAN provenance;
- known-camera COLMAP dataset;
- P10 pre-fusion mesh.

Outputs:
- `gate7_registration.json`;
- explicit P9/P10 scene identity;
- identity 4×4 transform;
- scale = 1;
- translation = 0;
- no Sim(3) refit;
- fail-closed provenance checks.

Promotion is rejected if Gate 6 geometry quality is FAIL or if P9 run / Scene Contract / known-camera authority diverges.

### G7.2 — Authority-aware geometry provenance
Status: **NEXT**

Build a geometry provenance classification without modifying official geometry.

Initial classes:
- P9_SOURCE_PROTECTED;
- P9_RETAINED;
- P10_MULTIVIEW_SUPPORTED;
- P10_GENERATED_ONLY;
- UNKNOWN;
- CONFLICT.

The first implementation is evidence/diagnostic only. It must be possible to inspect which geometry comes from P9 versus P10 before any fusion operation can delete or replace geometry.

### G7.2C — Geometry confidence field
Status: **PLANNED**

Use the already-approved policy in `11_GEOMETRY_CONFIDENCE_REFINEMENT_POLICY.md`.

Defaults:
- confidence analysis ON;
- confidence visualization ON;
- confidence-guided refinement OFF.

The OFF path is the release baseline. Confidence cannot silently modify official geometry.

### G7.3 — Free-space evidence / no-fill authority
Status: **PLANNED**

Use `12_FREE_SPACE_VISIBILITY_CARVING_POLICY.md`.

Build:
- FREE votes;
- OCCUPIED votes;
- UNKNOWN;
- CONFLICT.

CONFIRMED_FREE becomes a no-fill/no-bridge constraint. UNKNOWN is never treated as FREE.

This stage may also add the planned Delaunay visibility-aware mesh candidate beside Poisson using the existing Gate 6 dense workspace. Gate 6 itself is not reopened as a blocker.

### G7.4 — Protected fusion candidate
Status: **PLANNED**

Create a fused candidate while preserving:
1. original-source/P9 protected geometry;
2. registered P10 evidence where P9 is unobserved or weak;
3. explicit no-fill constraints from CONFIRMED_FREE;
4. provenance for every accepted region.

No destructive cleanup/remesh belongs here; that remains Gate 8.

### G7.5 — Registration/provenance visual review
Status: **PLANNED**

User-facing Gate 7 preview must show:
- P9 geometry;
- P10 registered geometry;
- source-protected regions;
- P10-generated/multiview-supported regions;
- FREE / UNKNOWN / CONFLICT evidence where available;
- camera/frustum context;
- metric-isotropic views and/or dedicated 3D provenance view.

Expected preview result remains the Master Plan contract:
`P9/P10 registration overlay + geometry provenance`.

### G7.6 — Gate 7 closeout
Status: **PLANNED**

Required before Gate 8:
- P9 unchanged byte-for-byte where the P9 contract requires immutability;
- registration provenance PASS;
- no unauthorized Sim(3)/scale normalization;
- fused candidate exists and is non-empty;
- protected source surfaces remain protected;
- free-space no-fill rules represented;
- provenance manifest complete;
- Gate 7 Preview package published and user-reviewed.

## Parallel-development rule while r15 is under test

Source-only Gate 7 development may continue in the current work branch because it does not modify the already-published r15 runtime bundle.

Until r15 is accepted:
- do not promote Gate 7 into the current user workflows;
- do not publish Gate 7 as an accepted Preview;
- do not overwrite the current P9 or P10 attempt;
- continue GitHub/Drive recovery checkpoints.

If r15 exposes another Route Setup UX/runtime defect, fix DR9R independently and keep the Gate 7 source checkpoint recoverable.

## Current progress

- DR9R r15: user runtime test in progress.
- G7.1 implementation: complete in source.
- G7.1 tests: added.
- Next safe work: G7.2 provenance classifier.
