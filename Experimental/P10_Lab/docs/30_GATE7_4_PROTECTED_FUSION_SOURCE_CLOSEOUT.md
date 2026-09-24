# ConceptGhost P10 — Gate 7.4 Protected Fusion Candidate Source Closeout

Date: 2026-09-24  
Status: COMPLETE / CI PASS at source level. User-facing Gate 7 promotion remains blocked until the current DR9R r15 route-editor runtime acceptance is finished.

## Purpose

Gate 7.4 creates the first combined P9 + P10 geometry candidate without granting destructive authority.

The candidate is additive and conservative:
- every authoritative P9 face is copied unchanged;
- no P9 vertex is moved;
- no P9 face is deleted;
- P10 faces are accepted only when their local evidence is independently multiview-supported and confidence-qualified;
- CONFIRMED_FREE is a hard no-fill veto;
- free-space CONFLICT is unresolved and therefore not accepted into the fusion candidate;
- P10 faces overlapping protected P9 source geometry are rejected;
- when Delaunay evidence exists, accepted P10 faces must also agree locally with that visibility-aware structural candidate.

No cleanup/remesh/replacement occurs in this gate. Those operations remain Gate 8 work.

## New source component

`p10_lab/protected_fusion.py`

Primary API:

`build_protected_fusion_candidate(...)`

Inputs:
- authoritative P9 run;
- accepted G7.1 registration;
- G7.3D confidence/free-space overlay;
- G7.3B free-space constraints;
- the registered P10 Poisson pre-fusion mesh;
- optional/automatic G7.3C Delaunay evidence mesh when present.

## P9 authority contract

The candidate retains all P9 geometry:

- `all_p9_faces_copied_unchanged = true`
- `p9_faces_removed = 0`
- `p9_vertices_moved = 0`
- source-protected P9 overlap never admits a competing P10 face.

The original P9 files are never overwritten. The Gate 7.4 PLY is a new derived candidate.

## P10 acceptance contract

A P10 face is admitted only when all applicable checks pass:

1. no sampled face point enters `CONFIRMED_FREE`;
2. no sampled face point enters free-space `CONFLICT`;
3. the face centroid is outside the protected-P9 overlap radius;
4. the face is close enough to G7.2/G7.3 support evidence;
5. nearest provenance is `P10_MULTIVIEW_SUPPORTED`;
6. confidence after free-space coupling is >= 0.40 by default;
7. when a Delaunay candidate exists, the face agrees locally with Delaunay within the structural-support radius.

Face probes include:
- 3 vertices;
- 3 edge midpoints;
- centroid.

This is specifically intended to catch a Poisson bridge whose vertices sit outside a narrow opening but whose edge/centroid crosses a CONFIRMED_FREE cell.

## Per-face provenance

Every P10 input face receives an explicit result code:

- `ACCEPTED_P10_MULTIVIEW`
- `CONFIRMED_FREE_VETO`
- `FREE_SPACE_CONFLICT`
- `P9_SOURCE_PROTECTED_OVERLAP`
- `INSUFFICIENT_PROVENANCE`
- `LOW_CONFIDENCE`
- `SUPPORT_DISTANCE`
- `DELAUNAY_DISAGREEMENT`

Artifact:

`protected_fusion_face_provenance.npz`

This records accepted/rejected source face indices, reason codes, confidence, support distance, protected-P9 distance and Delaunay distance.

## Candidate geometry artifact

`protected_fusion_candidate.ply`

The candidate stores:
- P9 layer = 1;
- accepted P10 layer = 2;
- provenance class;
- confidence metadata on vertices.

The candidate is explicitly:

- `candidate_is_official_geometry = false`
- `candidate_may_be_discarded = true`
- `official_geometry_changed = false`
- `destructive_cleanup_performed = false`
- `ready_for_destructive_fusion = false`

It exists for Gate 7.5 visual review and Gate 7.6 closeout, not as the final mesh.

## Why additive instead of replacing weak P9 immediately

Gate 7 identifies admissible evidence. It does not own destructive cleanup.

Even when a P10 patch is stronger than weak/unobserved P9 continuation, Gate 7.4 preserves the upstream P9 mesh and adds the P10 patch as a separate candidate layer. Gate 8 will later decide whether bounded local replacement/remesh is justified.

This prevents a confidence/provenance mistake from silently destroying the accepted P9 result.

## Delaunay relationship

The smooth Poisson mesh remains the primary P10 pre-fusion surface candidate.

Delaunay remains separate structural evidence.

Policy:
- no automatic global Poisson-vs-Delaunay winner;
- local Delaunay agreement is required for P10 candidate admission when the Delaunay result is available;
- lack of a Delaunay artifact is recorded and does not silently pretend agreement;
- CONFIRMED_FREE remains the stronger hard veto.

## CI

Focused Gate 7.4 runtime suite:

- `35954991624` — SUCCESS on Ubuntu/Python 3.12 and Windows/Python 3.12.

General regression suite:

- `35954991620` — SUCCESS on Ubuntu/Python 3.12, Windows/Python 3.12 and Windows/Python 3.14.

Source snapshot:

- `35954991565` — SUCCESS.

Focused tests verify:
- all P9 faces are retained;
- no P9 movement/removal occurs;
- only one synthetic supported P10 face is admitted;
- source-protected overlap is rejected;
- CONFIRMED_FREE is rejected;
- low-confidence P10 is rejected;
- non-unit registration is rejected;
- the candidate remains non-official and non-destructive.

## Safety status

- P9 authority changed: NO
- P9 file overwritten: NO
- P9 face deleted: NO
- P9 vertex moved: NO
- CONFIRMED_FREE bridged: NO
- free-space CONFLICT auto-resolved: NO
- confidence refinement enabled: NO
- Gate 8 cleanup performed: NO
- Maya output changed: NO
- current DR9R r15 runtime bundle changed: NO

## Next bounded source gate

G7.5 — Registration / Provenance Visual Review.

The preview must show the combined candidate in context without promoting it:
- P9 geometry;
- accepted P10 candidate geometry;
- source-protected P9;
- rejected/conflict/free-space evidence;
- cameras/frustums;
- metric-isotropic inspection.

Gate 7.6 closeout remains blocked until that preview exists and the current DR9R runtime UX acceptance is resolved.
