# ConceptGhost — Post-v0.32 Execution Checklist

Frozen byte authority:
- Drive bundle: ConceptGhost_v0.32_COMPLETE.zip
- SHA-256: c89c542274d924d393dd529750ba3233aa4134a61b45dc2b17f335ec31298f3b
- GitHub freeze branch: frozen/v0.32-complete-20260918

## Status legend
- [x] complete/verified
- [~] active or implemented but awaiting target-machine evidence
- [ ] pending

## Phase F — v0.32 freeze
- [x] Build one self-contained v0.32 COMPLETE bundle
- [x] Include pinned MoGe vendor for clean-machine install
- [x] Remove legacy v0.30/v0.31 release/workflow/cache files from bundle
- [x] Keep one current workflow: ConceptGhost_Master_v0.32.json
- [x] Add bundle manifest and VERIFY_BUNDLE.bat
- [x] 64/64 local release tests PASS
- [x] ZIP CRC PASS
- [x] Per-file bytes/SHA inventory PASS
- [x] Store exactly one COMPLETE ZIP in frozen Google Drive folder
- [x] Freeze GitHub release record with bundle SHA-256 and Drive pointer
- [ ] Fresh final Windows/ComfyUI/Maya acceptance — deliberately deferred until post-freeze improvements are complete

## Parallel Track A — Safe DA3 removal
- [x] DA3 retired from future ConceptGhost architecture
- [x] Add read-only AUDIT_DA3_SAFE.bat
- [x] Discover known and name-matched DA3/DepthAnythingV3 paths
- [x] Classify KEEP / SAFE_TO_DELETE / UNCERTAIN
- [x] Default UNCERTAIN to KEEP
- [x] Protect Python, Torch/PyTorch, CUDA, NumPy/common libraries
- [x] Protect Single View and Multi View/Trellis
- [x] Protect unrelated ComfyUI custom nodes/workflows/models/caches
- [x] Add exact-path fail-closed REMOVE_DA3_SAFE.bat
- [ ] Run AUDIT_DA3_SAFE.bat on target PC
- [ ] Review measured bytes and every UNCERTAIN candidate before deletion
- [ ] Prove any additional DA3 plugin/model directory exclusive before authorizing it
- [ ] Execute safe removal only after review
- [ ] Measure reclaimed disk bytes
- [ ] Verify protected-file hashes unchanged
- [ ] Final protected workflow smoke checks

## Improvement Track B — A1 MoGe Metric Evidence & Measurement Layer
- [~] A1.0 inventory current MoGe worker/native evidence outputs
- [ ] A1.1 preserve immutable points_metric_native before ConceptGhost registration/scaling
- [ ] A1.2 preserve immutable depth_metric_native
- [ ] A1.3 add metric measurement utilities
- [ ] A1.4 expose MoGe native normals as evidence only
- [ ] A1.5 compare MoGe intrinsics/FOV vs Atlas without replacing Atlas
- [ ] A1.6 add valid-mask/support diagnostics
- [ ] A1.7 preserve optional refinement-step diagnostics when available
- [ ] A1 acceptance: no automatic movement of official PrimaryMesh

## Improvement Track C — Deterministic Atlas metrology
- [ ] A2 ray/ground-plane metrology
- [ ] A3 architectural distance/height
- [ ] A3.1 physical-size consistency
- [ ] A4 global/local ground quality and fail-closed fallback

## Improvement Track D — Agreement and artist diagnostics
- [ ] A5 MoGe × Atlas metric agreement
- [ ] A6 Maya metric diagnostics and region metadata

## Improvement Track E — Independent witness / consensus
- [ ] B1 Depth Pro isolated installation spike
- [ ] B3 robust metric consensus (weighted median/MAD/outlier groups; never simple mean)

## Deferred geometry track
- [ ] B4 simplified geometric regions
- [ ] A7 artist-approved local geometry cleanup
- [ ] Re-evaluate frozen external tools only after proven remaining gaps

## Final acceptance after improvements
- [ ] Rebuild one current COMPLETE bundle
- [ ] Verify bundle/hash/clean install contract
- [ ] Fresh Windows/ComfyUI run(s)
- [ ] Fresh Maya 2026 MAYA_LIVE PASS
- [ ] MAYA_REOPEN PASS
- [ ] FBX_ROUNDTRIP PASS
- [ ] CG_FUSED_POINTS present after reopen
- [ ] Camera/FOV/transforms/UV/normals/material linkage unchanged
- [ ] No duplicate COMPLETE run ZIP / USDA / PrimaryTexture / persistent FBM
- [ ] Freeze next proven baseline only after all required runtime gates pass
