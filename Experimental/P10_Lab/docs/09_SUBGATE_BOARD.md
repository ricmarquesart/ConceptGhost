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
| 2. Completion Bundle and P9 identity boundary | 5 | 4 completed + 1 runtime confirmation pending |
| 3. Temporary panorama and completion envelope | 5 | 3.1-3.4 COMPLETED; 3.5 IMPLEMENTATION READY / RUNTIME PENDING |
| 4. Automatic paths, collision, raw controls and masks | 6 | 4.1 PREVIEW READY / USER RUNTIME PENDING; 4.2 IMPLEMENTED / CI GREEN |
| 5. WAN completion and source-preserving composite | 5 | PLANNED |
| 6. SphereSfM and COLMAP reconstruction | 6 | PLANNED |
| 7. Registration, fusion and provenance | 5 | PLANNED |
| 8. Geometry cleanup and texture recovery | 5 | PLANNED |
| 9. Original-view regression and Maya export | 5 | PLANNED |
| 10. Adaptive quality, hardware compliance and Refined integration | 6 | PLANNED |

Total: **52 bounded subgates**.

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
2.5 User runtime confirmation in real ComfyUI Desktop — PENDING USER TEST.

Gate 2 remains open until 2.5 passes.

## Gate 3 — 5 subgates

3.1 Canonical camera authority + panorama coordinate/math contract — COMPLETED.
Evidence: real v1.53 CameraBundle.v0.8 fixture; FOV recomputation; rigid
right-handed world-matrix validation; source↔ERP reversible ray math; strict
2:1 ERP contract; GitHub Actions run 35685846429 SUCCESS.
3.2 Perspective-to-equirectangular projection and source placement — COMPLETED.\nEvidence: seam-safe camera-local source footprint, reversible ERP sampling, half-pixel raster convention, orientation/no-flip tests and cross-platform CI.\n3.3 Source-lock mask + observed/unknown panorama map — COMPLETED.\nEvidence: exact observed/unknown complements, source authority lock, deterministic SHA-256 and cross-platform CI run 35686124075 SUCCESS.\n3.4 Bounded local completion envelope from authoritative scene/camera scale — COMPLETED.\nEvidence: flight-offset containment, rear/pole/world-scale rejection, unknown-only generation candidates and corrected cross-platform CI run 35686379285 SUCCESS.\n3.5 Gate 3 ComfyUI panorama preview + runtime validation — IMPLEMENTATION READY / RUNTIME PENDING.\nEvidence: registered IMAGE/MASK/MASK preview node, real v1.53 bundle rendered at 2048×1024, observed fraction ≈1.57%, candidate fraction ≈20.67%, PrimaryMesh characteristic radius ≈70.27 canonical units, direct ComfyUI temp-image UI support, and latest branch GitHub Actions run 35686851557 SUCCESS.

Gate 3 implementation may proceed through independent preparation while 2.5 is
pending, but Gate 3 cannot be promoted/closed until Gate 2 closes.

## Gate 4 — 6 subgates

4.1 Convert scene-relative flight definitions into authoritative world cameras — PREVIEW READY / USER RUNTIME PENDING. Geometry-aware planning measures the current PrimaryMesh footprint at runtime and produces entry/center micro-orbit 360 paths plus outbound/return full-scene traversals. The integrated Refined node generates ERP, source lock, flight views, raw holes, trajectory map and GIF during the same execution. Real v1.53 runtime smoke: PASS; adaptive per-pose renderer CI run 35690559474 SUCCESS. Complete Installer: ConceptGhost_v1.54_P10_Gate04_REFINED_COMPLETE_INSTALLER_r1.zip.\n4.2 Collision/clearance query contract and safe path adaptation — IMPLEMENTED / CI GREEN, runtime integration acceptance pending. GitHub Actions run 35688972654 SUCCESS.
4.3 P10-only raw-hole geometry derivative.
4.4 Geometry-control frame renderer.
4.5 Disocclusion/unsupported-region mask generator.
4.6 Per-flight control/mask Preview and runtime validation.

## Gate 5 — 5 subgates

5.1 11 GB WAN runtime/resource policy.
5.2 Masked-video conditioning adapter.
5.3 Sequential per-flight WAN completion + checkpoints.
5.4 Source-preserving high-resolution composite.
5.5 Generated/composite Preview and runtime validation.

## Gate 6 — 6 subgates

6.1 Generated-view collection and camera manifest.
6.2 SphereSfM dataset adapter.
6.3 SphereSfM camera/sparse reconstruction.
6.4 COLMAP dense stereo/fusion.
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
