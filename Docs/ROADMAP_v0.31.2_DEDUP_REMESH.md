# ConceptGhost v0.31.2 — Deduplication + Optional Remesh Branches

Baseline rule: no v0.31.2 change may alter or rewrite the frozen v0.31.1 baseline.

**Current execution status (2026-09-18 PT):** Gate 0 COMPLETE · Gate 1 COMPLETE · Gate 2 COMPLETE · Gates 3/4/5/6 IMPLEMENTED LOCALLY and awaiting Windows/Maya runtime validation where noted · Gate 7 COMPLETE LOCAL · Gate 8 COMPLETE LOCAL on the frozen real PrimaryMesh · Gate 9 COMPLETE LOCAL · Gate 10 RUNTIME-READY RC6 (RC5 installer vendor-archive regression fixed; fresh Windows/ComfyUI/Maya v0.31.2 OFF + ON runs required) · Gate 11 TOOLING COMPLETE LOCAL / target-machine audit still pending.

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
- [x] Compare `geometry/canonical/pointcloud.usda` vs `maya/ConceptGhost_<scene>_Ghost.usda`: identical SHA-256 confirmed on reference run
- [x] Audit repeated texture copies: source/PrimaryTexture are byte-identical; .fbm extraction/manual copies classified as duplicate sidecars when embedded textures are present
- [x] Audit ComfyUI transport copies: PLY and HF GLB preview transports identified as duplicate payload candidates; hard-link-first policy implemented locally
- [x] Compare Ghost.fbx vs GhostFullScene.fbx by role/signature: v0.31.1 exports the same curated scene twice; binary bytes differ only as separate FBX exports/metadata
- [x] Classify large artifacts and record evidence in `DEDUP_AUDIT_v0.31.2_WIP.md` (Drive WIP)

## Gate 2 — Remove unnecessary run ZIP
- [x] Stop automatic creation of `*_COMPLETE.zip` in v0.31.2 workflow
- [x] Remove final ZIP node from v0.31.2 graph; Stage 13 remains small manifest/acceptance evidence only
- [x] Keep small manifests/audit evidence without copying payload files
- [x] Update WIP release/output behavior so absence of ZIP is expected; legacy package call becomes `ARCHIVE_DISABLED` compatibility shim
- [x] Add regression test proving normal v0.31.2 workflow creates no full duplicate archive

## Gate 3 — Deduplicate canonical/USD data
- [x] Identical USDA SHA-256 proven; v0.31.2 local patch retains only canonical `geometry/canonical/pointcloud.usda`
- [x] Maya worker input now points directly to the run-local canonical USDA; no second physical USDA is written
- [ ] Verify Maya USD proxy still resolves after deduplication
- [ ] Verify .ma reopen remains PASS

## Gate 4 — Deduplicate textures and FBM folders
- [x] Reference run proves source PNG and PrimaryTexture PNG identical; v0.31.2 local patch reuses `source/source.png` as hero material texture
- [x] Prefer one run-level authoritative source texture; helper retains compatibility fallback only for direct callers
- [x] Local patch removes transient `.fbm` extraction after embedded-texture FBX round-trip validation
- [ ] Preserve compatibility when an external-texture FBX consumer requires a sidecar
- [ ] Regression-test texture linkage in .ma and FBX round-trip

## Gate 5 — Deduplicate ComfyUI transport/preview outputs
- [x] Preserve user-visible preview outputs while changing transport storage policy
- [x] PLY/HF GLB ComfyUI transport now prefers same-volume hard links; verified copy fallback remains for cross-volume filesystems
- [ ] Verify preview nodes still open the exact generated asset
- [ ] Record output location clearly in UI/report

## Gate 6 — Evaluate duplicate FBX roles
- [x] Compare legacy Ghost.fbx and GhostFullScene.fbx roles/signatures
- [x] Local v0.31.2 design designates `Ghost.fbx` as the single exported full-scene FBX; `GhostFullScene.fbx` is compatibility alias
- [ ] Retire duplicate only after Maya 2026 round-trip regression passes
- [x] Preserve CameraOnly.fbx as distinct diagnostic/interchange artifact

## Gate 7 — Restore floating-point visualization branch
- [x] Keep `CG_FUSED_POINTS` in the .ma exactly as validated in v0.31.1 baseline
- [x] Restore a user-facing point-cloud output/preview node (`ConceptGhostPointCloudPreview`)
- [x] Do not create another huge duplicate point-cloud payload solely for the node; consume existing `preview_ply` transport
- [x] Use/reference the authoritative canonical point data via the ExportBundle canonical PLY/preview transport

## Gate 8 — Optional remesh branch controls
- [x] Add master switch: `Generate Remesh Variants = OFF/ON` (default OFF)
- [x] OFF skips all Light/Medium/Strong remesh computation and file generation
- [x] ON creates three automatic derived profiles: Light / Medium / Strong
- [x] Each derived output preserves UVs, embedded source texture, world coordinates and `CG_ARTIST_CAMERA`
- [x] Derived remeshes never replace PrimaryMesh or CG_HERO_MESH
- [x] Primary .ma remains authored from the selected authoritative PrimaryMesh only
- [x] Use ConceptGhost Remesh naming; implementation remains deterministic ConceptGhost screen-space remesh, not Pixologic ZRemesher
- [x] Validate presets on frozen run `20260919T032045_435115Z_63417285`: Light 354,777v/684,730f; Medium 157,415v/300,267f; Strong 88,294v/166,803f

## Gate 9 — Output UX
- [x] Expose Master + optional Light/Medium/Strong as four separate downloadable/previewable output nodes
- [x] Clearly label Master as exact Maya PrimaryMesh authority
- [x] Clearly label Light / Medium / Strong as optional derived outputs
- [x] Show vertex/face counts for Master and each generated remesh branch in exporter UI/report
- [x] Show whether remesh generation was skipped (OFF) or executed (ON)

## Gate 10 — Size and regression acceptance

**Next active gate:** fresh v0.31.2 Windows/ComfyUI/Maya execution using `ConceptGhost_Master_v0.31.2_DEDUP_REMESH.json`. Local suite currently: **57 PASS**. RC3 WIP source SHA-256: `e64a1d08557869cb9ae433891f6620a9b32e129978aa1876ef8d16205fe96776`. Latest RC4 WIP after safe-DA3 tooling: SHA-256 `e15644ac63048e64ae4d4c6f0320ae38094f35e99a924f2635989e1dac4aea60`. Runtime-ready RC5: SHA-256 `9d7dc41e4a8bcc58b664943dac7edf9c5d9ccdbcfe546d56639a7934c7e2b670` (superseded due to vendor-archive installer regression). Runtime-ready RC6: SHA-256 `946d520fd4ca804494d707372e1ef5e0fa2a7a4bdbbf5f76cc87c6425468d511`; local suite **65 PASS**.
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


### Gate 10 RC5 installer regression / RC6 fix
- [x] RC5 target-machine install exposed a real packaging regression: `Tools\\MoGeRuntime\\vendor\\MoGe-main.zip` was absent while the runtime installer required it unconditionally
- [x] Confirm failure occurred before workflow/runtime acceptance; no Gate 10 result was falsely accepted
- [x] Confirm RC5 did not delete the isolated runtime contents; it only removed stale `READY.json` before failing
- [x] RC6 no longer deletes `READY.json` before deciding between full repair and runtime reuse
- [x] RC6 reuses the existing ConceptGhost-owned `%LOCALAPPDATA%\\ConceptGhost-MoGeRuntime-v1` when the vendor ZIP is absent
- [x] RC6 refreshes only ConceptGhost-owned worker scripts, validates cached ViT-L + ViT-G evidence, runs an actual CUDA smoke inference, and recreates `READY.json`
- [x] Clean-machine installs still fail closed if neither the pinned vendor ZIP nor a reusable private runtime exists
- [x] Local suite after fix: **65 PASS**
- [ ] Execute RC6 installer on target machine and confirm reuse path PASS

### Gate 10 RC5 runtime procedure
- [x] Add dedicated `PREPARE_V0312_RUNTIME_VALIDATION.bat`
- [x] Add dedicated `VERIFY_V0312_RUNTIME_OUTPUT.bat`
- [x] Legacy `PREPARE_GATE8_VALIDATION.bat` redirects to v0.31.2 procedure
- [x] Legacy `VERIFY_HIGH_FIDELITY_OUTPUT.bat` redirects to full v0.31.2 runtime acceptance
- [x] Runtime verifier rejects COMPLETE.zip, duplicate Maya USDA, duplicate PrimaryTexture PNG and persistent .fbm folders
- [x] Runtime verifier requires exact FBX alias payload and the requested Remesh OFF/ON state
- [x] Maya worker records and requires `CG_FUSED_POINTS` after reopening the saved .ma
- [ ] Execute Run A on target machine: Remesh OFF
- [ ] Execute Run B on target machine: Remesh ON
- [ ] Both target-machine runtime verifiers PASS

## Gate 11 — Safe DA3 computer cleanup
- [~] Measure total DA3 disk usage before deleting anything — v0.31.2 measure-only auditor ready; target-machine execution pending
- [x] Auditor inventories known DA3-attributable paths with bytes, file counts, owner role and classification
- [x] Separate DA3-exclusive assets from shared/uncertain runtimes, caches, models and workflows
- [x] Build explicit KEEP / SAFE_TO_DELETE / UNCERTAIN classification before deletion; UNCERTAIN defaults to KEEP
- [~] Remover is hard-fenced to exact proven DA3-exclusive paths; actual deletion not executed yet
- [x] Removal safety policy explicitly blocks shared Python/environments
- [x] Removal safety policy explicitly blocks Torch/PyTorch
- [x] Removal safety policy explicitly blocks CUDA/GPU libraries
- [x] Removal safety policy explicitly blocks NumPy/common dependencies
- [x] Single View references are protected; audit records hashes and cleanup verifies they do not change
- [x] Multi View/Trellis references are protected; audit records hashes and cleanup verifies they do not change
- [x] Broad Pixi cache, DA3 plugin/models and unrelated ComfyUI assets are not auto-approved for deletion
- [x] Preserve anything whose ownership cannot be proven; UNCERTAIN defaults to KEEP
- [~] Cleanup result report records reclaimed bytes; target-machine cleanup not executed yet
- [~] Cleanup invokes ConceptGhost verifier and verifies protected workflow hashes; actual target-machine smoke execution remains pending
- [x] Tooling writes `ConceptGhost.DA3SafeCleanupResult.v0.31.2` with audit source, removed paths, reclaimed bytes and protected hash verification

### Gate 11 non-interference objective
Delete only what is safely attributable to DA3. This gate must not break Python, Torch, CUDA, NumPy, Single View, Multi View/Trellis, other workflows, or other projects.

## Long-term roadmap imported from 2026-09-18 decisions document
Planning source: `Docs/2026-09-18-conceptghost-future-improvements-decisions-and-priority.md`.

These items are tracked here, but they are **not v0.31.2 promotion blockers** unless a later decision explicitly moves them into the active release scope.

### Architectural decisions
- [x] MoGe-3 designated official future geometry engine
- [x] Atlas retained as camera authority
- [x] DA3 Structural Witness (A8) removed from future architecture
- [x] MoGe native metric output designated first-class future evidence
- [x] Initial metric system constrained to REPORT ONLY / no automatic mesh movement
- [x] New external models must justify maintenance/runtime cost

### Phase 1 — A1 · MoGe Metric Evidence & Measurement Layer — APPROVED / Priority 1
- [ ] Preserve immutable `points_metric_native`
- [ ] Preserve immutable `depth_metric_native`
- [ ] Add MoGe measurement utilities: selected-point distance, camera-to-point, structure distance, approximate width/vertical extent, regional depth median/spread
- [ ] Preserve/use MoGe native normals as evidence while final mesh normals remain derived from final topology
- [ ] Compare MoGe intrinsics/FOV against Atlas with CONSISTENT / MODERATE_DISAGREEMENT / STRONG_CONFLICT states
- [ ] Add valid-mask/support diagnostics
- [ ] Preserve optional refinement-step diagnostics where available

### Phase 2 — A2/A3/A4 · Deterministic Atlas Metrology — APPROVED
- [ ] A2: pixel → Atlas ray → ground-plane intersection → world XYZ → camera/ground distance
- [ ] A3: architectural base distance and height estimation with closest-approach residual/confidence
- [ ] A3.1: physical-size consistency diagnostics
- [ ] A4: global ground-plane quality metrics
- [ ] A4: local-ground fallback when global ground quality fails
- [ ] Return INSUFFICIENT_GROUND_MODEL rather than fabricate measurements

### Phase 3 — A5 · MoGe × Atlas Metric Agreement — APPROVED
- [ ] Compare Atlas/geometric metrology with MoGe native metric geometry
- [ ] Add global scale agreement
- [ ] Add regional depth agreement
- [ ] Add camera-height agreement
- [ ] Add conflict reports for representative near/far/foreground regions

### Phase 4 — A6 · Maya Metric Diagnostics & Region Layer — APPROVED
- [ ] Add `CG_METRIC_DIAGNOSTICS`
- [ ] Add camera-height marker and ground-plane grid
- [ ] Add target base/top locators
- [ ] Add distance/height lines and metric labels
- [ ] Add agreement/conflict metadata
- [ ] Add Maya selection sets / region layer such as CG_GROUND, CG_FACADE_01, CG_ROOF_01, CG_TOWER_01
- [ ] Preserve rule: region = metadata/selection; region != geometry deletion

### Phase 5 — B1 · Depth Pro independent metric witness — APPROVED CANDIDATE
- [ ] Run isolated installation/runtime spike
- [ ] Validate GPU/runtime compatibility
- [ ] Validate known focal input where applicable
- [ ] Validate reproducible metric depth on the same source image
- [ ] Keep Depth Pro report/comparison-only initially; it must not become geometry authority

### Phase 6 — B3 · Metric Consensus Engine — APPROVED
- [ ] Combine MoGe native metric + Atlas deterministic metrology + Depth Pro
- [ ] Use weighted median / MAD / robust spread / agreement groups / outlier rejection
- [ ] Classify each observation VALID / WEAK / OUTLIER / UNAVAILABLE
- [ ] Keep initial consensus mode REPORT ONLY
- [ ] Explicitly forbid simple arithmetic-mean consensus

### Phase 7 — B4 · Simplified Geometric Regions / Graph Superpoints — DEFERRED
- [ ] Segment existing official geometry using normals, depth discontinuity, connectivity, planarity, curvature, spatial proximity and connected components
- [ ] Use validated region boundaries to prevent cross-region smoothing/bridging
- [ ] Do not create a competing geometry solver or competing official mesh

### Phase 8 — A7 · Local Geometry Cleanup / Region Operations — APPROVED CONCEPTUALLY, DEFERRED
- [ ] Isolated floating-component detection
- [ ] Spike/outlier detection
- [ ] Local plane fitting
- [ ] Local smoothing
- [ ] Small-hole diagnostics
- [ ] Local remeshing / adaptive local mesh density
- [ ] Boundary-protected triangulation
- [ ] Initial mode remains DIAGNOSTIC / ARTIST-APPROVED, not automatic destructive editing

### Phase 9 — Re-evaluate frozen tools only if a proven gap remains
- [ ] B2 Metric3D v2 — FROZEN
- [ ] C1 Point-SAM — FROZEN
- [ ] C2 EZ-SP / Superpoint Transformer full stack — FROZEN
- [ ] C3 UniDepth V2 — FROZEN
- [ ] C4 Mask3D — FROZEN
- [ ] C5 Mosaic3D — FROZEN
- [x] C6 Full SIHE software stack — DO NOT INTEGRATE AS FULL DEPENDENCY; reuse metrology principles only
- [ ] C7 SAM3D / OpenMask3D / Open3DIS-style 2D-first systems — FROZEN for current Single View path; reconsider only for a true Multi View branch

### Long-term ordering rule
- [ ] Complete MoGe evidence extraction before adding another external solver
- [ ] Complete deterministic Atlas metrology before metric consensus
- [ ] Add one independent learned metric witness (Depth Pro) before considering additional metric models
- [ ] Establish robust metric consensus before heavier 3D segmentation systems
- [ ] Keep automatic mesh movement disabled until multi-scene evidence justifies it

## Promotion rule
v0.31.2 may become the new baseline only after all required regression gates pass against the same reference input. Until then, v0.31.1 frozen branch + Drive baseline remain the rollback authority.
