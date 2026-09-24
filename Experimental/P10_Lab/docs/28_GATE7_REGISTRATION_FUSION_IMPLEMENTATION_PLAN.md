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
Status: **IMPLEMENTED / CI PASS**

Implemented from the existing Gate 6 dense workspace without reopening Gate 6 as a blocker.

Substages:
- **G7.3A** COLMAP dense depth/consistency evidence reader + sparse ray visibility field;
- **G7.3B** conservative `OCCUPIED / CONFIRMED_FREE / UNKNOWN / CONFLICT` classifier;
- **G7.3C** separate Delaunay visibility-aware mesh evidence beside the existing Poisson candidate;
- **G7.3D** confidence/free-space diagnostic overlay.

Key authority rules:
- `CONFIRMED_FREE` = future `NO_FILL / NO_BRIDGE`;
- `UNKNOWN` is never interpreted as FREE;
- `CONFLICT` remains unresolved/diagnostic;
- protected P9 source evidence is forced OCCUPIED and cannot be carved by generated views;
- geometry remains unchanged and destructive fusion remains disabled.

Focused CI run `35953822402` passed on Ubuntu/Python 3.12 and Windows/Python 3.12. General regression run `35953822364` also passed. Formal source closeout: `29_GATE7_3_FREE_SPACE_SOURCE_CLOSEOUT.md`.

### G7.4 — Protected fusion candidate
Status: **IMPLEMENTED / CI PASS**

Implemented as a new non-destructive additive candidate.

Rules:
1. every P9 face is copied unchanged;
2. P9 vertices are never moved;
3. P10 faces are admitted only when provenance is `P10_MULTIVIEW_SUPPORTED`, confidence is sufficient, support distance is bounded, protected P9 is not overlapped, and no face probe crosses `CONFIRMED_FREE` or free-space `CONFLICT`;
4. when a Delaunay visibility mesh exists, admitted P10 faces must also agree locally with that structural candidate;
5. every P10 face receives an explicit accept/reject reason code and retained provenance;
6. the output is a derived candidate only, never official geometry.

Artifacts:
- `protected_fusion_candidate.ply`;
- `protected_fusion_face_provenance.npz`;
- `protected_fusion_candidate_manifest.json`.

No destructive cleanup/remesh occurs here; that remains Gate 8.

Focused CI run `35954991624` passed on Ubuntu/Python 3.12 and Windows/Python 3.12. General regression run `35954991620` passed across Ubuntu/Python 3.12, Windows/Python 3.12 and Windows/Python 3.14. Formal closeout: `30_GATE7_4_PROTECTED_FUSION_SOURCE_CLOSEOUT.md`.

### G7.5 — Registration/provenance visual review
Status: **IMPLEMENTED / CI PASS AT SOURCE LEVEL**

Implemented as a non-promoting four-view diagnostic review:

- Perspective;
- Top X/Z;
- Front X/Y;
- Side Z/Y.

The orthographic panels share one metric world-units-per-pixel scale.

Visible layers:
- authoritative P9 geometry;
- `P9_SOURCE_PROTECTED`;
- accepted P10 Gate 7.4 geometry;
- rejected P10 source-face locations;
- `CONFIRMED_FREE`;
- free-space `CONFLICT`;
- Gate 6 camera centers / forward context.

Artifacts:
- `gate7_registration_provenance_review.png`;
- `gate7_visual_review_manifest.json`.

A source ComfyUI node is registered as:
`P10 · Gate 7 · Registration + Provenance Review`.

It remains intentionally absent from the published r15 workflows while r15 runtime UX acceptance is still active. The manifest keeps `artist_review_status = PENDING` and `ready_for_gate8 = false`.

Focused CI run `35956022505` passed on Ubuntu/Python 3.12 and Windows/Python 3.12. General regression run `35956022467` passed across Ubuntu/Python 3.12, Windows/Python 3.12 and Windows/Python 3.14. Formal closeout: `31_GATE7_5_VISUAL_REVIEW_SOURCE_CLOSEOUT.md`.

### G7.6 — Gate 7 closeout
Status: **SOURCE COMPLETE / CI PASS / RUNTIME PROMOTION BLOCKED**

Implemented after the project-wide Visual Evidence & Comparison Contract was frozen.

Source closeout now validates:
- G7.1 identity registration;
- G7.2 provenance;
- G7.2C confidence with refinement OFF;
- G7.3 free-space no-fill authority;
- G7.4 protected additive fusion;
- G7.5 visual review;
- one terminal preview + one comparison branch for every Gate 7 subgate.

G7.6 itself produces a visual-evidence contact sheet and an input/output summary when run against real Gate 7 artifacts.

Source implementation:
- `p10_lab/gate7_closeout.py`
- `p10_lab/visual_evidence_contract.py`
- `p10_lab/visual_comparisons.py`

Focused visual-evidence CI `35958717367`: SUCCESS on Ubuntu/Python 3.12 and Windows/Python 3.12.

Focused G7.6 CI `35958902099`: SUCCESS on Ubuntu/Python 3.12 and Windows/Python 3.12.

Formal closeout:
`33_GATE7_6_SOURCE_CLOSEOUT_VISUAL_EVIDENCE.md`

Required before Gate 8 runtime promotion still remains:
- DR9R r15 runtime UX accepted by the user;
- Gate 7 Preview packaged and run on the real attempt;
- artist visual review approved;
- complete runtime visual-evidence manifests present.

CI/source completion alone never promotes Gate 8.

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
- G7.3 free-space / visibility no-fill authority: **COMPLETE / CI PASS**.
- G7.4 protected additive fusion candidate: **COMPLETE / CI PASS**.
- G7.5 registration/provenance visual review: **COMPLETE / CI PASS AT SOURCE LEVEL**.
- Visual Evidence & Comparison Contract: **COMPLETE / CI PASS**.
- G7.6 source closeout: **COMPLETE / CI PASS**.
- Gate 7 source implementation is now complete and remains non-destructive; confidence refinement is OFF.
- Next safe work after DR9R r15 acceptance: **build/publish the Gate 7 Preview package and run the real visual review**.
- Gate 8 remains blocked until DR9R r15 UX acceptance and artist review of the real Gate 7 Preview are completed.
