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
Status: **IMPLEMENTED / CI PASS**

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
Status: **IMPLEMENTED / CI PASS**

The first implementation is diagnostic-only and does not modify official geometry.

Implemented classes:
- P9_SOURCE_PROTECTED;
- P9_RETAINED;
- P10_MULTIVIEW_SUPPORTED;
- P10_GENERATED_ONLY;
- UNKNOWN;
- CONFLICT.

Implementation:
- consumes the accepted G7.1 identity registration and fails closed on non-identity/Sim(3) registration;
- samples the authoritative P9 PrimaryMesh and preserves explicit source correspondence as protected P9 evidence;
- samples the P10 pre-fusion mesh in the same P9 canonical world;
- parses Gate 6 sparse tracks and maps COLMAP image IDs back to authored drone missions;
- treats support from at least two images in at least two independent authored missions as independent multiview support;
- writes `gate7_provenance.json` plus `gate7_provenance_evidence.npz`;
- records distance/support evidence and class histograms;
- keeps `ready_for_destructive_fusion = false`.

`P10_GENERATED_ONLY` is deliberately a conservative diagnostic candidate: it means the sampled P10 geometry lies outside the P9 conflict band and lacks independent multi-mission sparse support. That label alone never authorizes deletion/replacement.

GitHub Actions run `35946502650` completed SUCCESS across Ubuntu/Python 3.12, Windows/Python 3.12 and Windows/Python 3.14.

### G7.2C — Geometry confidence field
Status: **IMPLEMENTED / CI PASS**

Uses the approved policy in `11_GEOMETRY_CONFIDENCE_REFINEMENT_POLICY.md`.

Implemented defaults:
- confidence analysis ON;
- confidence visualization evidence ON;
- confidence-guided refinement OFF.

The first-pass field consumes G7.2 provenance and writes:
- `geometry_confidence_manifest.json`;
- `gate7_geometry_confidence_evidence.npz`;
- `gate7_geometry_confidence_points.ply` as a temporary diagnostic-only colored point proxy.

Confidence classes follow the frozen thresholds:
- HIGH >= 0.75;
- NEUTRAL >= 0.40;
- LOW >= 0.20;
- VERY_LOW < 0.20.

Source-protected P9 receives the strongest positive prior. Independently supported P10 geometry receives a multiview score from authored-mission support, track support and sparse-point distance. `CONFLICT` receives low confidence but is not deleted. `UNKNOWN` receives no free-space penalty because G7.3 has not yet supplied free-space authority.

A confidence virtual-hole candidate is diagnostic-only and cannot modify topology. The dedicated proxy is explicitly `COMFYUI_DIAGNOSTIC_ONLY_NEVER_MAYA_EXPORT`.

The OFF path remains the release baseline. `ready_for_destructive_fusion` remains false.

GitHub Actions run `35946720027` completed SUCCESS across Ubuntu/Python 3.12, Windows/Python 3.12 and Windows/Python 3.14.

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
- G7.1 implementation: **COMPLETE / CI PASS**.
- G7.2 provenance classifier: **COMPLETE / CI PASS**.
- G7.2C geometry confidence field: **COMPLETE / CI PASS**.
- G7.2/G7.2C remain diagnostic-only; confidence refinement is OFF and destructive fusion is still blocked.
- Next safe work: **G7.3 free-space evidence / no-fill authority**.
- User-facing Gate 7 Preview remains blocked until the current DR9R runtime UX acceptance is finished.
