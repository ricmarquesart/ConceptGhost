# ConceptGhost v0.31.2 — Deduplication + Optional Remesh Branches

Baseline rule: no v0.31.2 change may alter or rewrite the frozen v0.31.1 baseline.

## Status legend
- [x] complete and verified
- [~] in progress / evidence being collected
- [ ] pending

## Gate 0 — Freeze proven v0.31.1
- [x] Freeze GitHub branch: `frozen/v0.31.1-runtime-validated-20260918`
- [x] Freeze source commit: `20d2109de78754c6bd3306e6ad2f2f96cab4cc4a`
- [x] Preserve validated runtime run: `20260919T032045_435115Z_63417285`
- [x] Create Google Drive baseline folder `ConceptGhost_v0.31.1_RUNTIME_VALIDATED_BASELINE_20260918`
- [x] Copy release manifest/report/checksums into baseline
- [x] Copy runtime manifest, Maya manifest, variant report, output index and worker logs into baseline
- [x] Copy versioned workflow into baseline
- [x] Copy critical source files into baseline
- [x] Create isolated work branch: `work/v0.31.2-dedup-remesh`

## Gate 1 — Storage inventory and duplicate classification
- [x] Confirm COMPLETE.zip duplicates the authoritative saved run and costs ~822.6 MB on the validated run
- [x] Confirm the saved run folder remains authoritative; ZIP is only a snapshot/download transport
- [~] Compare `geometry/canonical/pointcloud.usda` vs `maya/ConceptGhost_<scene>_Ghost.usda` by content hash before removing either
- [~] Audit repeated texture copies: source image, PrimaryTexture, Ghost.fbm, GhostFullScene.fbm
- [~] Audit provider/ComfyUI transport copies of HF Master / Split Clean / Simplified outputs
- [ ] Compare Ghost.fbx vs GhostFullScene.fbx by scene content/signature, not size alone
- [ ] Classify every large file as AUTHORITY / REQUIRED INTERCHANGE / PREVIEW / DIAGNOSTIC / DUPLICATE / REGENERABLE

## Gate 2 — Remove unnecessary run ZIP
- [ ] Stop automatic creation of `*_COMPLETE.zip`
- [ ] Remove ZIP from mandatory Stage 13 / download contract
- [ ] Keep small manifests/audit evidence without copying payload files
- [ ] Update output_index/manifest schemas so absence of ZIP is expected
- [ ] Add regression test proving normal run creates no full duplicate archive

## Gate 3 — Deduplicate canonical/USD data
- [ ] If hashes prove the two USDA files identical, retain one authoritative file only
- [ ] Replace duplicate path with reference/manifest pointer instead of physical copy
- [ ] Verify Maya USD proxy still resolves after deduplication
- [ ] Verify .ma reopen remains PASS

## Gate 4 — Deduplicate textures and FBM folders
- [ ] Determine which external texture copy is actually required by Maya/FBX
- [ ] Prefer one run-level authoritative source texture
- [ ] Avoid duplicate FBM texture folders when embedded textures make them unnecessary
- [ ] Preserve compatibility when an external-texture FBX consumer requires a sidecar
- [ ] Regression-test texture linkage in .ma and FBX round-trip

## Gate 5 — Deduplicate ComfyUI transport/preview outputs
- [ ] Keep user-visible downloadable/previewable nodes
- [ ] Avoid copying the same GLB twice solely to expose it in ComfyUI when a reference/transport path can be used safely
- [ ] Verify preview nodes still open the exact generated asset
- [ ] Record output location clearly in UI/report

## Gate 6 — Evaluate duplicate FBX roles
- [ ] Compare legacy Ghost.fbx and GhostFullScene.fbx contents/signatures
- [ ] If functionally redundant after parity validation, designate one official full-scene FBX
- [ ] Retire duplicate only after Maya 2026 round-trip regression passes
- [ ] Preserve CameraOnly.fbx

## Gate 7 — Restore floating-point visualization branch
- [ ] Keep `CG_FUSED_POINTS` in the .ma exactly as v0.31.1
- [ ] Restore a user-facing point-cloud output/preview node
- [ ] Do not create another huge duplicate point-cloud payload solely for the node
- [ ] Use/reference the authoritative canonical point data where possible

## Gate 8 — Optional remesh branch controls
- [ ] Add master switch: `Generate Remesh Variants = OFF/ON`
- [ ] OFF must skip all remesh computation and file generation
- [ ] ON creates three automatic derived profiles: Light / Medium / Strong
- [ ] Each derived output preserves UVs, texture, world coordinates and `CG_ARTIST_CAMERA`
- [ ] Derived remeshes never replace PrimaryMesh or CG_HERO_MESH
- [ ] Primary .ma remains authored from the selected authoritative PrimaryMesh only
- [ ] Use ConceptGhost Remesh naming unless a real external ZBrush ZRemesher integration is implemented
- [ ] Validate Light/Medium/Strong settings empirically on the frozen reference input before locking defaults

## Gate 9 — Output UX
- [ ] Expose Master + optional Light/Medium/Strong as separate downloadable/previewable outputs
- [ ] Clearly label which output is the exact Maya PrimaryMesh
- [ ] Clearly label derived/remeshed outputs
- [ ] Show vertex/face counts for each branch
- [ ] Show whether remesh generation was skipped or executed

## Gate 10 — Size and regression acceptance
- [ ] Measure same reference run before vs after deduplication
- [ ] Target: remove COMPLETE.zip overhead entirely
- [ ] Target: eliminate verified physical duplicates without loss of functionality
- [ ] High Fidelity PrimaryMesh parity remains PASS
- [ ] MAYA_LIVE remains PASS
- [ ] MAYA_REOPEN remains PASS
- [ ] FBX_ROUNDTRIP remains PASS
- [ ] CG_FUSED_POINTS remains present in .ma
- [ ] Camera/FOV/transforms/UV/normals/material linkage remain unchanged
- [ ] Compare final v0.31.2 against frozen v0.31.1 before promotion

## Promotion rule
v0.31.2 may become the new baseline only after all required regression gates pass against the same reference input. Until then, v0.31.1 frozen branch + Drive baseline remain the rollback authority.
