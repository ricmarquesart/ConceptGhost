# P10-Lab Subgate Board

This board decomposes every P10 development gate into bounded, checkpointable
subgates. Each progress update must report the current Gate/Subgate as X/Y,
completed subgates, remaining subgates and the next dependency.

The user explicitly authorized safe work on the next gate while a previous
runtime preview is awaiting their test. This does **not** allow the previous gate
to be marked complete, nor does it allow a dependent promotion/integration step
to bypass missing runtime evidence.

## Overall decomposition

| Gate | Subgates | Current state |
|---|---:|---|
| 1. Foundation contracts and visible checkpoints | 4 | COMPLETED |
| 2. Completion Bundle and P9 identity boundary | 5 | COMPLETED |
| 3. Temporary panorama and completion envelope | 5 | COMPLETED FUNCTIONALLY; visual-quality refinement deferred to Gate 11 |
| 4. Automatic paths, collision, raw controls and masks | 6 | COMPLETED FUNCTIONALLY; route-quality refinements deferred to Gate 11 |
| 5. WAN completion and source-preserving composite | 5 | 5.1-5.4 COMPLETED; 5.5 PREVIEW READY / USER RUNTIME PENDING |
| 6. SphereSfM and COLMAP reconstruction | 6 | 6.1-6.4 COMPLETED; 6.5 NEXT |
| 7. Registration, fusion and provenance | 5 | PLANNED |
| 8. Geometry cleanup and texture recovery | 5 | PLANNED |
| 9. Original-view regression and Maya export | 5 | PLANNED |
| 10. Adaptive quality, hardware compliance and Refined integration | 6 | PLANNED |
| 11. Panorama & Adaptive Drone Refinement | 6 | DEFERRED UNTIL END-TO-END RESULT EXISTS |
| 12. Diagnostic Observability & Visual Branches | 6 | DEFERRED UNTIL END-TO-END RESULT EXISTS |

Total: **64 bounded subgates**.

## Gate 1 — 4/4 completed

1.1 Raw-hole safety policy and source authority.
1.2 Data-driven 3+1 flight-plan contract.
1.3 Four visible checkpoint roles and digest-safe resume.
1.4 Filesystem/security hardening and cross-platform closure.

## Gate 2 — 5 subgates

2.1 Completion Bundle v0.3 contract — COMPLETED.
2.2 Real v1.53 official-run P9/Baseline adapter — COMPLETED.
2.3 Identity/hash/stale/tamper comparator and rejection — COMPLETED.
2.4 ComfyUI Builder/Loader Preview + complete installer packaging — COMPLETED.
2.5 User runtime confirmation in real ComfyUI Desktop — COMPLETED through the integrated Refined r5 execution. The P10 boundary accepted the official Refined run and executed downstream.

## Gate 3 — 5 subgates

3.1 Canonical camera authority + panorama coordinate/math contract — COMPLETED.
Evidence: real v1.53 CameraBundle.v0.8 fixture; FOV recomputation; rigid
right-handed world-matrix validation; source↔ERP reversible ray math; strict
2:1 ERP contract; GitHub Actions run 35685846429 SUCCESS.
3.2 Perspective-to-equirectangular projection and source placement — COMPLETED.\nEvidence: seam-safe camera-local source footprint, reversible ERP sampling, half-pixel raster convention, orientation/no-flip tests and cross-platform CI.\n3.3 Source-lock mask + observed/unknown panorama map — COMPLETED.\nEvidence: exact observed/unknown complements, source authority lock, deterministic SHA-256 and cross-platform CI run 35686124075 SUCCESS.\n3.4 Bounded local completion envelope from authoritative scene/camera scale — COMPLETED.\nEvidence: flight-offset containment, rear/pole/world-scale rejection, unknown-only generation candidates and corrected cross-platform CI run 35686379285 SUCCESS.\n3.5 Gate 3 ComfyUI panorama preview + runtime validation — COMPLETED FUNCTIONALLY through the integrated Refined r5 execution.\nEvidence: registered IMAGE/MASK/MASK preview node, real v1.53 bundle rendered at 2048×1024, observed fraction ≈1.57%, candidate fraction ≈20.67%, PrimaryMesh characteristic radius ≈70.27 canonical units, direct ComfyUI temp-image UI support, and latest branch GitHub Actions run 35686851557 SUCCESS.

Gate 3 is functionally closed. The partial ERP/source-lock outputs are intentionally accepted as sufficient for end-to-end development; panorama quality and context coverage are deferred to Gate 11.

## Gate 4 — 6 subgates

4.1 Convert scene-relative flight definitions into authoritative world cameras — COMPLETED FUNCTIONALLY. Geometry-aware planning measures the current PrimaryMesh footprint at runtime and produces entry/center micro-orbit 360 paths plus outbound/return full-scene traversals. The integrated Refined node generates ERP, source lock, flight views, raw holes, trajectory map and GIF during the same execution. Real v1.53 runtime smoke: PASS; adaptive per-pose renderer CI run 35690559474 SUCCESS. Complete Installer r1 was rejected by the unchanged v1.53 Project Control self-test because the package accidentally contained multiple filenames matching ConceptGhost_Master_v*.json. r2 fixes packaging without weakening the test: exactly one canonical Master remains (ConceptGhost_Master_v1.53.0.json), while the integrated full Refined preview ships under a noncanonical preview filename and is installed only after base verification. Installer r2 reached the integrated Refined node but ComfyUI rejected the node before execution because linked run_dir deserialization shifted numeric widgets, producing view_width=1. r3 scopes run_dir forceInput=True only to the Refined evidence node and serializes [1024, 640, 2] for panorama_width/view_width/steps_per_segment. Installer r3 reached P10 runtime but rejected the real exported branch_mode `Refined / P9 Clone · P10 Reserved` because the boundary whitelist only contained the shorter Refined label. r4 accepts that exact official label while still rejecting near matches. For stabilization the runtime now uses exactly three adaptive missions: entry_micro_orbit_360, center_micro_orbit_360, and scene_round_trip (full-depth outbound + reverse-looking return). The planner remains data-driven for a later 7-10 mission budget without graph duplication. Current test artifact: ConceptGhost_v1.54_P10_Gate04_REFINED_COMPLETE_INSTALLER_r4.zip.\n4.2 Collision/clearance query contract and safe path adaptation — COMPLETED FUNCTIONALLY. Runtime uses a bounded approximate PrimaryMesh vertex-clearance cloud; all-blocked cases are advisory and fall back to unadapted routes so end-to-end execution continues. GitHub Actions run 35688972654 SUCCESS.
4.3 P10-only raw-hole geometry derivative — COMPLETED. Raw unsupported geometry is preserved without compensation/fill.
4.4 Geometry-control frame renderer — COMPLETED. Ordered control frames + disk manifest are emitted for downstream WAN.
4.5 Disocclusion/unsupported-region mask generator — COMPLETED. Strict binary unsupported masks are emitted without dilation/feather in the first-pass pipeline.
4.6 Per-flight control/mask Preview and runtime validation — COMPLETED FUNCTIONALLY via the integrated Refined r5 visual execution plus CI consolidation run 35702377645 SUCCESS.

## Gate 5 — 5 subgates

5.1 11 GB WAN runtime/resource policy — COMPLETED. Conservative first-pass profile: 832×480, max 33-frame WAN window, 4 steps, CFG 1.0, FP8 UNet, one window at a time, model/cache offload between windows. GitHub Actions run 35702692128 SUCCESS.
5.2 Masked-video conditioning adapter — COMPLETED. ConceptGhost-native WAN I2V masked-video conditioning uses the full geometry control sequence; white mask means generate/hole and black means known/P9. GitHub Actions run 35702777990 SUCCESS.
5.3 Sequential per-flight WAN completion + checkpoints — COMPLETED. A single data-driven sampler groups frames by mission, splits into sequential windows, pads temporal lengths to WAN's 4k+1 convention (for example 31→33) without changing the real route, saves raw WAN outputs, and unloads between windows. GitHub Actions run 35703621997 SUCCESS.
5.4 Source-preserving high-resolution composite — COMPLETED FOR FIRST END-TO-END PASS. Known control/P9 pixels are restored exactly after WAN sampling; WAN contributes only where the binary hole mask is white. A heavier SplatKit-style high-resolution coordinate-field composite remains eligible for later texture-quality refinement, but does not block end-to-end development.
5.5 Generated/composite Preview and runtime validation — PREVIEW READY / USER RUNTIME PENDING. Full ConceptGhost Master Refined workflow patch is implemented and CI-green (run 35703771287). WAN model asset manifest/hashes are locked and CI-green (run 35703927155). User-test artifact: ConceptGhost_v1.54_P10_Gate05_REFINED_WAN_COMPLETE_INSTALLER_r1.zip. The installer automatically verifies/downloads the four required WAN assets (~24 GB total) instead of bundling them in the ZIP.

## Gate 6 — 6 subgates

6.1 Generated-view collection and camera manifest — COMPLETED. The Refined evidence stage now persists a Scene-Contract-bound per-frame PINHOLE camera manifest, and Gate 6 pairs every source-preserved Gate 5 composite with the exact planned P9-world camera using global frame index as the join key. GitHub Actions run 35746991214 SUCCESS.
6.2 Reconstruction dataset adapter — COMPLETED. The primary path is now known-camera COLMAP because ConceptGhost already owns authoritative P9-derived drone poses. The adapter materializes source-preserved Gate 5 composites into `images/`, writes a deterministic `sparse/known/` COLMAP text model, preserves Scene Contract/provenance, deduplicates identical intrinsics, and explicitly converts ConceptGhost/Maya camera axes (+X right, +Y up, -Z forward) into COLMAP axes (+X right, +Y down, +Z forward). SphereSfM remains optional ERP validation/fallback rather than the primary pose solver for perspective P10 composites. GitHub Actions run 35748183037 SUCCESS.
6.3 Known-camera feature matching + sparse point triangulation (with SphereSfM optional validation path) — COMPLETED. Gate 6.3 now performs per-intrinsics feature extraction, adaptive matching (exhaustive for <=120 frames, sequential overlap 12 above that), fixed-pose point triangulation, and text conversion for sparse-cloud inspection. COLMAP's native `clear_points=1` filename transcription is used to synchronize database image IDs, while `fix_existing_frames=true` is enforced internally by `point_triangulator`; `refine_intrinsics=0` keeps P9-derived intrinsics authoritative. GitHub Actions run 35749126222 SUCCESS.
6.4 COLMAP dense stereo/fusion — COMPLETED. The first-pass RTX 2080 Ti profile uses 832 max image size, 4 GB PatchMatch/Fusion caches, 3 PatchMatch iterations, geometric consistency, single GPU 0 and fusion min_num_pixels=2. The runner emits per-command logs, dense_reconstruction_manifest.json, fused.ply, exact fused vertex count from the PLY header, sampled bounds/shape diagnostics and dense_fused_preview.svg with TOP XZ / FRONT XY / SIDE ZY projections. Completed fused clouds fail closed instead of being silently overwritten. GitHub Actions run 35750107834 SUCCESS.
6.5 Dense cloud → pre-fusion triangle mesh + health checks.
6.6 Reconstruction Preview and runtime validation.

## Gate 7 — 5 subgates

7.1 P10 reconstruction → P9 coordinate registration.
7.2 Authority-aware known/generated fusion.
7.3 Narrow transition geometry handling.
7.4 Per-face/per-region provenance.
7.5 Registration/fusion Preview and runtime validation.

## Gate 8 — 5 subgates

8.1 Defect analysis and bounded repair regions.
8.2 Local remesh/cleanup.
8.3 UV preservation/recovery.
8.4 Texture recovery with texel provenance.
8.5 Cleanup/texture Preview and runtime validation.

## Gate 9 — 5 subgates

9.1 Original-camera reprojection/regression metrics.
9.2 Observed-region rejection thresholds.
9.3 Maya scene assembly.
9.4 Diagnostic groups/sets/material/provenance export.
9.5 Preliminary editable Maya Preview and runtime validation.

## Gate 10 — 6 subgates

10.1 Residual-defect analyzer.
10.2 Adaptive-flight spending policy.
10.3 Restart/cache/resource cleanup.
10.4 RTX 2080 Ti 11 GB compliance run.
10.5 Refined topology integration: P9 (= Baseline) → P10.
10.6 Complete v1.54 release candidate, end-to-end validation and recovery bundle.

## Integration-first preview rule

User-facing P10 previews are no longer considered acceptable as isolated
laboratory workflows.

The official product surface is the existing ConceptGhost Master workflow:
- Baseline/P9 branch remains untouched.
- Refined/P9 Clone is the reserved P10 branch and must progressively become
  Refined = P9 + P10.
- Internal P10-Lab workflows/nodes remain valid only for engineering tests.
- A visual/runtime subgate is accepted only when the new capability is wired
  into a full ConceptGhost Master Refined preview and can be queued from the
  same Run Mode profile.
- Every preview installer must include all ConceptGhost node changes and all
  third-party packs/models required up to that preview.
- Do not ask the user to validate isolated P10-Lab graphs when the same
  capability can be exercised inside the Refined workflow.

Gate 3.5 status clarification:
- the isolated panorama diagnostic implementation is engineering evidence only;
- user-facing acceptance requires the same panorama/source-lock/candidate
  preview wired into Refined/P9 Clone.

Gate 4.1 status clarification:
- world-camera math is implemented and CI-green (run 35687023080);
- Gate 4.1 remains IN PROGRESS until the P10 insertion point and these camera
  paths are connected inside the full Refined workflow.

## Reporting rule

Every subgate report states:

- Gate X — N total subgates.
- Current Subgate X.Y — part Y/N.
- What was completed in this subgate.
- Acceptance evidence.
- Remaining subgates in the gate.
- Whether a user-facing Preview exists yet.
- GitHub commit / Drive checkpoint state.


### Gate 4.1 runtime hotfix r5

User runtime of r4 reached the integrated P10 evidence node and failed at the far-end turnaround with `Waypoint look vector cannot have zero length`. The failure was caused by linear interpolation between antipodal look directions (+forward to -forward), whose midpoint is exactly (0,0,0). r5 replaces vector lerp for look direction with deterministic angular yaw/pitch interpolation; exact 180-degree turns rotate through camera-local +right. Three-mission stabilization remains unchanged: `entry_micro_orbit_360`, `center_micro_orbit_360`, `scene_round_trip`. GitHub Actions run 35699515076 SUCCESS. Installer self-test and real Refined smoke both PASS. Current artifact: `ConceptGhost_v1.54_P10_Gate04_REFINED_COMPLETE_INSTALLER_r5.zip`.


### Gate 4.1 user runtime r5 PASS

User confirmed the r5 integrated Refined preview executed successfully in real ComfyUI Desktop. This closes the execution blocker for the three-mission adaptive planner and validates that the P10 node can run after the full Refined/P9 export. Visual-quality review remains pending the user's evidence package/screenshots before Gate 4.1 is marked fully accepted.

Current stabilization missions:
- entry_micro_orbit_360
- center_micro_orbit_360
- scene_round_trip

Do not start Gate 4.2 visual promotion until the Gate 4.1 runtime evidence is reviewed.


## Gate 11 — 6 subgates — DEFERRED UNTIL COMPLETE RESULT

This gate exists deliberately so current end-to-end development does not stall on route/panorama perfection.

11.1 Panorama/context quality audit: compare P9 partial ERP, source ERP and generated context.
11.2 Generic scene-coverage scoring from mesh footprint, occupancy, depth and uncovered solid angle.
11.3 Expand adaptive mission budget from the current 3 stabilization missions to a data-driven 7–10 mission budget without graph duplication.
11.4 Route-family refinement: lateral, elevated, diagonal, center-orbit, far-orbit and reverse passes selected only when they add coverage.
11.5 Coverage-aware stopping rule and route ranking using marginal new-visible-area / hole-discovery gain.
11.6 Final visual regression of panorama, drone paths, masks and runtime cost before release hardening.

Acceptance policy: Gate 11 is intentionally non-blocking until Gates 4–10 produce a complete end-to-end Refined result.


### Gate 5 Preview r1 recovery checkpoint

Gate 5 code reached the user-facing runtime boundary. Subgates 5.1–5.4 are implemented and CI-green; 5.5 is awaiting real ComfyUI runtime validation.

Artifact:
- `ConceptGhost_v1.54_P10_Gate05_REFINED_WAN_COMPLETE_INSTALLER_r1.zip`
- SHA-256: `dcdd3e6489eda41492e6e771cb4e1b2b4036056176023092f102921b302c25bb`
- Evaluation_Builds Drive ID: `1-5LulMqtamRAfQm7J_oMbI8MEy3wLlov`
- P10 recovery mirror Drive ID: `1nrTSZ6vM-HPYBBGdxYJdYsSKnFOp66jA`

Runtime installation path remains `03_INSTALL_ALL.bat → 04_VERIFY_INSTALL.bat → 05_RUN_CONCEPTGHOST.bat`. The installer validates or downloads the four hashed WAN assets (~24 GB) and reuses any matching files already present. The full preview workflow is `ConceptGhost_v1.54_P10_Gate05_REFINED_WAN_PREVIEW_r1.json`. Gate 5 remains open until the user confirms WAN hole filling + source-preserving composite in the real Refined workflow.


### Gate 6.1 image-camera authority checkpoint

Gate 6.1 is complete. The pipeline no longer needs to rediscover P10 camera poses from generated imagery. Each drone frame now carries authoritative PINHOLE intrinsics and a 4×4 P9-world camera matrix in `camera_manifest.json`, bound to the same Scene Contract. The reconstruction-input collector pairs Gate 5 source-preserved composite frames with those cameras and fails closed on missing/duplicate/mismatched frame identities. GitHub Actions run 35746991214 SUCCESS. Next subgate: 6.2 dataset adapter.


### Gate 6.2 known-camera COLMAP dataset checkpoint

Gate 6.2 is complete. ConceptGhost no longer hands its perspective P10 composites to a spherical SfM solver merely to rediscover camera poses that are already known. The primary reconstruction dataset now contains the source-preserved Gate 5 images plus an authoritative COLMAP text model in `sparse/known/` generated from the P9-world camera matrices.

Coordinate conversion is explicit and tested:
- source camera convention: +X right, +Y up, -Z forward;
- COLMAP convention: +X right, +Y down, +Z forward;
- local-axis conversion: `diag(1,-1,-1)`;
- camera-to-world matrices are converted to COLMAP world-to-camera `qvec/tvec`.

The dataset also writes `reconstruction_inputs.json` and `dataset_manifest.json` with Scene Contract, image provenance, camera authority and per-frame identity. Existing non-empty output roots fail closed unless overwrite is explicitly requested. GitHub Actions run 35748183037 SUCCESS. Next subgate: 6.3 sparse reconstruction using fixed/known cameras; SphereSfM is retained as optional ERP validation/fallback.


### Gate 6.3 fixed-camera sparse triangulation checkpoint

Gate 6.3 is complete. The runner creates/resumes `database.db`, extracts features by known PINHOLE intrinsics group, selects a matcher by dataset size, triangulates against the `sparse/known/` model, and exports a TXT copy of the triangulated model for point-count/health inspection.

Current policy:
- <=120 frames: `exhaustive_matcher` for maximum first-pass connectivity;
- >120 frames: `sequential_matcher` with overlap 12 and loop detection disabled until Gate 11 route-scale refinement;
- P9/P10 camera poses stay fixed through COLMAP's `point_triangulator`;
- camera intrinsics are not refined;
- completed sparse outputs are never silently overwritten;
- each COLMAP step writes a dedicated log and a final `sparse_triangulation_manifest.json`.

GitHub Actions run 35749126222 SUCCESS across Windows Python 3.12, Windows Python 3.14 and Ubuntu Python 3.12. Next subgate: 6.4 COLMAP dense stereo/fusion.


## Gate 12 — 6 subgates — DEFERRED UNTIL COMPLETE RESULT

This gate standardizes visual and machine-readable diagnostics across the full Refined pipeline without changing the functional architecture.

12.1 Stage evidence inventory: enumerate every major P9/P10 stage and classify whether a visual proxy, numeric diagnostic, log, or all three are meaningful.
12.2 Unified evidence folder contract per run/stage with stable filenames, manifests and provenance.
12.3 Visual branches for panorama, camera paths, holes/masks, WAN raw/composite, sparse cloud, dense cloud, registration/fusion, cleanup/texture and final reprojection where applicable.
12.4 Machine-readable health metrics and threshold summaries for each stage, including explicit PASS/WARN/FAIL reasons.
12.5 Consolidated diagnostic bundle + HTML/JSON index linking visuals, logs, metrics and source artifacts.
12.6 Regression/acceptance audit ensuring a stage can be isolated and diagnosed without rerunning unrelated upstream stages when checkpoints are valid.

Cross-cutting rule effective immediately: new stages should emit useful logs/manifests and a lightweight visual proxy whenever practical, but Gate 12 remains non-blocking until the first complete end-to-end result exists.


### Gate 6.4 dense fusion + visual diagnostics checkpoint

Gate 6.4 is complete. Dense reconstruction now has both machine-readable and visual evidence rather than only a final point cloud.

Runtime sequence:
- `image_undistorter` from `sparse/triangulated` into the COLMAP dense workspace;
- `patch_match_stereo` with geometric consistency, GPU 0, max image size 832, 4 GB cache and 3 iterations;
- `stereo_fusion` with geometric input, max image size 832, 4 GB cache and `min_num_pixels=2`;
- PLY health analysis and lightweight three-view SVG rendering.

Artifacts:
- `dense/fused.ply`
- `dense/fused.ply.vis` when produced by COLMAP
- `dense/dense_fused_preview.svg`
- `dense_reconstruction_manifest.json`
- `logs/gate6_4/00_image_undistorter.log`
- `logs/gate6_4/01_patch_match_stereo.log`
- `logs/gate6_4/02_stereo_fusion.log`

The visual preview samples the fused PLY deterministically and renders TOP XZ, FRONT XY and SIDE ZY projections with point colors, count and sampled bounds. This provides a quick way to detect collapsed/flattened/displaced dense geometry without opening a 3D package. GitHub Actions run 35750107834 SUCCESS across Windows Python 3.12, Windows Python 3.14 and Ubuntu Python 3.12. Next subgate: 6.5 dense cloud → pre-fusion triangle mesh + health checks.
