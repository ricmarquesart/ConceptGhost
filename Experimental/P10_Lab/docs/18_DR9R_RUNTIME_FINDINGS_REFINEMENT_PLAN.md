# ConceptGhost P10 DR9R — Runtime Acceptance Findings and Refinement Plan

Date: 2026-09-23

## Runtime acceptance state

DR9 is **NOT accepted yet**. Corrective block DR9R remains active before Gate 7.

The next user runtime test is intentionally deferred until the complete DR9R improvement set below is implemented and internally checkpointed. Intermediate DR9R subgates are recovery/development checkpoints only and are not user-test releases.

## P9 authority lock — 2026-09-23

The current P9 result is accepted as the authoritative upstream scene for P10.

- P9 depth spread, disconnected shells and monocular geometry characteristics are **not P10 defects**.
- P10 must operate correctly on the P9 geometry exactly as delivered.
- DR9R must not reshape, compress, normalize, flatten or otherwise "fix" P9 merely to make P10 reconstruction easier.
- P9 remains the coordinate, camera, source-observation and known-geometry authority at the P10 handoff.
- P10 reconstruction quality is judged by whether generated/recovered evidence is coherent with that P9 world, not by whether P9 itself resembles a compact photogrammetry capture.

This decision supersedes any diagnostic suggestion that the existing P9 depth span should be corrected as part of DR9R.

## Confirmed runtime findings

1. The original 07R TOP/SIDE/FRONT route editor distorted scene proportions because each display axis was independently normalized. DR9R-A corrected the orthographic displays to metric-isotropic scaling.

2. The second fixed three-panel image below the editor was only the stale normal ComfyUI IMAGE preview from the previous execution. It was not a second route authority. DR9R-A removed the duplicate UI surface.

3. Artist route edits happen after the prompt that produced the map. Downstream nodes cannot consume edits retroactively in the same already-completed prompt. A deliberate P9 Route Setup → P10 Production handoff is required.

4. The second prompt did consume the artist-authored missions. P9/MoGe was cached; the waste is the first automatic P10 pass, not a second P9 solve.

5. P10 attempt outputs are not yet immutable per execution. Several output roots are keyed only by the parent P9 run id.

6. The current pre-fusion mesh proves runtime plumbing, not geometric acceptance. It is fragmented and must be re-evaluated only after the complete DR9R reconstruction hardening work is implemented.

7. PATH camera orientation currently follows the path tangent. Camera position can therefore be close to useful geometry while the optical axis looks away from the intended subject.

8. Gate 6 sparse reconstruction currently selects the largest verified image-match connected component. This can silently discard valid missions when separately generated drone sequences are not mutually feature-connected.

9. Existing Gate 6 PASS states mainly prove successful execution/file production. They do not yet prove sufficient sparse density, multi-mission contribution, dense coherence or P9-world agreement.

10. The Gate 6 pre-fusion preview itself uses independently normalized axes and therefore is not suitable for judging real metric proportions.

## Architecture decision

Do **not** author routes against a disposable low-fidelity proxy and then switch to a different P9 geometry for production.

Use the same authoritative P9 run for route setup and P10 production.

### Stage A — P9 Scene Solve + Route Setup

- Run P9 once with the intended authoritative geometry profile.
- Produce PrimaryMesh, camera, source/raw evidence and immutable P9 run_dir.
- Open the P10 route workspace from that completed P9 run.
- Stop before WAN and Gate 6.
- Artist edits and commits the P10 route.

### Stage B — P10 Production from Existing P9 Run

- Load the existing P9 run_dir without re-solving P9.
- Load the scene-bound committed route.
- Generate P10 evidence, WAN completion and reconstruction.
- Preserve access to P9 raw/official evidence for later registration/fusion.
- Create a unique P10 attempt identity for every production execution.

## DR9R corrective gates

### DR9R-A — Orthographic Accuracy + Duplicate Preview Cleanup
Status: **COMPLETE / CI PASS**

- one metric scale per TOP/SIDE/FRONT orthographic panel;
- sampled PrimaryMesh points use source-image colors when available;
- stale duplicate ComfyUI image preview removed;
- explicit next-Queue-Prompt guidance;
- route/collision math unchanged.

### DR9R-B — Route + Reconstruction Hardening
Status: **ACTIVE**

DR9R-B is decomposed into six bounded recovery checkpoints. No user runtime test is requested between them.

#### DR9R-B1 — 4-View Route Workspace
Status: **COMPLETE / CI PASS**

- one interactive Perspective/orbit viewport;
- fixed metric-isotropic TOP / SIDE / FRONT views;
- all four views share the exact same P9 geometry and route state;
- perspective is inspection/navigation first; authoritative position edits remain orthographic;
- route direction and camera/frustum visualization.

#### DR9R-B2 — Camera Orientation Authority
Status: **COMPLETE / CI PASS**

Add explicit per-mission orientation modes:
- LOOK_AT_TARGET — production default for PATH;
- LOOK_ALONG_PATH — preserves current tangent-follow behavior when explicitly selected;
- MANUAL_DIRECTION — explicit artist direction;
- SPIN_360 retains its rotating optical axis.

The route workspace must display the target/direction/frustum so camera position and camera aim cannot be confused.

#### DR9R-B3 — P9-Only Reconstruction Round-Trip Audit
Status: **COMPLETE / CI PASS / RUNTIME EVIDENCE DEFERRED**

Run a diagnostic reconstruction using P9-rendered camera views without WAN generation:
P9 PrimaryMesh → P10 known cameras → P9-only rendered frames → known-camera COLMAP → reconstructed cloud/mesh.

Purpose: isolate camera matrices, intrinsics, crop/resize mapping, ConceptGhost→COLMAP pose conversion and dense reconstruction from WAN consistency.

This is diagnostic only. P9 remains accepted authority regardless of the audit result.

#### DR9R-B4 — Multi-Mission / Per-Drone Reconstruction Audit
Status: **ACTIVE**

- stop treating only the largest match component as sufficient geometric evidence;
- report contribution and match connectivity per mission;
- preserve independently valid mission components in the common known P9 world;
- fail/warn when a mission is silently absent from sparse/dense reconstruction;
- expose used/dropped frame counts and reasons.

#### DR9R-B5 — Metric P9/P10 Reconstruction Overlay
Status: **PLANNED**

Add a metric-isotropic diagnostic surface showing:
- P9 authoritative geometry;
- P10 sparse cloud;
- P10 dense fused cloud;
- P10 pre-fusion mesh;
- camera centers/frustums;
- per-mission contribution/provenance.

Report P9 bounds, P10 bounds, camera bounds, connected components and P10→P9 distance statistics without treating P9 distance alone as a requirement for unseen surfaces.

#### DR9R-B6 — Gate 6 Geometry Quality Authority
Status: **PLANNED**

Replace execution-only PASS semantics with explicit geometry-quality status.

Required diagnostics include:
- sparse point count/density;
- selected and dropped frames per mission;
- number of contributing missions;
- dense fused point count;
- pre-fusion connected-component count;
- degenerate/invalid topology;
- camera/scene metric bounds;
- cross-view support;
- P9-only round-trip status;
- clear PASS / WARN / FAIL reasons.

Gate 6 file existence remains a runtime check, not geometry acceptance.

### DR9R-C — Explicit Two-Stage P9→P10 Handoff
Status: **PLANNED**

- Route Setup path stops before WAN/Gate 6.
- Commit route against scene_contract_id + P9 run_id.
- P10 Production loads the existing P9 run_dir + committed route.
- No second P9 solve is required.

### DR9R-D — Immutable P10 Attempt Directories
Status: **PLANNED**

- introduce p10_attempt_id independent from parent p9_run_id;
- every P10 production execution gets a unique attempt folder;
- retain parent_p9_run_id, scene_contract_id and route_plan_sha256;
- never overwrite previous P10 attempts;
- LATEST_P10_RUN is a pointer only.

### DR9R-E — Complete Runtime Regression + User Test Bundle
Status: **PLANNED / USER TEST DEFERRED**

Only after DR9R-B1..B6, DR9R-C and DR9R-D are complete:
- build one complete installer/workflow bundle;
- test curved/descending PATH + LOOK_AT_TARGET;
- test SPIN_360;
- confirm one GIF per authored mission;
- confirm WAN and Gate 6 consume the committed route;
- inspect P9-only audit, per-mission contribution and pre-fusion reconstruction;
- confirm unique attempt directories;
- only then ask for the next real ComfyUI user runtime test.

## Checkpoint policy during DR9R

After every bounded implementation subgate:
1. commit/synchronize source to GitHub;
2. save a recovery checkpoint to Google Drive;
3. record parent commit, changed files and subgate status;
4. do not publish it as a user-test release;
5. continue automatically to the next planned subgate unless a blocking implementation problem is discovered.

GitHub authority:
`Experimental/P10_Lab/docs/18_DR9R_RUNTIME_FINDINGS_REFINEMENT_PLAN.md`


### DR9R-B1 implementation checkpoint — 2026-09-23

- 2×2 workspace contract is implemented: interactive Perspective + metric-isotropic TOP/SIDE/FRONT.
- Perspective consumes the same P9-local sampled PrimaryMesh geometry/source color evidence as the orthographic workspace.
- Perspective orbit/zoom is inspection-only; waypoint coordinates remain authored in orthographic views.
- Backend/server preview and frontend now share the same isotropic panel extents.
- Route-direction arrows are visible.
- User runtime test remains intentionally deferred.

### DR9R-B2 implementation checkpoint — 2026-09-23

- Route schema v0.2 adds explicit camera orientation authority.
- PATH supports LOOK_AT_TARGET, LOOK_ALONG_PATH and MANUAL_DIRECTION.
- New route-editor seeds use LOOK_AT_TARGET toward the P9 scene center.
- Existing v0.1 routes remain readable and retain tangent-follow behavior until explicitly rebound.
- Existing v0.1 bound route hashes are verified without silently changing their digest.
- Target editing and manual yaw/pitch controls are exposed in the route editor.
- Camera aim cues are rendered in Perspective and all three orthographic views.
- Collision HOLD_AND_RESUME re-applies orientation after position holds so LOOK_AT_TARGET remains geometrically exact.
- Per-mission diagnostics now include orientation mode/target/direction without changing the DR8 diagnostics schema.
- GitHub CI passed after the B2 implementation fixes; final B2 checkpoint includes the legacy-hash preservation follow-up.
- User runtime test remains intentionally deferred.


### DR9R-B3 implementation checkpoint — 2026-09-23

- Gate-4 control and camera manifests now carry the immutable source P9 run directory.
- WAN propagates the same P9 run authority downstream.
- Added a dedicated P9-only known-camera COLMAP dataset path using Gate-4 P9-rendered control frames and zero WAN pixels.
- The P9-only audit runs before the WAN-composite reconstruction inside Gate 6, in an isolated `p9_roundtrip` subtree.
- Audit failures are non-blocking diagnostic evidence: they are persisted as FAIL evidence rather than silently aborting or modifying P9.
- Audit source inputs are hash-bound to control/camera manifests and can be reused only when the exact context matches.
- Unit/CI coverage validates dataset identity, camera mapping and WAN exclusion.
- Runtime geometric evidence from the audit is intentionally deferred until the final DR9R-E user test; implementation/CI is complete.
