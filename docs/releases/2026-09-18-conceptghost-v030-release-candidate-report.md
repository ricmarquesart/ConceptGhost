# ConceptGhost v0.30 — Canonical MoGe-3 / High Fidelity Release Candidate Report

**Status:** RELEASE CANDIDATE — NOT FROZEN  
**Target:** `ConceptGhost_v0.30_Canonical_MoGe3_HighFidelity`  
**Date:** 2026-09-18

## Root cause

The exact High Fidelity regression occurred at the handoff from `ConceptGhostMoGeEvidence.build()` to `canonicalize_moge()`.

The MoGe evidence node correctly resolved `High Fidelity`, and real RAW evidence proved that ViT-G ran. But the resolved profile was not written to the top-level evidence object consumed by canonicalization. The downstream canonicalizer then used a dangerous fallback equivalent to:

```python
geometry_profile = evidence.get("geometry_profile") or "Standard"
```

That silently converted the authoritative profile to `Standard`. Several later fallback/default sites allowed the bad state to propagate into SceneBundle / ExportBundle / PrimaryMesh.

Real failing run `20260918T195826_428213Z_67686e0e`:
- RAW: High Fidelity / `Ruicheng/moge-3-vitg` / resolution 9
- PrimaryMesh: Standard / `standard_transport_stride` / stride 3

## Architecture change

v0.30 introduces one authoritative `ConceptGhost.GeometryProfile.v1` contract.

After the user chooses Standard or High Fidelity, the downstream pipeline no longer re-infers the profile from hidden defaults. Missing or contradictory profile metadata is a hard error.

`MASTER → GeometryProfile.v1 → MoGe-3 → MoGe Evidence → Canonical → Profile-specific Mesher → PrimaryMesh → ExportBundle → Maya Worker → MA/FBX/USD → manifests`

DA3 has been removed from the active ConceptGhost graph.

## High Fidelity

- Model: `Ruicheng/moge-3-vitg`
- resolution 9
- SSR7
- mixed precision
- force_projection true
- apply_mask true
- silent fallback false
- mesher `moge_full_resolution_depth_edge_preserving`
- stride 1
- depth_edge_rtol 0.04
- simplification/decimation disabled
- normals from final topology

## Standard reference

- full points: 1,428,291
- vertices: 158,724
- faces: 313,524
- stride 3

## Local validation

- compileall PASS
- pytest: 12 PASS
- workflow graph: 26 nodes / 66 links / 0 dangling
- active workflow/source has no DA3 / DepthAnythingV3 / Semantic/SAM active dependency
- exact forbidden RAW-HF -> final-Standard regression fails closed
- HF -> Standard Maya payload mismatch fails closed

## Real reference scene proof

Same ViT-G RAW from `20260918T195826_428213Z_67686e0e`.

Before v0.29.1:
- PrimaryMesh Standard
- stride 3
- vertices 159,368
- faces 316,244

After v0.30 offline reconstruction from exact same RAW:
- Canonical High Fidelity
- PrimaryMesh High Fidelity
- stride 1
- rtol 0.04
- retained vertices 1,426,735
- faces 2,823,599
- candidate faces 3,139,990
- rejected invalid faces 280,372
- rejected depth-edge faces 36,019
- forbidden-edge triangles accepted 0
- normal gate PASS
- camera-away faces 0
- opposed normals 0

High Fidelity retains about 8.99x as many mesh vertices and 9.01x as many faces as the Standard reference.

## Maya / FBX status

Static profile propagation and worker validation are implemented, but these mandatory real-Windows gates remain pending:
- MAYA_LIVE
- MAYA_REOPEN
- FBX_ROUNDTRIP
- real v0.30 maya_manifest

`VERIFY_HIGH_FIDELITY_OUTPUT.bat` is included to validate these after the first real v0.30 Windows run.

## DA3 retirement / cleanup safety

v0.30 no longer installs or requires DA3.

Historically ConceptGhost-owned DA3 caches measured:
- `C:\ConceptGhost\cache\da3-comfy-env` ~4.07 GB
- `C:\ConceptGhost\cache\pixi` ~4.04 GB

So historical safe-exclusive reclaim is about **8.11 GB**.

Potentially shared candidates:
- ComfyUI-DepthAnythingV3 plugin ~416 MB
- depthanything3 models ~1.53 GB

Drive research contains prior documents explicitly referencing DA3 with Single View, including `E05_B1_DA3_SINGLE_VIEW_CAMERA_VALUE_TRAIN25_SPEC_FREEZE_20260906`. Therefore the v0.30 cleanup deliberately does **not** auto-delete the DA3 plugin/model folder. The machine-specific `AUDIT_DA3_REMOVAL.bat` must be run first.

No cleanup removes ComfyUI Python, Torch, CUDA, NumPy, global Python or shared ComfyUI venv packages.

## Remaining freeze gates

v0.30 stays RC until:
1. real Windows v0.30 High Fidelity run completes;
2. `VERIFY_HIGH_FIDELITY_OUTPUT.bat` reports end-to-end PASS;
3. MAYA_LIVE / MAYA_REOPEN / FBX_ROUNDTRIP pass;
4. remote Windows GitHub Actions / PowerShell 5.1 checks pass.
