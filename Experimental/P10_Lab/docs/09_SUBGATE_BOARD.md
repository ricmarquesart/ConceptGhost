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
| 6. SphereSfM and COLMAP reconstruction | 6 | 6.1-6.5 COMPLETED; 6.6 PREVIEW READY / USER RUNTIME PENDING |
| 7. Registration, fusion and provenance | 5 | PLANNED |
| 8. Geometry cleanup and texture recovery | 5 | PLANNED |
| 9. Original-view regression and Maya export | 5 | PLANNED |
| 10. Adaptive quality, hardware compliance and Refined integration | 6 | PLANNED |
| 11. Panorama, Adaptive Drone & HiRes Source-Authority Refinement | 8 | DEFERRED UNTIL END-TO-END RESULT EXISTS |
| 12. Diagnostic Observability & Visual Branches | 6 | DEFERRED UNTIL END-TO-END RESULT EXISTS |

Total: **66 required bounded subgates**, plus the optional non-blocking Gate 7.2C confidence overlay.

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
6.5 Dense cloud → pre-fusion triangle mesh + health checks — COMPLETED. The first-pass Poisson mesher converts `dense/fused.ply` into `dense/pre_fusion_mesh.ply` with depth 10, trim 10, point_weight 1.0 and vertex color enabled. The runner writes a dedicated Poisson log, `prefusion_mesh_manifest.json`, exact vertex/face counts, face/vertex ratio, invalid-face diagnostics, sampled degenerate-face ratio, XYZ bounds/spans, flattened-axis warnings and `pre_fusion_mesh_preview.svg` with TOP XZ / FRONT XY / SIDE ZY triangle projections. Existing meshes fail closed instead of being silently overwritten. GitHub Actions run 35751267600 SUCCESS.
6.6 Reconstruction Preview and runtime validation — PREVIEW READY / USER RUNTIME PENDING. The full Refined Master now connects Gate 5 WAN/source-preserved composite outputs to a resumable Gate 6 known-camera reconstruction runtime. It reuses valid stage checkpoints, runs dataset→sparse→dense→Poisson mesh only where required, returns a live pre-fusion mesh preview in ComfyUI, and writes a reconstruction_runtime_manifest.json. COLMAP 4.2.0 CUDA is frozen as the required reconstruction runtime asset. GitHub Actions run 35752970504 SUCCESS. User-test package built and structurally validated: ConceptGhost_v1.54_P10_Gate06_REFINED_RECONSTRUCTION_COMPLETE_INSTALLER_r1.zip, 12,064,521 bytes, SHA-256 9ec7a63f0065cd10314ba0129877c4d24cc9bce69fdc44d1645208082720c4a2. Runtime acceptance remains pending.

## Gate 7 — 5 subgates

7.1 P10 reconstruction → P9 coordinate registration.
7.2 Authority-aware known/generated fusion.
   - **Confidence diagnostics + optional refinement overlay (7.2C):** after 7.1 registration, always compute a per-face P9/P10 geometry-confidence field and expose an always-available dedicated ComfyUI 3D confidence preview (HIGH=blue, LOW/VERY_LOW=red, NEUTRAL uncolored). Geometry refinement remains **DEFAULT OFF** and, only when explicitly enabled, may allow low/very-low-confidence side/back geometry to become eligible for bounded replacement/remesh while preserving high-confidence source-facing geometry. Confidence visualization is diagnostic-only and is not exported to Maya. Full policy: `docs/11_GEOMETRY_CONFIDENCE_REFINEMENT_POLICY.md`.
7.3 Narrow transition geometry handling.
   - **Free-space / visibility carving extension:** consume Gate 6 geometric depth + known-camera visibility to classify OCCUPIED / FREE / UNKNOWN / CONFLICT. Add a COLMAP Delaunay visibility-aware mesh branch alongside Poisson, then enforce CONFIRMED_FREE as a no-fill constraint during Gate 7 fusion/transition handling. Detailed policy: `docs/12_FREE_SPACE_VISIBILITY_CARVING_POLICY.md`.
7.4 Per-face/per-region provenance, including confidence classification metadata for diagnostics and optional refinement provenance only when 7.2C refinement is enabled.
7.5 Registration/fusion Preview and runtime validation. Confidence analysis/3D preview is expected as a normal diagnostic surface, while the required refinement-OFF path remains the geometry acceptance baseline; confidence refinement ON must pass a separate A/B regression before it can be considered beneficial.

### Gate 7.3 internal implementation plan — Free-Space / Visibility Carving

**Why this exists:** the pipeline must distinguish a valid opening from missing reconstruction. A table-leg gap, fence opening, arch center or visible gap between geometry must not be treated as a hole that should be sealed. Conversely, an unseen back surface is UNKNOWN and may still require generation/reconstruction. Empty space therefore becomes explicit evidence, not merely absence of triangles.

**Primary rule:** use known-camera visibility + geometrically consistent depth, not semantic object labels. If a camera ray reaches a supported farther surface, the traversed segment before that first surface is evidence of FREE space. A narrow band around the first surface is OCCUPIED. Volume behind the first surface remains UNKNOWN. Mixed FREE/OCCUPIED evidence becomes CONFLICT.

**Gate placement and dependency flow:**
- Gate 6.4 supplies geometric depth maps, normal maps and consistency graphs from the existing COLMAP dense workspace.
- Gate 6.5 gains a Delaunay visibility-aware meshing candidate beside the already-proven Poisson output. Gate 6 is not reopened as a current blocker; these producer extensions are activated when Gate 7 implementation begins.
- Gate 7.2C consumes FREE/OCCUPIED/CONFLICT as confidence evidence.
- Gate 7.3 is the main consumer and applies CONFIRMED_FREE as a no-fill/no-bridge topology constraint.
- Gate 8.1/8.2 classifies and repairs defects using explicit labels such as VALID_OPENING, FALSE_SURFACE_IN_CONFIRMED_FREE, MISSING_SURFACE_UNKNOWN and CONFLICT_REGION.
- Gate 11 may use UNKNOWN/CONFLICT to spend additional drone coverage only after first end-to-end completion.
- Gate 12 adds standardized Free-Space 3D diagnostics.

**Required components:**
- existing COLMAP 4.2.0 CUDA runtime;
- known P9-derived per-frame cameras;
- Gate 5 source-preserved composite views;
- COLMAP PatchMatch `*.geometric.bin` depth maps;
- COLMAP normal maps;
- COLMAP consistency graphs;
- existing Poisson mesh;
- new COLMAP Delaunay branch;
- native sparse visibility/free-space field;
- Gate 7 confidence layer;
- ComfyUI-only Free-Space 3D Preview.

**New ConceptGhost modules planned:**
- `p10_lab/colmap_dense_io.py` — parse/validate depth, normals and consistency graphs;
- `p10_lab/free_space_evidence.py` — sparse ray-carving evidence;
- `p10_lab/free_space_constraints.py` — FREE/OCCUPIED/UNKNOWN/CONFLICT classification and no-fill constraints;
- `p10_lab/free_space_preview.py` — temporary 3D diagnostic representation.

**Files to extend:**
- `dense_reconstruction.py`;
- `prefusion_mesh.py`;
- `reconstruction_runtime.py`;
- `preview_nodes.py`;
- `workflow_integration.py`.

**Initial free-space classification policy:**
- CONFIRMED_FREE requires multiple supporting views and at least two independent route/view groups;
- adjacent frames from one drone are correlated and do not count as fully independent votes;
- require useful baseline/view-angle diversity;
- reject low-consistency depth samples;
- protected original-source/P9 surfaces outrank generated-view contradictions;
- UNKNOWN is never treated as FREE;
- CONFLICT fails conservatively and is not auto-carved.

**Authority order for free-space decisions:**
1. original-source/P9 observed geometry;
2. HiRes source-authority reprojection;
3. P10 COLMAP geometric support;
4. WAN-only generated multiview evidence;
5. isolated/low-consistency generated evidence as diagnostic only.

**Meshing strategy:** keep both Poisson and Delaunay. Poisson provides smoother surface candidates; Delaunay contributes visibility-aware structural evidence. Neither is globally authoritative by itself. Gate 7 fusion compares both against explicit free-space evidence.

**ComfyUI diagnostic:** planned node `P10 · Free-Space 3D Preview`:
- FREE/CONFIRMED_FREE = cyan/green;
- OCCUPIED = neutral/white;
- CONFLICT = magenta/yellow;
- UNKNOWN = hidden;
- orbit/zoom/pan inspection;
- diagnostic only;
- no Maya materials/groups/selection sets;
- temporary proxy stored in the run TEMP workspace and auto-cleaned after validated success.

**Hardware/storage policy:** target RTX 2080 Ti 11 GB; use sparse/hash/chunked cells, sequential camera processing and depth downsampling. Never allocate a full dense world grid at image resolution. First target is approximately 256–384 sparse cells across the useful scene span, independent of final mesh triangle density.

**Internal execution steps (do not change the 66 required-subgate count):**
- FS-1 Dense evidence contract.
- FS-2 Sparse ray evidence accumulator.
- FS-3 Independence + state classification.
- FS-4 Delaunay mesh branch.
- FS-5 Coupling to Gate 7.2C confidence.
- FS-6 CONFIRMED_FREE no-fill enforcement in Gate 7.3.
- FS-7 ComfyUI Free-Space 3D Preview.
- FS-8 A/B fixtures: table, fence/railing, arch/doorway, chair, foliage and solid-wall control.
- FS-9 RTX 2080 Ti / 7 routes × 30 frames runtime and TEMP storage validation.
- FS-10 Promotion decision after repeatable improvement and no original-view regression.

**Acceptance:** valid openings stay open; false bridges/walls crossing CONFIRMED_FREE are materially reduced; source-observed geometry remains unchanged; UNKNOWN is not accidentally carved; foliage/conflict fails conservatively; checkpoints remain resumable; free-space failures do not corrupt the standard Poisson/Gate 7 path.

Full specification: `docs/12_FREE_SPACE_VISIBILITY_CARVING_POLICY.md`.

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
10.3 Unified per-run TEMP workspace lifecycle + restart/cache/resource cleanup. Implement `<ComfyUI output>/conceptghost/_temp/<run_id>/`, expose `temp_workspace_path`, record ACTIVE/FAILED_RETAINED/CLEANUP_PENDING/CLEAN states, preserve on failure, and only mark intermediates cleanup-eligible after downstream validation.
10.4 RTX 2080 Ti 11 GB compliance run.
10.5 Refined topology integration: P9 (= Baseline) → P10.
10.6 Complete v1.54 release candidate, end-to-end validation, safe auto-clean and recovery bundle. Confirm final `.ma`/mesh/textures before deleting heavy intermediates, emit `cleanup_manifest.json`, preserve failed-run workspaces, and retain the compact diagnostic package.

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


## Gate 11 — 8 subgates — DEFERRED UNTIL COMPLETE RESULT

This gate exists deliberately so current end-to-end development does not stall on route/panorama perfection. It now also owns the REQUIRED HiRes source-authority refinement requested for the final-quality pass.

11.1 Panorama/context quality audit: compare P9 partial ERP, source ERP and generated context.
11.2 Generic scene-coverage scoring from mesh footprint, occupancy, depth and uncovered solid angle.
11.3 Official default camera dataset: **7 geometry-adaptive routes × 30 configurable frames per route (~210 frames)**. `frames_per_drone` must be a visible node property and changing it must not require workflow edits. More frames are not assumed better; later useful-view selection/subsampling may reduce the reconstruction set.
11.4 Route-family refinement: lateral, elevated, diagonal, center-orbit, far-orbit and reverse passes selected only when they add coverage.
11.5 Coverage-aware stopping rule and route ranking using marginal new-visible-area / hole-discovery gain.
11.6 REQUIRED HiRes Composite source-authority pass. Logical insertion point is after Gate 5 WAN generation and before Gate 6 reconstruction input collection. Presets: **4K DEFAULT / 6K / 8K**. Reproject full-resolution authoritative source pixels through P9/P10 geometry; use WAN only where geometry/source authority has no answer. Geometry/source-authority mode is primary and must not require RAFT. Preserve per-frame coverage/gate masks and visual diagnostics.
11.7 REQUIRED HiRes Views / dataset augmentation. Logical insertion point is between Gate 6.1 camera authority and Gate 6.3 feature extraction. Render only useful additional high-resolution PINHOLE views from authoritative geometry/source texture, register them as additional known-camera observations without moving existing P9/P10 cameras, respect the shared TEMP workspace lifecycle, optionally retriangulate, and retain selected views for Gate 8 texture recovery.
11.8 Final A/B regression: base end-to-end vs HiRes-enhanced end-to-end, including panorama/drone paths, WAN holes, source coverage, sparse/dense reconstruction, mesh quality, texture fidelity, runtime, TEMP workspace peak size and cleanup result.

Acceptance policy: Gate 11 remains non-blocking until Gates 4–10 produce a complete end-to-end Refined result. Once activated, 11.6 and 11.7 are REQUIRED final-quality work, not optional experiments.

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
12.2 Unified evidence + TEMP workspace contract per run/stage with stable filenames, manifests, provenance, visible `temp_workspace_path`, lifecycle state and measured/estimated storage.
12.3 Visual branches for panorama, camera paths, holes/masks, WAN raw/composite, sparse cloud, dense cloud, free-space/occupancy, registration/fusion, cleanup/texture and final reprojection where applicable.
12.4 Machine-readable health metrics and threshold summaries for each stage, including explicit PASS/WARN/FAIL reasons plus workspace state (`CLEAN`, `ACTIVE`, `FAILED_RETAINED`, `CLEANUP_PENDING`).
12.5 Consolidated retained diagnostic package + HTML/JSON index linking visuals, summarized logs, metrics and removed-artifact inventory. Target **<=200 MB**, preferably substantially smaller; never retain full 4K/6K/8K frame sequences or complete dense/cache intermediates in this permanent package.
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


### Gate 6.5 pre-fusion mesh + health diagnostics checkpoint

Gate 6.5 is complete. The P10-only dense cloud is now converted into a preliminary triangle surface before Gate 7 registration/fusion.

First-pass meshing policy:
- COLMAP `poisson_mesher`;
- Poisson depth 10 rather than COLMAP's default 13 to keep the first end-to-end pass bounded;
- trim 10;
- point_weight 1.0;
- vertex color enabled;
- no silent overwrite of an existing pre-fusion mesh.

Artifacts:
- `dense/pre_fusion_mesh.ply`
- `dense/pre_fusion_mesh_preview.svg`
- `prefusion_mesh_manifest.json`
- `logs/gate6_5/00_poisson_mesher.log`

Mesh diagnostics include exact PLY vertex/face counts, face-to-vertex ratio, exact invalid-index face count, deterministic sampled degenerate-face ratio, XYZ bounds/spans, flattened-axis warnings and a PASS/WARN health status. The visual preview renders sampled triangle edges in TOP XZ, FRONT XY and SIDE ZY so exploded, collapsed, sparse or flattened topology can be inspected without opening Maya.

GitHub Actions run 35751267600 SUCCESS across Windows Python 3.12, Windows Python 3.14 and Ubuntu Python 3.12. Next subgate: 6.6 integrated reconstruction preview/runtime validation.


### Gate 6.6 integrated reconstruction preview checkpoint

Gate 6.6 implementation is complete and user runtime acceptance is pending. The Refined Master now contains one integrated reconstruction runtime node downstream of Gate 5. It consumes the live WAN manifest and authoritative camera manifest, then resumes or builds Gate 6.2–6.5 outputs as needed.

The Gate 6 Complete Installer:
- retains the proven complete v1.53 / Gate 5 payload;
- freezes the P10 Gate 6 overlay to commit `d07f0c82ab2466e68479c91753f2617ce760a930`;
- validates/downloads the existing four WAN assets only if missing or hash-invalid;
- validates/downloads/extracts COLMAP 4.2.0 Windows x64 CUDA;
- verifies the COLMAP executable and full P10 node/workflow contract;
- keeps `03_INSTALL_ALL.bat → 04_VERIFY_INSTALL.bat → 05_RUN_CONCEPTGHOST.bat`;
- enables stage-level checkpoint resume by default;
- exposes a live mesh preview in the same Refined Master workflow.

Artifact build:
- `ConceptGhost_v1.54_P10_Gate06_REFINED_RECONSTRUCTION_COMPLETE_INSTALLER_r1.zip`
- size: 12,064,521 bytes
- SHA-256: `9ec7a63f0065cd10314ba0129877c4d24cc9bce69fdc44d1645208082720c4a2`
- 149 ZIP members
- Project Control self-test PASS
- bundle structure PASS
- GitHub Actions run 35752970504 SUCCESS.

Runtime acceptance is required before Gate 6 is marked fully closed. Next development gate after runtime acceptance is Gate 7 registration/fusion/provenance.


### Required HiRes Source-Authority Integration Plan

Decision: HiRes Composite and HiRes Views / dataset augmentation are REQUIRED for the final-quality Refined pipeline, while first end-to-end development continues without reopening Gates 5/6 until Gate 10 is complete.

Why:
- Gate 5 WAN is necessary only for genuinely unknown/disoccluded pixels. It must not repaint source-observed detail when geometry can reproject the authoritative source.
- High-resolution known-source views add feature-rich, internally consistent observations to COLMAP and later texture recovery without changing the camera authority hierarchy.
- Existing P9/P10 cameras remain fixed. HiRes evidence is additive and lower authority than source/P9 geometry.

Logical insertion points:
1. **HiRes Composite**: immediately after WAN generation and before reconstruction dataset materialization. The composite must be geometry/source-first: authoritative source where reprojection is valid; WAN only in holes. It replaces the current first-pass low-resolution source-preserving composite for the final-quality rerun.
2. **HiRes Views / dataset augmentation**: after the camera manifest is known and before feature extraction/matching. Add selected high-resolution PINHOLE views with exact P9/P10-derived intrinsics/poses. These views participate in sparse/dense reconstruction and are retained for Gate 8 texture baking/recovery.

Implementation preference:
- Port/adapt the needed SplatKit ideas natively into ConceptGhost instead of making the entire SplatKit/SphereSfM/Matrix-3D stack mandatory.
- Reuse ConceptGhost P9/P10 geometry and camera authority instead of re-running MoGe solely for HiRes rendering.
- Geometry-first HiRes Composite does **not** require RAFT optical flow; RAFT is only needed for the SplatKit WAN-base mode, which is not the ConceptGhost authority policy.
- Debug-save intermediate WAN-upscaled/fill frames remains OFF by default and can be enabled selectively for Gate 12 diagnostics.

Reference storage from SplatKit HiRes Composite documentation at 8192-pixel panorama width, four trajectories:
- 25 selected frames per trajectory (`0-15,16-/8`): ~2.3 GB.
- 41 selected frames per trajectory (`0-80/2`): ~3.8 GB.
- all 81 frames per trajectory: ~7.4 GB.
Approximate linear scaling to future ConceptGhost 7–10 routes at the same 8K output:
- 25 frames/route: ~4.0–5.8 GB.
- 41 frames/route: ~6.7–9.5 GB.
- 81 frames/route: ~13.0–18.5 GB.
HiRes Views are separate full-resolution PINHOLE PNGs; expected working budget is ~1–3 GB for a moderate 4K augmentation set across 7–10 routes, and roughly ~4–8 GB for a comparable 8K-heavy set. Exact disk use is scene/compression/view-count dependent and must be measured in the manifest at runtime.
Software/model footprint for the native ConceptGhost adaptation is small: the current SplatKit repository itself is only ~2.9 MB of versioned files, and geometry-first HiRes Composite requires no additional RAFT checkpoint. The dominant cost is generated image data, not new model weights.

Upstream technical references:
- https://github.com/mickmumpitz/ComfyUI-SplatKit
- https://github.com/mickmumpitz/ComfyUI-SplatKit/blob/main/docs/HIRES_COMPOSITE.md

### Gate 5/6 runtime blocker — ComfyUI WAN widget serialization

Real user runtime on 2026-09-22 exposed two layers of the same Gate 5/6 blocker.

First failure: node 2207 (`ConceptGhostP10WanSequentialSampler`) executed and rejected invalid width/height values. Runtime normalization hotfix `fa6d0b9...` made the sampler robust when invalid dimensions reach Python.

Second failure (r2): ComfyUI blocked the prompt *before node execution*. The live node showed `seed=0, width=480, height=33, max_window_length=4, steps=1, cfg=1.0`. Root cause: the serialized `widgets_values` omitted ComfyUI's auxiliary seed control widget (`control_after_generate`). The frontend therefore consumed `832` as that hidden seed-control value and shifted every subsequent widget left. The optional `clip_vision_output` socket was also omitted from the serialized input list and is now emitted explicitly.

Definitive workflow serialization policy:
- input tail is explicitly `clip_vision_output, seed, width, height, max_window_length, steps, cfg`;
- widget values are explicitly `[0, "fixed", 832, 480, 33, 4, 1.0]`;
- runtime dimension normalization remains as a second safety layer;
- installer verifier and bundle test reject any Gate 6 workflow that does not preserve this exact modern-Comfy serialization contract.

GitHub workflow serialization fix: `168a4a5879505fb8116ad56de25ebe4dfa2e1cd4`.
Regression-contract commit: `88a0b1604c3b1a9c1163e653238e02171a8dc6b3`.
GitHub Actions run `35760003619`: SUCCESS.

Replacement user-test artifact: `ConceptGhost_v1.54_P10_Gate06_REFINED_RECONSTRUCTION_COMPLETE_INSTALLER_r3.zip`.
- Size: 12,077,109 bytes; 146 ZIP members; SHA-256 `c45a1ada40821aadbcd319074657bbd150e7b71bbe9f74f1fd8b259944f03246`.
- Evaluation_Builds Drive ID: `1YKUB9_XP06SbiNPjlA_RXiTjzbOimzbz`.
- P10 recovery mirror Drive ID: `1oBWVddR2prgjgnuiNpZ4MvRISeMSHcrl`.
- Static package validation PASS: Gate6 bundle structure, Project Control single canonical Master, installer argument forwarding, non-destructive installer contract, and explicit node-2207 widget/input serialization contract.
r2 is superseded and must not be used for further runtime acceptance.
### Gate 6 r2 WAN-dimension hotfix package

The real Gate 5/6 runtime blocker was fixed and repackaged.
- Hotfix implementation commit: `fa6d0b9cb547bc2a51bd34d4dfd56c59960b9fb7`.
- GitHub Actions run `35757635947`: SUCCESS.
- Artifact: `ConceptGhost_v1.54_P10_Gate06_REFINED_RECONSTRUCTION_COMPLETE_INSTALLER_r2.zip`.
- Artifact SHA-256: `21bb2f2276fc4cdf4833c74213180ee58d863acb1aab235e47e2d02951cd428a`.
- ZIP size: 12,075,894 bytes; 150 members; ZIP integrity PASS.
- Evaluation_Builds Drive ID: `1FAonnTDX0sJ7ucUUJEhz_CKoYP6aZJIR`.
- P10 recovery mirror Drive ID: `17x-IXXSAYHhdy6IBqVQ53zHAfKy8gEyC`.
- Exactly one canonical `ConceptGhost_Master_v*.json` remains in the package.
- Gate 6 code overlay now pins 13 files at the hotfix commit, including `wan_sequence.py`.
- Integrated Gate 6 workflow ships under the new filename `ConceptGhost_v1.54_P10_Gate06_REFINED_RECONSTRUCTION_PREVIEW_r2.json`, avoiding reuse of stale r1 workflow-tab state.

Runtime acceptance remains pending. User should discard r1 and use Gate 6 r2. The same r2 package fixes Gate 5 because Gate 6 installs/verifies the complete Gate 5 stack before applying the Gate 6 overlay.

### P10 Quality Refinement Policy — official defaults

The detailed approved policy is stored in `docs/10_P10_QUALITY_REFINEMENT_POLICY.md`.

Release-target defaults:
- `drones = 7`
- `frames_per_drone = 30`
- `HiRes Composite = ON`
- `HiRes Views = ON`
- `hires_resolution = 4K` with 6K/8K optional presets
- `auto_clean = ON`
- `preserve_on_failure = ON`
- `debug_heavy = OFF`
- `diagnostic_package = ON`
- `diagnostic_package_max = 200 MB`

Heavy per-run data belongs under `<ComfyUI output>/conceptghost/_temp/<run_id>/`, with the absolute `temp_workspace_path` visible in the UI and manifests. Heavy intermediates are removed only after their downstream dependencies and final deliverables validate successfully. Crash/failure/cancel retains the workspace for diagnosis. Final success emits `cleanup_manifest.json` before cleanup and preserves only final deliverables plus the compact diagnostic package.


### Gate 6 r4 layout-only preview

The Gate 6 r4 package is functionally equivalent to r3 for execution/runtime behavior, but reorganizes all current P10 Gate 4/5/6 nodes into a dedicated visual lane below the proven Refined/P9 graph.

Layout policy:
- Gate 4 evidence and visual diagnostics occupy the left side of the P10 lane.
- Gate 5 WAN loaders/conditioning/sampler/composite occupy the center.
- Gate 6 reconstruction runtime and mesh preview occupy the right.
- Baseline/P9 and existing Refined/P9 node positions are untouched.
- Automated rectangle-overlap regression test is release-blocking for the current known P10 nodes.

Validation:
- complete packaged workflow node-overlap count: **0**;
- Gate 6 bundle structure PASS;
- Project Control single canonical Master PASS;
- installer argument forwarding PASS;
- non-destructive installer PASS;
- node 2207 modern-Comfy serialization remains `[0, "fixed", 832, 480, 33, 4, 1.0]`.

Artifact:
- `ConceptGhost_v1.54_P10_Gate06_REFINED_RECONSTRUCTION_COMPLETE_INSTALLER_r4.zip`
- size: 12,119,673 bytes
- ZIP members: 163
- SHA-256: `dbc8e1d8acd49ca94fe3b4209db4b9936ad76f823c64b828fda8edf4bbb4af69`
- Evaluation_Builds Drive ID: `1BHqrJJrH4XCJU8a4UL-9dDHKpxSivqLf`
- P10 recovery mirror Drive ID: `1AytMTn5AVbGUGHBUvtmr8vFwERH_4EY5`
- layout implementation commit: `94f82dd3baa5b773de00047708ff5b84c19afc56`
- layout regression test commit: `8b7e08c7c59724d54022672b390ef985e174240f`
- GitHub Actions run `35762253447`: SUCCESS.

r4 changes layout only. If the user is already running r3, that test remains valid; installing r4 is only necessary to obtain the reorganized workflow surface.


### Gate 6 r5 implicit-seed-control removal

User runtime with r4 still loaded node 2207 with an invalid shifted widget state: the visible `seed` value became `fixed`, followed by `width=480`, `height=33`, `max_window_length=4`, `steps=1`. Investigation against the current ComfyUI frontend confirmed that inputs named exactly `seed` or `noise_seed` receive an implicit client-side control-after-generate widget. That made hand-authored workflow serialization version-sensitive.

Definitive r5 fix:
- rename the sampler input from `seed` to `wan_seed`;
- remove all dependence on the implicit `fixed/randomize/increment/decrement` helper;
- serialize widgets deterministically as `[0, 832, 480, 33, 4, 1.0]`;
- explicit input tail is `clip_vision_output, wan_seed, width, height, max_window_length, steps, cfg`;
- retain the runtime dimension-normalization safety layer;
- retain the r4 zero-overlap P10 visual lane.

Implementation:
- runtime rename commit: `1f4243611e14f271157a8a2505797a95d4495233`;
- workflow serializer commit: `abbdd99f74f6c7ec093e26fd7aedb137df626ee1`;
- regression contract commit: `1b78057d3e068005955b3f47dc5c9eac787b00fd`;
- GitHub Actions run `35763186003`: SUCCESS.

Artifact:
- `ConceptGhost_v1.54_P10_Gate06_REFINED_RECONSTRUCTION_COMPLETE_INSTALLER_r5.zip`
- size: 12,072,091 bytes
- ZIP members: 149
- SHA-256: `5f8e165fb904d3a0c64d74aff1c87d46d4b051b4044c9ce21b58fd78890f6e6a`
- Evaluation_Builds Drive ID: `1wgnLY0zqgQqalw5TK46KfQYk3Qux7ZyR`
- P10 recovery mirror Drive ID: `1zMSHwV9JFvhDmb9acTIKYJIZcGzUHRdo`

Static package validation PASS:
- Gate 6 bundle structure;
- Project Control single canonical Master;
- installer argument forwarding;
- non-destructive installer;
- exact node-2207 `wan_seed` input contract;
- exact WAN widgets `[0,832,480,33,4,1.0]`;
- complete workflow rectangle-overlap count = 0.

r5 supersedes r4 for further Gate 5/6 runtime acceptance.


### Gate 6 r7 WAN VAE decode-shape hotfix

Real ComfyUI runtime progressed past the earlier WAN dimension, widget-serialization and `wan_seed` failures and reached WAN VAE decode plus frame serialization. Node 2207 then failed when Pillow received a frame array with an extra video dimension.

Observed runtime failure:
- node: `ConceptGhostP10WanSequentialSampler` (2207);
- failure point: `Image.fromarray(raw_array)`;
- effective symptom: decoded WAN video remained rank-5, so per-frame slicing produced an unsupported Pillow array shape.

r7 correction:
- normalize a decoded rank-5 WAN video tensor to ComfyUI IMAGE batch shape `[N,H,W,C]` immediately after `vae.decode`;
- leave already-correct rank-4 IMAGE batches unchanged;
- fail closed on unexpected ranks/channel counts;
- perform frame accounting, source-preserving composite and Pillow save only after normalization.

Evidence:
- runtime fix commit: `a5c9383990f5e3f4ad55f7ec1b2474be2a505a3a`;
- regression commit: `87c56a0644cb1983882264062268596d7e0f97c4`;
- GitHub Actions run `35771754630`: SUCCESS;
- current branch head `81d2716285d0719fb4496b2a29c2fc43583e6ced`: SUCCESS in run `35772121481`;
- artifact: `ConceptGhost_v1.54_P10_Gate06_REFINED_RECONSTRUCTION_COMPLETE_INSTALLER_r7.zip`;
- ZIP size: 12,102,618 bytes;
- SHA-256: `c921fd235ca54b61ab807cf6e94764073b7a818b8079f7c537331c9723f8325c`;
- Evaluation_Builds ZIP ID: `18VJ3Kn5LU1wPJ4dJsF_DZvxIHVutEBE5`;
- P10 recovery ZIP ID: `1VMxkp9ohh4tLe9-6j5TmsHGeDQBpalx-`;
- expanded Evaluation_Builds folder ID: `1RYy_gkp83lcIFHHGgwG00t1DpEPXf4PU`, verified at 155 files.

Status remains **Gate 6.6 PREVIEW READY / USER RUNTIME PENDING**. Do not begin required Gate 7 implementation until the integrated r7 runtime is accepted, although roadmap/design work already recorded for Gate 7.2C remains valid.
