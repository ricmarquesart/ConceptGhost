# ConceptGhost P10 — Gate 7.5 Registration / Provenance Visual Review Source Closeout

Date: 2026-09-24  
Status: COMPLETE / CI PASS at source level. The node exists in source, but it is intentionally not promoted into the currently published DR9R r15 workflows while r15 runtime UX acceptance is still being tested.

## Purpose

Gate 7.5 provides the human-review surface required before Gate 7 can close and before Gate 8 is allowed to consume the protected fusion candidate.

The review is explicitly non-promoting:
- it does not make the Gate 7.4 candidate official;
- it does not modify P9;
- it does not modify P10 geometry;
- it does not enable destructive cleanup;
- it does not enable Gate 8.

## New source component

`p10_lab/gate7_visual_review.py`

Primary API:

`build_gate7_visual_review(...)`

The renderer validates the complete Gate 7 chain and produces one four-panel metric review image plus a machine-readable manifest.

## Review panels

The preview contains:

- Perspective diagnostic view;
- Top X/Z;
- Front X/Y;
- Side Z/Y.

The orthographic panels use one common world-units-per-pixel scale so proportions can be compared directly rather than independently auto-fit per panel.

## Required visual layers

The preview draws:

- authoritative P9 geometry;
- `P9_SOURCE_PROTECTED` points;
- accepted P10 Gate 7.4 geometry;
- rejected P10 source-face centroids;
- `CONFIRMED_FREE` evidence;
- free-space `CONFLICT` evidence;
- Gate 6 camera centers and forward/frustum direction context.

The diagnostic palette exists only in the review PNG / ComfyUI preview. It is not written into P9, the candidate mesh materials, or future Maya deliverables.

## Input authority

The renderer consumes:

- `protected_fusion_candidate_manifest.json`;
- `protected_fusion_candidate.ply`;
- `protected_fusion_face_provenance.npz`;
- original P10 Poisson mesh for rejected-face locations;
- `free_space_constraints_manifest.json` + NPZ;
- G7.1 registration;
- Gate 6 known-camera dataset metadata.

Identity mismatches fail closed.

## Review manifest

Output:

- `gate7_registration_provenance_review.png`;
- `gate7_visual_review_manifest.json`.

The manifest records:
- scene / P9 / attempt identity;
- enabled review layers;
- render counts;
- metric-isotropic review contract;
- paths back to the Gate 7.4 and Gate 7.3 evidence;
- `artist_review_status = PENDING`;
- `ready_for_gate8 = false`.

Promotion blockers are explicit:

- `ARTIST_VISUAL_REVIEW_PENDING`;
- `DR9R_R15_RUNTIME_UX_ACCEPTANCE_PENDING`.

## ComfyUI source node

New source node:

`ConceptGhostP10Gate7VisualReview`

Display name:

`P10 · Gate 7 · Registration + Provenance Review`

Outputs:
- review IMAGE tensor;
- preview PNG path;
- visual-review manifest path;
- diagnostics JSON.

When executed inside ComfyUI, the node also attempts to copy the preview into ComfyUI temp storage for direct UI display. The IMAGE tensor remains the authoritative node output.

The node is source-registered now, but it is not inserted into the published r15 Workflow 01/02 package. That isolation preserves the current runtime test boundary.

## Safety contract

- candidate officialized: NO
- official geometry changed: NO
- P9 authority changed: NO
- P9 face deleted: NO
- P9 vertex moved: NO
- rejected P10 hidden from review: NO
- CONFIRMED_FREE hidden from review: NO
- camera context omitted: NO
- Gate 8 enabled: NO
- current r15 bundle modified: NO

## CI

Focused Gate 7.5 visual-review runtime suite:

- `35956022505` — SUCCESS on Ubuntu/Python 3.12 and Windows/Python 3.12.

General regression suite:

- `35956022467` — SUCCESS on Ubuntu/Python 3.12, Windows/Python 3.12 and Windows/Python 3.14.

Source snapshot:

- `35956022506` — SUCCESS.

Focused tests verify:
- four required views are rendered;
- all required review layers are present;
- candidate remains non-official;
- artist review remains PENDING;
- Gate 8 remains blocked;
- officialized candidates are refused;
- the ComfyUI node is discoverable without adding it to a user workflow.

## Next bounded source gate

G7.6 — Gate 7 Closeout.

G7.6 can now validate source-side completeness of G7.1 through G7.5, freeze the Gate 7 evidence contract and prepare a Preview package.

However, final Gate 7 promotion and Gate 8 start must remain blocked until:
1. DR9R r15 route-editor runtime UX acceptance is confirmed by the user;
2. the Gate 7.5 visual-review package is actually published/integrated into a testable workflow;
3. the user reviews the Gate 7 visual result.
