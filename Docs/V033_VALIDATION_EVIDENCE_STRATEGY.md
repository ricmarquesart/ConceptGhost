# ConceptGhost v0.33 — Validation & Evidence Strategy

Baseline authority: `frozen/v0.32-complete-20260918`.

## Current hold
P7/P8 implementation is paused until the reported `ConceptGhost_Master_v0.32.json` runtime error is diagnosed. The frozen v0.32 branch must not be rewritten; any real baseline defect is fixed in a separate hotfix lineage.

## Why current geometry may look unchanged
P1–P6 are intentionally report-only:
- P1/A1 preserves and exposes MoGe native metric evidence.
- P2/A2+A3+A4 adds deterministic Atlas metrology.
- P3/A5 compares MoGe and Atlas.
- P4/A6 adds Maya diagnostics/region infrastructure.
- P5/B1 adds an independent Depth Pro witness.
- P6/B3 builds robust metric consensus.

These phases must not automatically move the official PrimaryMesh.

Visible mesh improvement is expected only after:
- P7/B4 simplified geometric regions
- P8/A7 local geometry cleanup / local remesh

## Benchmark Gate V0 — Baseline health
- [ ] v0.32 installer PASS
- [ ] v0.32 verifier PASS
- [ ] `ConceptGhost_Master_v0.32.json` opens with no missing/invalid node
- [ ] one High Fidelity run completes without graph/runtime error
- [ ] freeze exact run as benchmark reference

## Benchmark Gate V1 — No-regression parity for report-only improvements
Run v0.32 and v0.33 on the exact same input and configuration.
Require:
- [ ] same source image hash
- [ ] same Atlas camera/FOV/extrinsics
- [ ] same High Fidelity profile/model/settings
- [ ] same PrimaryMesh vertex/face counts
- [ ] same PrimaryMesh positions/topology hash where report-only code does not touch geometry
- [ ] same UV/material/camera linkage
- [ ] same normal-validation results
- [ ] no new forbidden depth bridges
- [ ] v0.33 extra diagnostics do not silently alter official geometry

A report-only phase is considered an improvement when it adds useful, reproducible evidence while preserving the official geometry.

## Benchmark Gate V2 — Controlled metrology truth set
Create controlled scenes/images with known:
- camera height
- focal length/FOV
- object base distance
- object height
- ground plane

Measure:
- Atlas ray-ground distance error
- Atlas architectural height error
- MoGe metric distance error
- Depth Pro metric distance error
- consensus error

For deterministic geometry, mathematical tests are strict. For learned metric models, record absolute/relative error distributions before setting acceptance thresholds.

## Benchmark Gate V3 — Real-image consistency
Use a fixed small suite of real images:
- current frozen ConceptGhost reference image
- near/far architecture scene
- strong depth-discontinuity scene
- foreground/background overlap scene

Record for every version:
- camera/FOV
- PrimaryMesh vertices/faces
- support ratio
- depth-edge rejects
- normal gate
- disconnected shells
- metric source values
- agreement/conflict state
- runtime and peak memory

No version is promoted from a single visually pleasing example.

## Benchmark Gate V4 — P7 region quality
When P7 exists:
- regions must respect mesh connectivity/depth discontinuities
- façade/roof/ground should not be merged across strong boundaries
- region generation must not delete or move official geometry
- region output must be reproducible on the same input

## Benchmark Gate V5 — P8 geometry-improvement proof
When P8 exists, compare against v0.32 and pre-cleanup v0.33:
- [ ] local spike/floating-component count decreases
- [ ] target-region defect metric improves
- [ ] vertices outside approved region remain unchanged
- [ ] protected depth boundaries remain protected
- [ ] no new cross-depth bridges
- [ ] UV/material/camera unchanged
- [ ] normal validation remains PASS
- [ ] Maya/FBX round-trip remains PASS
- [ ] before/after GLBs and diagnostic report saved

## Promotion principle
Every improvement must answer both:
1. What measurable problem became better?
2. What previously working property remained unchanged?

If neither can be shown, the change is not promoted.
