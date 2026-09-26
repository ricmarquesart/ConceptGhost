> **MANDATORY PRIVATE REFERENCE POLICY (2026-09-25)**  
> Before acting on this roadmap/policy document, consult `G:\\My Drive\\ConceptGhost\\Drones\\00_PRIVATE_AUTHOR_REFERENCE_SOURCE_OF_TRUTH_DO_NOT_GITHUB`. The purchased/original reference files remain Google Drive only and must **not** be copied to GitHub or release bundles. Concept Art + accepted P9 camera/source authority remain the product authority. Current gate progression follows the result-first reset in `61_RESULT_FIRST_ROADMAP_RESET_PRIVATE_REFERENCE_POLICY.md`.

# P10-Lab Subgate Board

## R6 Route Editor refinement — 2026-09-24

- Validation policy: no intermediate target-PC validation; first user validation is R6F.
- R6A Points/Mesh LOD + Point Size — COMPLETE / CI PASS.
- R6B Selected Camera View + frustum — COMPLETE / CI PASS.
- R6C Per-waypoint camera pose + SPIN_360 pitch/yaw — COMPLETE / CI PASS.
- R6D Perspective pivot/gimbal + orbit correction — COMPLETE / CI PASS.
- R6E portable route schema v0.2 + TXT/CSV orientation export/import — COMPLETE / CI PASS.
- R6F aggregate regression + final Evaluation_Builds bundle — ACTIVE.


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

Total: **67 required bounded subgates**, plus the optional non-blocking Gate 7.2C confidence overlay.

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


### Gate 4R — Artist Drone Route Authoring refinement — ACTIVE

The automatic Gate 4 planner is no longer intended to remain the final route authority for production P10. Long, curved and vertically changing environments make a generic automatic path insufficiently controllable. A bounded 10-subgate refinement is now authoritative in `docs/14_ARTIST_DRONE_ROUTE_AUTHORING_PLAN.md`.

Current state:
- DR0 planning/authority contract — COMPLETED;
- DR1 route data model/sampling — COMPLETED;
- DR2 synchronized TOP/SIDE/FRONT backend — COMPLETED;
- DR3 interactive ComfyUI editor — IMPLEMENTED, CI/runtime validation active;
- DR4 multi-drone PATH/SPIN_360 UX — backend implemented, frontend controls implemented, runtime validation pending;
- DR5 hold-last-safe-and-resume collision policy — backend prototype implemented;
- DR6 Gate 4→5→6 authored-route integration — COMPLETED in code/CI; user runtime acceptance deferred to DR9;
- DR7 persistence/hash-safe resume — COMPLETED at code/CI level; user save/reload runtime acceptance deferred to DR9;
- DR8 diagnostics/tests — ACTIVE / partially implemented;
- DR9 packaged user acceptance — pending.

Production direction:
- 1–7 artist-controlled drones;
- shared global capture settings;
- each drone can be a waypoint PATH or fixed-position SPIN_360;
- TOP edits Right/Forward, SIDE edits Forward/Up, FRONT edits Right/Up;
- all views edit the same 3D waypoint;
- automatic planning becomes editable seed/fallback only;
- collision policy prevents emitted frames from simply crossing known P9 geometry.

Gate 6 first-pass runtime acceptance remains valid. Gate 4R improves the evidence-camera authoring feeding Gate 5/Gate 6 and does not reopen the Gate 6 calibration fix.


### Gate 4R DR6 checkpoint — authored route identity through Gate 6

DR6 is complete at code/CI level.

The route chain is now explicit and regression-tested:
`P10DroneRouteAuthoring → P10RefinedEvidence → P10WanSequentialSampler → P10ReconstructionRuntime`.

Authority/identity guarantees:
- Gate 4 control + camera manifests use v0.2 route metadata;
- exact mission order/modes/frame counts are preserved;
- WAN tensor count/dimensions must equal the serialized Gate 4 control contract;
- WAN cannot silently drop authored frames;
- split WAN windows retain original `mission_name`;
- Gate 6 requires matching route authority, route SHA-256 and mission order between WAN and camera manifests;
- COLMAP dataset records the same route identity while camera pose authority remains P9-derived;
- untouched route-editor seed is tagged `EDITABLE_SEED`; artist interaction promotes it to `ARTIST_AUTHORED`.

GitHub Actions run 35811855641 completed SUCCESS across Ubuntu Python 3.12, Windows Python 3.12 and Windows Python 3.14.


### Gate 4R DR7 checkpoint — deterministic route persistence

DR7 is complete at code/CI level.

Persistence/resume contract:
- route editor state is serialized in the workflow and bound to the exact P9 source `scene_contract_id` and `source_run_id`;
- deterministic `route_plan_sha256` covers the route, binding and authority;
- artist edits clear the stale hash and mark the plan dirty; execution rebinds the current bytes;
- cross-scene/cross-run artist-route reuse fails closed;
- `Resetar cena` is the explicit escape hatch for discarding old authored state;
- Gate 4 persists the current bound route beside control/camera manifests;
- stale Gate 4 frames/masks are removed before a replacement sequence is written;
- Gate 5 verifies the persisted route file and clears stale WAN outputs before regeneration;
- Gate 6 checkpoint reuse validates WAN/camera manifest digests plus exact composite-image digests;
- source composite mutation or deletion invalidates the Gate 6 dataset instead of reusing stale sparse/dense/mesh state.

CI evidence: `35813649004` SUCCESS on `02c72585a312e26fda011e128e27dd9eae4f1cc2`.

Next: DR8 diagnostics / quality controls / regression closeout.


### Gate 4R DR8A checkpoint — pre-WAN route diagnostics

DR8A is COMPLETE / CI PASS.

Before WAN generation the P10 Gate 4 output now persists:
`diagnostics/drone_route_diagnostics.json`

Schema:
`ConceptGhost.P10DroneRouteDiagnostics.v0.1`

Per mission it records:
- PATH / SPIN_360 / AUTO mode;
- authored route length and emitted translation length;
- expected/emitted frame count;
- held/resumed frame counts and held fraction;
- minimum candidate/output clearance;
- min/mean/max P9 coverage;
- min/mean/max hole fraction;
- PASS / WARN / FAIL plus machine-readable alerts.

Global diagnostics record:
- exact mission order;
- active drone count;
- total emitted/held frames;
- route authority/hash and source scene/run;
- deterministic status policy.

CI evidence: `35816433877` SUCCESS on `efb7a39b0a53c2035ab8ae58ca34a26c339ea92a`.

Next: DR8B — one final-composite GIF per drone.


### Gate 4R DR8B checkpoint — per-drone final-composite GIF previews

DR8B is COMPLETE / CI PASS.

Gate 5 now generates exactly one looping animated GIF per authored drone/mission from **final composite** frames.

Contract:
- all frames belonging to the mission are included;
- a mission split into multiple WAN windows is reconstructed by original global frame index;
- duplicate, missing, cross-mission or out-of-range frames fail closed;
- 640 px maximum width, preserved aspect ratio, 10 fps, infinite loop;
- Windows-safe filenames;
- output root: `p10_gate5/<run_id>/drone_previews/`;
- each preview records GIF SHA-256 and ordered source-frame-set SHA-256;
- `drone_preview_index.json` is emitted alongside the GIFs;
- Gate 5 diagnostics surface preview count, index path and individual preview metadata.

CI evidence: `35816862522` SUCCESS on `6c9931c63ed18ad3d6c3ad97b59175b44a4bad22`.

Next: DR8C — formal preview index/output surfacing contract.


### Gate 4R DR8C checkpoint — preview index and output surfacing

DR8C is COMPLETE / CI PASS.

The per-drone preview package now has a formal output contract:
`ConceptGhost.P10DronePreviewIndex.v0.2`

Index identity:
- run ID;
- scene contract ID;
- source run ID;
- route-plan SHA-256;
- source control-manifest SHA-256;
- WAN generation-context SHA-256;
- exact mission order/modes.

Per preview:
- drone index + mission name/mode;
- exact global frame range/count;
- GIF fps/dimensions;
- ordered source-frame-set SHA-256;
- GIF SHA-256;
- Windows-safe filename;
- portable ComfyUI output subfolder plus absolute path.

Validation fails closed when GIF bytes, mission order/mode, frame count, route identity, control evidence or WAN generation context do not match.

Surfacing:
- WAN manifest stores preview-index path + SHA-256;
- Gate 5 diagnostics expose the preview package;
- WAN node has a new fifth output `drone_preview_index_path`;
- existing outputs 0–3 keep their slot numbers;
- per-drone GIFs are surfaced through standard ComfyUI output-image metadata.

CI:
- `35817184829` SUCCESS — formal index validation;
- `35817189070` SUCCESS — Gate 5 workflow/output surfacing.

Next: DR8D — preview invalidation / freshness.


### Gate 4R DR8D checkpoint — preview invalidation and freshness

DR8D is COMPLETE / CI PASS.

Preview authority now follows:
`route hash + control-manifest hash + WAN generation-context hash + exact final-composite bytes`.

Before regeneration, the prior preview package is classified with a machine-readable invalidation reason. The prior index SHA-256 is checked against the prior WAN manifest when route/control/settings are otherwise unchanged.

During regeneration:
- old `drone_previews` contents are removed before new publication;
- no old `drone_preview_index.json` survives a failed/new run as current authority;
- new GIFs are validated against their recorded GIF hashes;
- final composite frames are reassembled again and hashed after preview generation;
- source-frame-set hashes must still match the exact current composite bytes.

Therefore route changes, control changes, WAN-setting changes, preview-index tampering, GIF tampering and post-generation composite mutation all invalidate preview authority instead of silently presenting stale previews.

CI:
- `35817845135` SUCCESS — implementation;
- `35817871526` SUCCESS — invalidation/freshness regressions.

Next: DR8E — final diagnostics/GIF/index/workflow regression closeout.


### Gate 4R DR8E checkpoint — final regression closeout

DR8E is COMPLETE / CI PASS. DR8 is now complete at code/CI level.

Dedicated aggregate regression:
`tests/test_dr8_closeout.py`

Explicit GitHub Actions step:
`Validate DR8 route-authoring closeout regressions`

The closeout locks:
- Baseline/P9 input workflow remains unmodified;
- Baseline export node remains unchanged in the patched workflow;
- P10-only High Fidelity Split Clean default;
- artist route → Gate 4 → WAN → Gate 6 wiring;
- PATH + SPIN_360 two-drone identity and exact sampling;
- scene/run-bound route hashes and cross-run fail-closed behavior;
- route diagnostics PASS/WARN semantics;
- multi-window same-drone frame reconstruction;
- multi-drone separation;
- preview index/GIF/source-composite freshness;
- frontend add/remove drone, SPIN_360, reset, dirty hash and blocked-route UI contracts.

CI run `35818321869`:
- Ubuntu / Python 3.12 — SUCCESS
- Windows / Python 3.12 — SUCCESS
- Windows / Python 3.14 — SUCCESS

Formal matrix:
`docs/15_DR8_FINAL_REGRESSION_CLOSEOUT.md`

Next: DR9 — complete installer/workflow package + real ComfyUI runtime acceptance.


## Gate 5 — 5 subgates

5.1 11 GB WAN runtime/resource policy — COMPLETED. Conservative first-pass profile: 832×480, max 33-frame WAN window, 4 steps, CFG 1.0, FP8 UNet, one window at a time, model/cache offload between windows. GitHub Actions run 35702692128 SUCCESS.
5.2 Masked-video conditioning adapter — COMPLETED. ConceptGhost-native WAN I2V masked-video conditioning uses the full geometry control sequence; white mask means generate/hole and black means known/P9. GitHub Actions run 35702777990 SUCCESS.
5.3 Sequential per-flight WAN completion + checkpoints — COMPLETED. A single data-driven sampler groups frames by mission, splits into sequential windows, pads temporal lengths to WAN's 4k+1 convention (for example 31→33) without changing the real route, saves raw WAN outputs, and unloads between windows. GitHub Actions run 35703621997 SUCCESS.
5.4 Source-preserving high-resolution composite — COMPLETED FOR FIRST END-TO-END PASS. Known control/P9 pixels are restored exactly after WAN sampling; WAN contributes only where the binary hole mask is white. A heavier SplatKit-style high-resolution coordinate-field composite remains eligible for later texture-quality refinement, but does not block end-to-end development.
5.5 Generated/composite Preview and runtime validation — PREVIEW READY / USER RUNTIME PENDING. Full ConceptGhost Master Refined workflow patch is implemented and CI-green (run 35703771287). WAN model asset manifest/hashes are locked and CI-green (run 35703927155). User-test artifact: ConceptGhost_v1.54_P10_Gate05_REFINED_WAN_COMPLETE_INSTALLER_r1.zip. The installer automatically verifies/downloads the four required WAN assets (~24 GB total) instead of bundling them in the ZIP.

## Gate 6 — 6 subgates

6.1 Generated-view collection and camera manifest — COMPLETED. The Refined evidence stage now persists a Scene-Contract-bound per-frame PINHOLE camera manifest, and Gate 6 pairs every source-preserved Gate 5 composite with the exact planned P9-world camera using global frame index as the join key. GitHub Actions run 35746991214 SUCCESS.
6.2 Reconstruction dataset adapter — COMPLETED. The primary path is now known-camera COLMAP because ConceptGhost already owns authoritative P9-derived drone poses. The adapter materializes source-preserved Gate 5 composites into `images/`, writes a deterministic `sparse/known/` COLMAP text model, preserves Scene Contract/provenance, deduplicates identical intrinsics, and explicitly converts ConceptGhost/Maya camera axes (+X right, +Y up, -Z forward) into COLMAP axes (+X right, +Y down, +Z forward). SphereSfM remains optional ERP validation/fallback rather than the primary pose solver for perspective P10 composites. GitHub Actions run 35748183037 SUCCESS.
6.3 Known-camera feature matching + sparse point triangulation (with SphereSfM optional validation path) — IMPLEMENTED / RUNTIME HOTFIX VALIDATION ACTIVE. Gate 6.3 performs per-intrinsics feature extraction, adaptive matching (exhaustive for <=120 frames, sequential overlap 12 above that), fixed-pose point triangulation, and text conversion for sparse-cloud inspection. The current synchronization layer rebuilds the known COLMAP model with the database-assigned image/camera/rig/frame IDs before triangulation while preserving authoritative P9-derived qvec/tvec and using `refine_intrinsics=0`. After the r8 runtime exposed a second issue, Gate 6 now also maps the Gate 4 camera intrinsics into the exact saved Gate 5 WAN composite viewport (ComfyUI center-crop + resize) before COLMAP extraction, invalidates stale v0.1 reconstruction datasets on resume, and rebuilds `database.db` from scratch for each sparse retry so obsolete camera rows cannot survive a calibration change.
6.4 COLMAP dense stereo/fusion — COMPLETED FOR FIRST END-TO-END PATH; FREE-SPACE EVIDENCE PRODUCER CONTRACT RECORDED. The first-pass RTX 2080 Ti profile uses 832 max image size, 4 GB PatchMatch/Fusion caches, 3 PatchMatch iterations, geometric consistency, single GPU 0 and fusion min_num_pixels=2. The runner emits per-command logs, `dense_reconstruction_manifest.json`, `fused.ply`, exact fused vertex count, sampled bounds/shape diagnostics and `dense_fused_preview.svg`. For the Free-Space extension, this gate is also the producer/retention point for `dense/stereo/depth_maps/*.geometric.bin`, normal maps, `consistency_graphs/*.geometric.bin` and their exact known-camera identities. The explicit sparse ray-carving field is activated with Gate 7 implementation and does not reopen the already-completed first-pass Gate 6.4 as a blocker.
6.5 Dense cloud → pre-fusion triangle mesh + health checks — COMPLETED FOR FIRST END-TO-END PATH; DUAL-MESH EXTENSION RECORDED. The current proven first-pass Poisson mesher converts `dense/fused.ply` into the legacy `dense/pre_fusion_mesh.ply` with depth 10, trim 10, point_weight 1.0 and vertex color enabled, plus mesh-health diagnostics and three-view preview. When the Free-Space producer extension is activated with Gate 7, Gate 6.5 retains two explicit candidates: `dense/pre_fusion_mesh_poisson.ply` and `dense/pre_fusion_mesh_delaunay.ply`, plus `dense/free_space_meshing_comparison.json`. Poisson remains the smooth surface candidate; COLMAP Delaunay contributes visibility-aware structural evidence. Neither becomes automatic final authority by itself.
6.6 Reconstruction Preview and runtime validation — COMPLETED / USER RUNTIME PASS (r9). The full Refined Master now connects Gate 5 WAN/source-preserved composite outputs to a resumable Gate 6 known-camera reconstruction runtime. It reuses valid stage checkpoints, runs dataset→sparse→dense→Poisson mesh only where required, returns a live pre-fusion mesh preview in ComfyUI, and writes a reconstruction_runtime_manifest.json. COLMAP 4.2.0 CUDA is frozen as the required reconstruction runtime asset. GitHub Actions run 35752970504 SUCCESS. User-test package built and structurally validated: ConceptGhost_v1.54_P10_Gate06_REFINED_RECONSTRUCTION_COMPLETE_INSTALLER_r1.zip, 12,064,521 bytes, SHA-256 9ec7a63f0065cd10314ba0129877c4d24cc9bce69fdc44d1645208082720c4a2. Runtime acceptance remains pending.

### Gate 6 runtime correction — r8 camera/composite calibration

The r8 real-runtime failure at node `ConceptGhostP10ReconstructionRuntime` occurred before Gate 6.4, while Gate 6.3 was validating the COLMAP database cameras. Gate 4 camera manifests describe the pre-WAN control viewport, while Gate 5 saves composites after `common_upscale(..., crop="center")` at the WAN effective dimensions. Passing the pre-WAN intrinsics unchanged into COLMAP therefore produced a real width/height/intrinsics mismatch.

Current correction contract:
- transform fx/fy/cx/cy from the Gate 4 viewport into the exact Gate 5 saved-composite viewport using the same center-crop geometry and pixel-center-aware resize mapping;
- persist the transform/provenance in reconstruction inputs and dataset manifest v0.2;
- hash the WAN and camera manifests and invalidate stale dataset checkpoints when either input changes;
- treat old v0.1 dataset manifests as stale;
- rebuild the Gate-6-owned COLMAP `database.db` from scratch on every sparse retry;
- keep P9-derived camera pose authority unchanged;
- keep `refine_intrinsics=0`;
- fail closed with explicit expected-vs-database calibration diagnostics if parity still diverges.

This correction is independent of the new Free-Space policy. Free-Space starts consuming Gate 6.4/6.5 evidence only after a valid known-camera reconstruction exists.

### Gate 6.6 r9 runtime acceptance

Runtime evidence on 2026-09-23:
- official source run: `20260923T001018_212752Z_21246d71`;
- source/export structural status: PASS;
- P10 WAN/source-preserving composite completed;
- corrected known-camera sparse reconstruction completed;
- COLMAP dense stereo/fusion completed;
- pre-fusion meshing completed;
- `P10 LIVE · RECONSTRUCTED PRE-FUSION MESH` rendered successfully.

Important quality qualifier: the source P9 run was `Fast Test / Low Resolution`, so this closes Gate 6 as an execution/contract milestone, not as final-quality geometry approval.

Preview-only issue: some downstream core `PreviewImage` panels may remain blank because they are temp/cache UI consumers. They are not in the authoritative data path. Compact persistent diagnostics are now emitted by the P10 evidence node so observability does not depend on those temp panels.

Release-facing P10 default is now `High Fidelity Split Clean`.

## Gate 7 — 6 required subgates + optional 7.2C overlay

7.1 P10 reconstruction → P9 coordinate registration — **SOURCE COMPLETE / CI PASS**.
7.2 Authority-aware provenance/fusion evidence — **SOURCE COMPLETE / CI PASS**.
   - **7.2C confidence diagnostics:** **SOURCE COMPLETE / CI PASS**. HIGH=blue and LOW/VERY_LOW=red visual evidence is mandatory; confidence refinement remains DEFAULT OFF.
7.3 Free-space / visibility no-fill authority — **SOURCE COMPLETE / CI PASS**. CONFIRMED_FREE is no-fill/no-bridge; UNKNOWN is never FREE; Delaunay remains structural evidence beside Poisson.
7.4 Protected additive fusion candidate — **SOURCE COMPLETE / CI PASS**. P9 remains unchanged; only supported P10 candidate faces are admitted.
7.5 Registration/provenance visual review — **SOURCE COMPLETE / CI PASS**. Perspective + Top + Front + Side with P9/P10/provenance/free-space/camera context.
7.6 Gate 7 closeout / visual-evidence completeness — **SOURCE COMPLETE / CI PASS**. Requires one terminal preview and one comparison branch per subgate and fails closed before Gate 8 without runtime/artist approval.

**Mandatory visual evidence rule:** every meaningful gate must expose a terminal state preview plus a BEFORE/AFTER or REFERENCE/RESULT comparison. Same-camera drone replay is preferred when a camera sequence exists. Full contract: `docs/32_VISUAL_EVIDENCE_COMPARISON_CONTRACT.md`.

**Runtime status:** Gate 7 source is complete, but Gate 8 remains blocked pending DR9R r15 UX acceptance, Gate 7 Preview packaging/runtime execution and artist visual approval.

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

8.1 Defect analysis and bounded repair regions. **SOURCE/CI COMPLETE; TARGET-RUNTIME PROMOTION BLOCKED BY GATE 7 ACCEPTANCE.**
   - Implemented `p10_lab/gate8_defect_analysis.py` with the frozen taxonomy: `VALID_OPENING`, `FALSE_SURFACE_IN_CONFIRMED_FREE`, `MISSING_SURFACE_UNKNOWN`, `LOW_CONFIDENCE_SURFACE`, `CONFLICT_REGION`, `SUPPORTED_SURFACE`.
   - Consumes Gate 7.4 protected-fusion reasons, Gate 7.3 FREE/UNKNOWN/CONFLICT and Gate 7.2C virtual-hole confidence evidence.
   - Produces bounded face/voxel regions and NPZ evidence without moving/removing faces; `automatic_geometry_edit_allowed=false`.
   - CONFIRMED_FREE remains no-fill authority; UNKNOWN is never reinterpreted as FREE; CONFLICT never authorizes automatic edits.
   - Unit/regression coverage: `tests/test_gate8_defect_analysis.py`.
   - Next source-only work: G8.2 local remesh/cleanup safety contract + structural-analysis preview (analysis ON, apply OFF).
8.2 Local remesh / cleanup / optional hard-surface structural regularization.
   - **Structural Analysis + Preview is ON by default; geometry application is OFF by default.** The pipeline detects planar/sharp/parallel/orthogonal/coplanar/repeated-offset and soft-symmetry candidates, shows an always-available ComfyUI 3D impact map, and may build a regularized candidate without changing official geometry.
   - Artist switch: `Apply Structural Regularization = OFF / ON`. OFF passes the standard Gate 8 mesh downstream unchanged; ON promotes only safety-approved local edits.
   - Safety inputs: original-source camera/reprojection, Gate 7.2C confidence, Gate 7.3 CONFIRMED_FREE/UNKNOWN/CONFLICT, Gate 8.1 defect regions, provenance and multi-view geometry support.
   - Tooling plan: isolated Open3D-based planar analysis + native ConceptGhost bounded constraint solver; optional OpenCV source-line evidence; CGAL remains an optional validation/reference path rather than a required first-pass dependency.
   - Full policy and HS-1..HS-13 internal steps: `docs/13_HARD_SURFACE_STRUCTURAL_REGULARIZATION_POLICY.md`.
8.3 UV preservation/recovery.
8.4 Texture recovery with texel provenance.
8.5 Cleanup/texture Preview and runtime validation. A/B evidence must report standard vs structural candidate when the Gate 8.2 feature is evaluated.

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

## Cross-cutting workflow Notes contract

Every meaningful P10 node or visual node group in the shipped Refined workflow must include a visible explanatory note. Notes are part of the operator UX and must not exist only in source-code comments.

Minimum note content:
- Purpose;
- Inputs;
- What it does;
- Outputs;
- Authority level (diagnostic / candidate / official);
- Whether geometry is modified;
- Default switch state where applicable;
- Failure/fallback behavior;
- TEMP/retention behavior;
- Next downstream stage.

Group titles should include the Gate/Subgate identifier. Existing P10 lanes are backfilled during Gate 12 observability cleanup; every new group added from this point forward must ship with its note immediately.

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


## DR9R active correction block — 2026-09-23

P9 is now explicitly treated as accepted upstream authority. Its current depth span/shell structure is not a DR9R correction target; P10 must work from that P9 world.

DR9R-A is COMPLETE / CI PASS.

DR9R-B is ACTIVE and is decomposed into:
- B1 4-view Perspective + TOP/SIDE/FRONT route workspace;
- B2 LOOK_AT_TARGET / LOOK_ALONG_PATH / MANUAL_DIRECTION orientation authority + frustums;
- B3 P9-only known-camera reconstruction round-trip audit;
- B4 per-drone/multi-mission reconstruction preservation and dropped-frame diagnostics;
- B5 metric P9/P10 sparse/dense/mesh/camera overlay;
- B6 geometry-quality PASS/WARN/FAIL authority.

Then:
- DR9R-C explicit P9 Route Setup → P10 Production handoff;
- DR9R-D immutable p10_attempt_id output directories;
- DR9R-E one complete runtime regression/user-test bundle.

The user requested **no intermediate runtime test**. Each partial subgate must nevertheless be saved to GitHub and a Google Drive recovery checkpoint before continuing.


### DR9R-B progress checkpoint — 2026-09-23

- DR9R-B1 — COMPLETE / CI PASS: four-view Perspective + TOP/SIDE/FRONT route workspace, shared P9 geometry, metric-isotropic ortho editing, orbit/zoom inspection.
- DR9R-B2 — COMPLETE / CI PASS: explicit LOOK_AT_TARGET / LOOK_ALONG_PATH / MANUAL_DIRECTION authority, target/manual controls, visible aim cues, orientation-safe collision holds, v0.1 route/hash compatibility.
- DR9R-B3 — NEXT: P9-only known-camera reconstruction round-trip audit.
- DR9R-B4 — PLANNED: multi-mission/per-drone reconstruction preservation.
- DR9R-B5 — PLANNED: metric P9/P10 reconstruction overlay.
- DR9R-B6 — PLANNED: Gate 6 geometry-quality authority.

No user runtime test is requested until DR9R-E after B1-B6/C/D are complete.


### DR9R C/D closeout — 2026-09-23

- DR9R-C — COMPLETE / CI PASS: explicit P9 Route Setup → committed production entry → standalone P10 Production handoff; Stage A stops before WAN/Gate6 and Stage B contains no P9 solver dependency.
- DR9R-D — COMPLETE / CI PASS: unique immutable p10_attempt_id per Production queue; Gate4/Gate5/Gate6 share one attempt root; previous attempts are preserved; LATEST_P10_RUN is pointer-only; cross-attempt manifest mixing fails closed.
- DR9R-E — ACTIVE: aggregate closeout regression + final two-workflow installer + one deferred user runtime acceptance pass.


### DR9R-E final package published — 2026-09-23

- DR9R-B1..B6 — COMPLETE / CI PASS.
- DR9R-C — COMPLETE / CI PASS.
- DR9R-D — COMPLETE / CI PASS.
- DR9R-E package build — COMPLETE.
- Final bundle: `ConceptGhost_v1.54_P10_DR9R_COMPLETE_TWO_STAGE_INSTALLER_r5.zip`.
- SHA-256: `63ec487e3a73e98018cb72d5d27472ada3e33ccbd450ebf964028e558420be1d`.
- Google Drive Evaluation_Builds file id: `1qr3iAHlRRlgRHsqRF1zwULlfNikhTwyH`.
- GitHub Release: tag `p10-dr9r-r5`.
- User runtime acceptance — PENDING.
- Required final flow: Route Setup queue #1 -> edit route -> Route Setup queue #2 commit -> P10 Production queue #1.
- Gate 7 remains blocked until this final user runtime evidence is accepted.


### DR9R-E r6 final user-test package — 2026-09-23

- Status: READY FOR USER RUNTIME ACCEPTANCE.
- One ZIP only: `ConceptGhost_v1.54_P10_DR9R_COMPLETE_TWO_STAGE_INSTALLER_r6.zip`.
- Two installed workflows: ROUTE_SETUP_r6 and PRODUCTION_r6.
- Queue sequence: Route Setup #1 -> artist edit -> Route Setup #2 commit -> Production #1.
- Production defaults to AUTO_LATEST and writes each attempt to a unique immutable p10_attempt_id directory.
- Final package static audit fixed the PowerShell workflow-path join and verifier Python syntax before publishing.
- 256 source tests PASS; final bundle test PASS; verifier PASS; extracted hashes PASS.
- ZIP SHA-256: `be3e3fc5ef84f404a41cd7177b16a5aa9331ba0420c6013397a4f641413226d5`.
- Runtime acceptance on the user's ComfyUI PC is the only remaining DR9R-E acceptance item.


### DR9R-F active — 2026-09-23

Runtime acceptance of r6 is reopened by first real Route Setup UX findings. Gate 7 remains blocked.

- F1 numbered workflow order + embedded Run #1/#2/#3 instructions.
- F2 reset-safe dynamic four-view workspace; zoom/pan all views; no frozen Perspective duplicate; route visibility guard.
- F3 explicit storage lifecycle + safe P10-only cleanup.
- F4 AUTO_LATEST resolved-path observability.
- F5 P9 persisted-dependency closure audit for all future P10 gates.
- F6 dual Maya deliverable contract: preserve P9 .ma; later create separate P10 Refined .ma.
- F7 current-only install: no legacy Master v1.53 in user workflow folder.
- F8 aggregate regressions + replacement bundle.

No intermediate user runtime test. Save each subgate checkpoint to GitHub and Google Drive.


### DR9R-F r7 published — 2026-09-23

- F1 numbered 01/02 workflows + embedded Run instructions — COMPLETE.
- F2 reset-safe dynamic four-view workspace + all-view zoom/axis-locked pan + visibility guard — COMPLETE / runtime pending.
- F3 explicit P10 storage lifecycle + safe cleanup tool — COMPLETE for current P10; final automatic disposable cleanup remains tied to final P10 closeout.
- F4 AUTO_LATEST resolved-path observability — COMPLETE.
- F5 persisted P9 dependency inventory / critical hash validation — COMPLETE; future gates fail closed on missing persisted evidence.
- F6 dual Maya non-overwrite contract — IMPLEMENTED; actual P10 refined Maya export remains in the later Maya/export gate.
- F7 current-only user workflow installation — COMPLETE in r7.
- F8 static regression/package acceptance — COMPLETE.
- Final package: `ConceptGhost_v1.54_P10_DR9R_COMPLETE_TWO_STAGE_INSTALLER_r7.zip`
- SHA-256: `0e38a75b5b4736a6b09e99fcfe71f3a361cf03946ac0bed0ef47eed889d8f756`
- Google Drive file id: `1hAp4qqbCVxUyHLXrKuWQUPHERLcFNFWR`
- GitHub release: `p10-dr9r-r7`
- User runtime acceptance: PENDING. Gate 7 remains blocked until r7 is reviewed.


### DR9R-F9 MoGe diagnostics — 2026-09-23

- Status: IMPLEMENTED / CI PASS / r8 PACKAGE PUBLISHED.
- Workflow 01 contains `P9 · MoGe Depth Diagnostics · OPTIONAL · OFF BY DEFAULT`.
- OFF writes no diagnostic folder and does not change official P9/P10 output.
- ON produces native/raw + derived depth inspection evidence in a separate retained diagnostic directory.
- Diagnostic branch is fail-open and has no geometry authority.
- r8 package SHA-256: `9774a887e397e18d9dcb76c65dea29ce4496ec95f0fa75570b400238dad0139c`.
- User runtime inspection remains pending.


### DR9R r9 installer hotfix published — 2026-09-23

- Status: PACKAGE PUBLISHED / CI PASS / USER RUNTIME ACCEPTANCE PENDING.
- Final bundle: `ConceptGhost_v1.54_P10_DR9R_MOGE_DIAGNOSTICS_TWO_STAGE_INSTALLER_r9.zip`.
- SHA-256: `1143e94e0fcbfcf25809efa0a21fae162fa79079c3223b8ea2eec677069609bf`.
- Google Drive file id: `1YUTpjOJzAIwYJwhgk87f8Dr-WONzwo7T`.
- GitHub release: `p10-dr9r-r9`.
- Final branch head: `9fa358c7ad7078b4f7bfa4e2e181848daf37cf2b`.
- Tests run `35906865640`: SUCCESS.
- Source snapshot run `35906865630`: SUCCESS.
- r9 supersedes r8 for target-PC testing.
- Gate 7 remains blocked pending user runtime acceptance.


## 2026-09-25 — Runtime-validation refinement queue

- **Current official acceptance boundary:** Gate 7 / R6F target-PC P9+P10 validation.
- **R6G — Route Editor Visual Quality & Layout:** SOURCE/CI COMPLETE; target-PC visual acceptance pending. Corrected implementation commit `1f20901413e1c8169dabe079eb1b043a9f486de2`; ConceptGhost Tests `36169054232` SUCCESS; Source Snapshot `36169053996` SUCCESS.
- **R6H — Gate 6 Live Progress & Streaming Logs:** NEXT PLANNED after R6G. Observability-only; no camera, geometry, WAN, COLMAP-quality or Gate-7 authority changes.
- **Gate 8.1 — Defect Analysis:** SOURCE/CI COMPLETE in parallel, but runtime promotion remains blocked behind Gate 7 acceptance.
- **Gate 8.2+:** not promoted until the Gate 7 runtime boundary and queued R6 refinements are reconciled.

### Gate 7 R6F15 target-PC correction — COLMAP auto-discovery

R6F14 target-PC runtime reached Gate 7.3 and failed only when the Delaunay
visibility branch tried to launch the bare executable token `colmap`. Gate 6
had already used the ConceptGhost private COLMAP runtime successfully, so this
was an executable-resolution handoff defect rather than a missing COLMAP
installation or geometry failure.

R6F15 fixes the handoff by reusing the Gate 6 COLMAP resolver for every Gate 7
native call, preferring the exact executable recorded in the dense manifest and
treating blank/`colmap` as AUTO. The Delaunay call now resolves before
`subprocess.run`; the preview node no longer forces an empty field to the
bare token.

Regression: `tests/test_gate7_colmap_resolution.py`.
ConceptGhost Tests run `36178840378`: SUCCESS.
R6F15 hotfix package build run `36178840498`: SUCCESS.

Target-PC recovery is intentionally in-place: the Evaluation_Builds hotfix
`ConceptGhost_R6F15_COLMAP_AUTODISCOVERY_HOTFIX_r2.zip` patches only the two
installed P10 Lab source files and includes `03_RESUME_LAST_GATE7.bat` to
resume the latest existing failed Gate 7 attempt without creating a new
Production attempt or regenerating WAN/Gate 6.

Target-PC resume result: **PASS** on existing attempt
`20260925T182415_329568Z_a99e3910_7d5df9fe`.
The recovery completed G7.3 Delaunay comparison, G7.4 protected fusion,
G7.5 visual-review artifact generation, and automatic run-local audit without
regenerating WAN/Gate 6 and without creating a new Production attempt.

Gate 7 runtime acceptance is now **PASS**. Gate 7 remains OPEN only for
artist visual acceptance of the G7.5 review/protected-fusion result.
Gate 8 runtime promotion remains blocked until that visual acceptance is recorded.

### Gate 7 target-PC quality finding — zero P10 contribution

R6F15 runtime recovery completed successfully, but artist-quality acceptance is
**NOT accepted** for the target scene.

The protected-fusion candidate contains:
- P9 faces: 2,665,370
- P10 input faces: 21,089
- P10 accepted faces: **0**
- P10 rejected faces: 21,089
- P10 candidate vertices added: **0**

Rejections:
- P9_SOURCE_PROTECTED_OVERLAP: 16,090
- FREE_SPACE_CONFLICT: 4,379
- CONFIRMED_FREE_VETO: 620

Gate 7.2 sampled 6,092 P10 vertices and classified 100% as P9_RETAINED;
P10_MULTIVIEW_SUPPORTED = 0.

Therefore:
- Gate 7 runtime = PASS;
- Gate 7 completion effectiveness = FAIL;
- Gate 7 artist quality acceptance = NOT ACCEPTED;
- Gate 8 runtime promotion remains BLOCKED.

Mainline priority changes from immediate Gate 8 promotion to proving a
measurable, spatially meaningful P10 novel-surface contribution first.
R6H remains safe parallel observability work.

Future run-side audit outputs must place RUN_TECHNICAL_SUMMARY.json,
RUN_TECHNICAL_SUMMARY.txt and RUN_GATE7_VISUAL_REVIEW.png beside
RUN_AUDIT_BUNDLE.zip when available.



### R6I — Gate 6 reopened for functional geometry proof — 2026-09-25

User acceptance decision: Gate 6 is **REOPENED**.

The Gate contract is authoritative: Gate 6 must produce a new 3D reconstruction
from the Gate 5 drone/WAN images and expose that geometry directly before Gate 7
filters or combines it with P9.

The 20260925 target run did create a pre-fusion P10 mesh (12,184 vertices /
21,089 faces), but Gate 6 did not expose it clearly enough as its own immutable
deliverable and Gate 7 later accepted zero P10 faces. Therefore runtime success
does not constitute Gate 6 functional acceptance.

R6I implements:
- explicit `GATE6_RAW_P10_GEOMETRY.ply`;
- explicit `GATE6_RAW_P10_GEOMETRY.obj`;
- explicit `GATE6_DENSE_POINTS.ply`;
- `GATE6_OUTPUT_MANIFEST.json` + README;
- compact `<P9_RUN>/P10_GATE6_OUTPUT/<attempt_id>/` sidecar near the run audit bundle;
- Gate 6 fail-closed contract when the new raw mesh is missing/empty;
- Workflow 02 visual groups identifying Gate 4 / Gate 5 / Gate 6 and each gate output;
- resume helper that reuses the already-generated Gate 4 camera manifest and Gate 5 WAN images.

Current acceptance state:
- Gate 5: runtime output exists / remains upstream evidence;
- Gate 6 runtime path: implemented;
- Gate 6 **functional acceptance: OPEN / target-PC raw-geometry inspection required**;
- Gate 7 runtime: PASS, but functional/artist acceptance cannot close while Gate 6 remains open;
- Gate 8.1 source work remains valid but runtime promotion is BLOCKED;
- Gate 8.2 is NOT promoted.

Gate 6 is considered functionally accepted only after the artist can inspect a
non-empty raw P10 reconstruction independently of Gate 7 and we verify whether
it actually contributes useful geometry in the intended occluded regions.
