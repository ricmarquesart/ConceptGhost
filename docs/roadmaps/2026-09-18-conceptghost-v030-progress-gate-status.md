# ConceptGhost v0.30 — Progress / Gate Status

**Date:** 2026-09-18
**Target:** `ConceptGhost_v0.30_Canonical_MoGe3_HighFidelity`
**Status:** RELEASE CANDIDATE — not frozen

## Completed
- GATE 0 — v0.29.1 baseline and regression evidence frozen.
- GATE 1 — exact High Fidelity profile-loss point identified.
- GATE 2 — DA3 removed from active workflow/source/packaging.
- GATE 3 — authoritative `ConceptGhost.GeometryProfile.v1` with fail-closed validation.
- GATE 4 — High Fidelity RAW contract: ViT-G / resolution 9 / SSR7 / no silent downgrade.
- GATE 5 — canonicalization keeps authoritative HF state.
- GATE 6 — HF PrimaryMesh uses full-resolution depth-edge-preserving mesher / stride 1 / rtol 0.04.
- Real failing ViT-G RAW reconstructed offline through v0.30: ~1.427M retained vertices, ~2.824M faces, 36,019 depth-edge face rejections, 0 forbidden bridges, normal gate PASS.
- Local compileall PASS.
- Local regressions: 12 PASS.
- Workflow: 26 nodes / 66 links / 0 dangling.
- COMPLETE/SOURCE ZIPs generated and hashed.
- COMPLETE/SOURCE bundles and reference proof uploaded to Drive.
- v0.30 source snapshot committed as three base64 parts for reproducible CI.
- GitHub Actions `v030-canonical.yml` committed for Linux + Windows PowerShell 5.1 validation.

## Pending before freeze
- GATE 7 / HF-N2: real MAYA_LIVE validation.
- GATE 7 / HF-N3: real MAYA_REOPEN validation.
- GATE 7 / HF-N4: real FBX_ROUNDTRIP validation.
- GATE 8: real v0.30 maya/final manifest end-to-end proof.
- GATE 9: run `AUDIT_DA3_REMOVAL.bat` on the actual machine for exact current reclaimable bytes/references.
- GATE 11: remote GitHub Actions result still must be observed.
- GATE 12: one real v0.30 High Fidelity run + `VERIFY_HIGH_FIDELITY_OUTPUT.bat` PASS before definitive freeze.

## DA3 disk space
Historical safe-exclusive ConceptGhost-owned DA3 storage:
- `C:\ConceptGhost\cache\da3-comfy-env`: ~4.07 GB
- `C:\ConceptGhost\cache\pixi`: ~4.04 GB
- historical safe-exclusive reclaim estimate: **~8.11 GB**

Additional historical candidates (~416 MB plugin + ~1.53 GB models) are not auto-deleted because another workflow may reference them.

The cleanup script never removes global/shared Python, Torch, CUDA, NumPy, ComfyUI venv packages, plugin, or model folders automatically.

## Freeze rule
Do not mark v0.30 definitive until a real Windows run proves:

`High Fidelity -> ViT-G -> Canonical HF -> PrimaryMesh HF/stride1/edge-aware -> Maya HF -> FBX HF -> all normal/profile gates PASS`.
