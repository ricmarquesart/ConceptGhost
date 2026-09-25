# Gate 7 R6F12 — P9 Baseline Quality Restore

Date: 2026-09-25 UTC  
Status: SOURCE FIX IMPLEMENTED — PACKAGE CI / TARGET-PC VISUAL ACCEPTANCE PENDING

## Trigger

The first Workflow / Baseline P9 began producing a visibly shredded/noisy PrimaryMesh. The regression is visible before P10, in the Primary Master preview and Maya export. Two fresh runs with the same source and the same High Fidelity profile reproduced the degraded topology:

- `20260925T040418_184791Z_3b562ead`
- `20260925T062251_194350Z_4e165ed6`

The second run used `Baseline / P9`, proving that the defect is upstream of the P10 route/reconstruction stages.

## Controlled run comparison

Both runs report the same core generation contract:

- model: `Ruicheng/moge-3-vitg`
- effective profile: `High Fidelity Split Clean`
- preset label: `Fast Test`
- `resolution_level=9`
- `refine_steps=7`
- `transport_stride=1`
- `depth_edge_rtol=0.04`
- `discontinuity_threshold=0.10`
- `long_triangle_ratio=14`
- `triangle_quality_min=0.04`
- raw valid points: `1,433,612`
- raster candidate faces: `2,859,621`

Therefore the quality collapse is not explained by the artist selecting a lower MoGe model/resolution/refinement profile.

## Confirmed code regression

The frozen v0.36 stable PrimaryMesh builder used one fixed relative-depth rejection rule:

```python
forbidden = (~positive) | (~np.isfinite(max_jump)) | (max_jump >= rtol)
```

with High Fidelity `rtol=0.04`.

Later P9.10 code changed the shared PrimaryMesh builder to tighten this threshold using `geometric_boundary_strength`:

```python
effective_rtol = np.maximum(
    rtol * 0.25,
    rtol * (1.0 - 0.60 * face_boundary),
)
forbidden = ... | (max_jump >= effective_rtol)
```

This allows a nominal 4% depth-jump threshold to be tightened down to 1%. The same adaptive rule was repeated in the final topology proof. P9.10 also added a normal/boundary topology veto.

That change leaked into the shared `Baseline / P9` generator even though the P9 master contract explicitly required the stable v0.36 generation behavior to remain unchanged and required new topology-changing refinement decisions to stay outside the stable branch.

## Measured effect on the failing source

Using the exact current MoGe evidence from the failing source:

- valid raster candidate faces: `2,859,621`
- current adaptive P9 run rejected at the pre-Split-Clean depth-edge gate: `253,870`
- frozen v0.36 fixed `rtol=0.04` rule on the same depth/mask evidence rejects: `191,320`

The leaked adaptive policy therefore removes **62,550 additional faces** before Split Clean, about **32.7% more depth-edge rejection than the frozen stable rule**.

Those removals occur specifically near geometric boundaries, so their visual effect is disproportionate: they split facades, roofs, street edges, distant structures and thin features into disconnected shells. Split Clean then applies its own discontinuity/elongation cleanup on top of that already-cut mesh, producing the observed shredded result.

The failing Baseline run records `2,671` connected components after Split Clean, consistent with over-fragmentation.

## R6F12 repair

R6F12 restores the frozen v0.36 PrimaryMesh topology rule:

- High Fidelity uses the fixed configured `depth_edge_rtol=0.04`;
- `geometric_boundary_strength` remains available as diagnostic/provenance evidence but cannot tighten the baseline PrimaryMesh gate;
- normal/boundary evidence no longer deletes PrimaryMesh faces at this stable baseline gate;
- the independent final topology proof uses the same fixed v0.36 threshold;
- report explicitly records:
  - `p9_boundary_adaptive_depth_threshold=false`
  - `p9_mesh_generation_compatibility=V036_STABLE_FIXED_DEPTH_RTOL`
  - `p9_boundary_evidence_role=DIAGNOSTIC_ONLY_AT_PRIMARYMESH_GATE`.

All later P10 evidence and cleanup stages remain available. This change only restores the stable P9 mesh-generation authority.

## MoGe runtime audit

R6F2-R6F11 changed the private Turing runtime so MoGe-3 can execute on RTX 2080 Ti. That path was audited separately because it was another plausible regression source.

MoGe-3's sparse refiner constructs its voxel coordinates as `torch.int32`; the FlexGEMM neighbor-map path used by that refiner therefore remains on the int32 coordinate path. The current evidence does **not** establish the R6F11 runtime bridge as the cause of this particular mesh fragmentation.

R6F12 therefore does not introduce another runtime change without evidence. It retains the R6F11 runtime that passed the target CUDA/refiner and ViT-G compatibility gates, while fixing the independently proven P9 topology regression.

## Acceptance

Source/CI acceptance requires:

1. no adaptive `effective_rtol` in the PrimaryMesh builder;
2. no normal-boundary deletion at that stable gate;
3. fixed `0.04` policy remains in the High Fidelity contract;
4. R6F11 Atlas-cache and MoGe/Turing compatibility tests remain passing;
5. no P9/P10 authority or quality-profile downgrade.

Target-PC visual acceptance requires rerunning **Workflow 1 / Baseline P9** first and comparing:

- Primary Master Preview;
- Maya PrimaryMesh;
- distant/tower continuity;
- connected-shell fragmentation;
- point/mesh readability before any Workflow 2 processing.

Gate 8 promotion remains blocked until Gate 7 / P9 quality acceptance.
