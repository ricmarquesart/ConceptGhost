# ConceptGhost P10 — Gate 7.3 Free-Space / No-Fill Source Closeout

Date: 2026-09-24  
Status: COMPLETE / CI PASS at source level. User-facing Gate 7 promotion remains blocked until the current DR9R route-editor runtime acceptance is finished.

## Purpose

Gate 7.3 distinguishes observed empty volume from unknown/disoccluded volume before any protected fusion can bridge, fill, delete, or replace geometry.

The central rule is now explicit:

`CONFIRMED_FREE != UNKNOWN`

- `CONFIRMED_FREE` becomes a later `NO_FILL / NO_BRIDGE` constraint.
- `UNKNOWN` never means free space and never means an automatic hole to fill.
- `CONFLICT` is diagnostic evidence and cannot trigger automatic deletion/fill.
- P9 source-protected evidence has the highest authority and is forced OCCUPIED.

## Implemented source components

### G7.3A — COLMAP dense evidence + sparse visibility field

New modules:

- `p10_lab/colmap_dense_io.py`
- `p10_lab/free_space_evidence.py`

The dense reader implements COLMAP's documented mixed text/binary formats:

- depth/normal header: `width&height&channels&` + little-endian float32 payload;
- consistency graph records: `<row><col><N><image_idx...>`;
- image indices are validated against the dense `images.txt` ordering.

The evidence builder:

1. validates G7.2C identity and P9 authority;
2. loads the existing Gate 6 dense workspace;
3. validates PINHOLE calibration and exact depth-map dimensions;
4. accepts only geometrically-consistent depth samples;
5. converts COLMAP depth endpoints back to the canonical P9 world;
6. marks camera-to-surface-minus-margin samples as FREE evidence;
7. marks the first supported depth endpoint as OCCUPIED evidence;
8. never marks space behind the first surface as FREE;
9. caps repeated same-route contributions;
10. preserves source-protected P9 voxels as highest-authority occupied evidence.

Artifacts:

- `free_space_raw_evidence.npz`
- `free_space_evidence_manifest.json`

## G7.3B — Conservative state classifier

New module:

- `p10_lab/free_space_constraints.py`

States:

- `OCCUPIED`
- `CONFIRMED_FREE`
- `UNKNOWN`
- `CONFLICT`

Default CONFIRMED_FREE policy:

- >= 3 effective supporting views;
- >= 2 independent authored routes;
- >= 5 degrees cross-route angular diversity;
- free/(free+occupied) ratio >= 0.80;
- no protected P9 source contradiction.

Repeated frames from one route are capped before effective-vote counting.

Artifacts:

- `free_space_constraints.npz`
- `free_space_constraints_manifest.json`
- `free_space_preview_points.ply`

The preview PLY is diagnostic-only and must never be exported to Maya.

## G7.3C — Delaunay visibility-aware structural candidate

`p10_lab/prefusion_mesh.py` now contains a separate Delaunay evidence branch.

COLMAP is invoked against the existing dense workspace:

`colmap delaunay_mesher --input_path <dense> --output_path <dense>/pre_fusion_mesh_delaunay.ply`

The current Poisson result is retained separately. No automatic winner is selected.

Artifacts:

- `dense/pre_fusion_mesh.ply` — existing Poisson candidate;
- `dense/pre_fusion_mesh_delaunay.ply` — visibility-aware structural evidence;
- `dense/free_space_meshing_comparison.json`;
- separate lightweight mesh previews.

Policy remains:

`POISSON + DELAUNAY`, not `POISSON vs DELAUNAY`.

## G7.3D — Confidence/free-space coupling

New module:

- `p10_lab/free_space_confidence.py`

The G7.3 state field is overlaid back onto G7.2C confidence diagnostics without changing official geometry:

- `CONFIRMED_FREE` caps P10 confidence at 0.05;
- `CONFLICT` caps P10 confidence at 0.18;
- `UNKNOWN` receives no penalty;
- `OCCUPIED` receives no automatic boost;
- P9 confidence remains unchanged;
- `geometry_confidence_refine` remains OFF.

Artifact:

- `gate7_confidence_free_space_overlay.npz`
- `confidence_free_space_overlay_manifest.json`

## Safety / authority status

- P9 authority changed: NO
- official geometry changed: NO
- destructive fusion enabled: NO
- Sim(3) alignment introduced: NO
- UNKNOWN interpreted as FREE: NO
- protected source geometry carve allowed: NO
- Maya output changed: NO
- current DR9R r15 runtime bundle changed: NO

## CI

General regression suite:

- ConceptGhost Tests run `35953822364`: SUCCESS.

Focused runtime-format/free-space suite with NumPy:

- Gate 7.3 Free-Space Tests run `35953822402`: SUCCESS on Ubuntu/Python 3.12 and Windows/Python 3.12.

Source snapshot:

- P10 DR9 Source Snapshot run `35953822367`: SUCCESS.

Focused tests cover:

- COLMAP depth-map parsing;
- COLMAP consistency-graph parsing;
- free-space ray evidence;
- CONFIRMED_FREE / CONFLICT / UNKNOWN / OCCUPIED classification;
- P9 source protection;
- confidence overlay behavior;
- Delaunay plan isolation from Poisson;
- source contracts that prohibit destructive fusion.

## External technical references

Implementation was checked against the official COLMAP documentation:

- Dense output format: https://colmap.github.io/format.html
- CLI dense reconstruction / Delaunay mesher: https://colmap.github.io/cli.html

## Next bounded source gate

G7.4 — Protected Fusion Candidate.

G7.4 may consume:

- G7.1 identity registration;
- G7.2 provenance;
- G7.2C confidence;
- G7.3 CONFIRMED_FREE/UNKNOWN/CONFLICT constraints;
- Poisson smooth candidate;
- Delaunay structural evidence.

It must still preserve P9 source-protected surfaces and may not perform Gate 8 cleanup/remesh work.
