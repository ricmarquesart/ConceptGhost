# ConceptGhost v0.33 — Improvements Checkpoint P8

Baseline authority remains `frozen/v0.32-complete-20260918`.

Drive checkpoint:
- `ConceptGhost_v0.33_P8_CHECKPOINT_SOURCE.zip`
- SHA-256: `e38747acea8e9af350367a95da75214f7e0d9fc9fde7d88525fec383945f115a`
- Drive folder: https://drive.google.com/drive/folders/1-EMTHvsW6c9BWEpSqphrgMh-p72W5lk3

Local regression suite: **125 PASS**.

## Progress
- [x] P0 — v0.32 frozen baseline
- [x] P1/A1 — MoGe native metric evidence/measurement layer
- [x] P2/A2+A3+A4 — deterministic Atlas metrology
- [x] P3/A5 — MoGe × Atlas metric agreement
- [~] P4/A6 — Maya diagnostics implementation complete; target Maya execution deferred
- [x] P5/B1 — Depth Pro isolated optional witness contract; target GPU execution deferred
- [x] P6/B3 — robust metric consensus
- [x] P7/B4 — simplified geometric regions, metadata-only
- [~] P8/A7 — conservative local cleanup foundation; adaptive remesh/small-hole work intentionally deferred pending region benchmark

## P7 real frozen-reference proof
Reference PrimaryMesh:
- vertices: 1,426,735
- faces: 2,823,599
- runtime: ~10.5 s
- peak RSS: ~940 MB
- raw graph regions: 450
- retained regions: 96
- face coverage: 96.65%
- PrimaryMesh mutation: none

## P8 real frozen-reference proof
Diagnostic candidate:
- flagged review regions: 51
- severe removable faces after boundary protection: 1 / 2,823,599
- automatic official mesh edit: none

Artist-approved derived planar candidate:
- selected planar regions: 1
- moved vertices: 14,705
- mean displacement: ~0.0124 m
- max displacement: 0.0200 m hard cap
- local plane RMS: 0.0750 m -> 0.0625 m (~16.7% reduction)
- vertices moved outside approved region: 0
- strong boundary vertices moved: 0 by contract
- cross-region vertices moved: 0 by contract
- PrimaryMesh replacement: false

## Deliberately not promoted yet
- exact floating shell/component deletion
- small-hole filling
- adaptive local remesh
- automatic destructive cleanup
- automatic metric-based PrimaryMesh movement

Those remain gated until fixed-suite benchmarking demonstrates a measurable benefit without regression.


## Small-hole diagnostics real proof
- boundary edges: 30,965
- closed loops: 218
- small closed loops (<=64 edges): 202
- artist-review candidates after image/depth/region protection: 3
- automatic fill: false
- P8 diagnostic runtime: ~4.0 s
- combined P7+P8 wall time: ~14 s
- peak RSS: ~993 MB

## Adaptive local remesh decision
Status: `DEFERRED_BY_BENCHMARK`.

Reason: safe promotion requires boundary-constrained triangulation or equivalent crack-free stitching, exact boundary preservation, no cross-depth/cross-region bridges, UV/material continuity, fixed-suite improvement evidence, and Maya/FBX round-trip. v0.33 does not ship an unproven local remesher.
