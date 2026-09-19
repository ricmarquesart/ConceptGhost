# ConceptGhost v0.33 — Improvements WIP Checkpoint P4

Baseline authority: `frozen/v0.32-complete-20260918`.

Source checkpoint (Drive): `ConceptGhost_v0.33_P4_CHECKPOINT_SOURCE.zip`
SHA-256: `7b65c715cad7043664771d3cdc7db18c421b37fe8fc273feb384ddc67cf2d650`
Drive folder: https://drive.google.com/drive/folders/1-EMTHvsW6c9BWEpSqphrgMh-p72W5lk3

## Status
- [x] P0 — v0.32 frozen baseline
- [x] P1 / A1 — MoGe native metric evidence & measurements
- [x] P2 / A2+A3+A4 — deterministic Atlas ground/distance/height metrology
- [x] P3 / A5 — MoGe × Atlas metric agreement
- [~] P4 / A6 — Maya metric diagnostics + region infrastructure implemented locally; target Maya validation deferred
- [ ] P5 / B1 — Depth Pro independent metric witness
- [ ] P6 / B3 — robust metric consensus
- [ ] P7 / B4 — simplified geometric regions
- [ ] P8 / A7 — local geometry cleanup

## P1
- Immutable semantic native metric points/depth without duplicate storage
- native measurements, normals, intrinsics, mask/support, optional refinement diagnostics
- Atlas-conditioned MoGe intrinsics explicitly marked non-independent
- report-only

## P2
- pixel → Atlas world ray
- ray → ground-plane intersection
- camera/ground distance
- architectural height + closest-approach residual
- optional physical-size plausibility ratio
- ground quality + global → local fallback → INSUFFICIENT_GROUND_MODEL
- report-only

## P3
- target camera-distance agreement
- camera-height agreement
- global scale-factor agreement
- CONSISTENT / MODERATE_DISAGREEMENT / STRONG_CONFLICT / UNAVAILABLE
- automatic_correction=false

## P4
- `ConceptGhost.MayaMetricDiagnosticsSpec.v0.33`
- `CG_METRIC_DIAGNOSTICS`
- ground grid, camera-height markers, base/top locators, distance/height lines
- agreement/conflict metadata
- `CG_REGIONS` selection/metadata infrastructure
- region policy: metadata/selection only; never geometry deletion
- Maya runtime acceptance intentionally deferred

Local regression suite at checkpoint: **95 PASS**.
