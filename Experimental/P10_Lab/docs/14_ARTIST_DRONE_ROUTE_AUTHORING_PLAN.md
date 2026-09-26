> **MANDATORY PRIVATE REFERENCE POLICY (2026-09-25)**  
> Before acting on this roadmap/policy document, consult `G:\\My Drive\\ConceptGhost\\Drones\\00_PRIVATE_AUTHOR_REFERENCE_SOURCE_OF_TRUTH_DO_NOT_GITHUB`. The purchased/original reference files remain Google Drive only and must **not** be copied to GitHub or release bundles. Concept Art + accepted P9 camera/source authority remain the product authority. Current gate progression follows the result-first reset in `61_RESULT_FIRST_ROADMAP_RESET_PRIVATE_REFERENCE_POLICY.md`.

# P10 — Artist Drone Route Authoring — Implementation Plan

Status: ACTIVE
Created: 2026-09-23
Scope: replace automatic drone-route authority with artist-authored routes while preserving the current automatic planner only as an optional editable seed/fallback.

## Goal

After the P9/Refined scene exists, the artist must be able to inspect the current 3D scene in synchronized TOP / SIDE / FRONT orthographic views and author from 1 to 7 drone missions directly in ComfyUI.

Each mission supports:
- PATH: an editable 3D waypoint curve/path;
- SPIN_360: one anchor point with a full 360-degree yaw sweep;
- shared global capture settings such as frames per drone and image quality/resolution;
- collision protection so authored routes do not simply pass through the current scene geometry.

All three views edit the same 3D waypoint. TOP edits Right/Forward, SIDE edits Forward/Up, FRONT edits Right/Up.

## Project-control rule

This work is a P10 route-authoring refinement inserted before Gate 4 evidence generation and before WAN/COLMAP. It does not modify Baseline/P9 solver authority.

Gate 6 first-pass remains completed. The new route authoring improves the camera evidence supplied to the existing Gate 4 -> Gate 5 -> Gate 6 path; it does not reopen the Gate 6 calibration fix.

## 10 bounded subgates

### DR0 — Planning / authoritative contract — COMPLETED
- define manual route authority;
- 1–7 drones;
- PATH / SPIN_360;
- global frames/quality policy;
- TOP/SIDE/FRONT linked coordinate semantics;
- automatic planner demoted to seed/fallback;
- collision behavior defined as hold-last-safe-and-resume.

Exit: written architecture and compatibility boundary.

### DR1 — Route data model + sampling — COMPLETED
- ConceptGhost.P10DroneRoutePlan.v0.1;
- unique drone missions;
- exact waypoint serialization;
- PATH interpolation;
- SPIN_360 sampling;
- 1–7 drone validation;
- global frames_per_drone;
- min_clearance_m and collision-mode contract.

Exit: deterministic route plan roundtrip and sampler tests.

### DR2 — Tri-view scene projection backend — COMPLETED
- load authoritative P9 PrimaryMesh;
- transform it into P9 camera-local Right/Up/Forward coordinates;
- compute robust scene bounds;
- generate synchronized TOP / SIDE / FRONT projections;
- draw the same 3D route in all three views;
- avoid one square global scale so long scenes remain readable.

Exit: one route-preview image + projection manifest + tests.

### DR3 — Interactive ComfyUI route editor — IMPLEMENTED / CI PASS / USER RUNTIME PENDING
- custom DOM/canvas editor;
- click to create waypoint;
- drag existing waypoint;
- selection highlighting;
- edits in any panel update the same 3D point in all panels;
- delete selected point;
- undo / clear route;
- persist route plan back into the hidden serialized widget;
- consume backend route_editor execution metadata.

Exit: route can be authored without manually editing JSON.

### DR4 — Multi-drone UX + mission modes — IMPLEMENTED IN BACKEND + FRONTEND / USER RUNTIME PENDING
- Drone 1 present by default;
- + Drone adds Drone 2…7;
- select active drone;
- remove drone;
- per-drone PATH / SPIN_360 mode;
- separate route color per drone;
- PATH requires >=2 points;
- SPIN_360 requires one anchor;
- shared global frames/quality settings.

Exit: artist can author and inspect any mix of 1–7 missions.

### DR5 — Collision protection / external-space safety — IMPLEMENTED AT CODE LEVEL / CI + USER RUNTIME PENDING
- P9 PrimaryMesh clearance now samples both vertices and triangle centroids into a bounded surface cloud;
- dense segment preflight samples the full authored segment, not just waypoint/frame endpoints;
- hold last safe position while requested route intersects the collision envelope;
- resume only when the requested target is reachable from the held position without crossing the known P9 surface, preventing a post-wall teleport;
- blocked route segments are returned as structured diagnostics and drawn in red in the tri-view editor after validation;
- route edits invalidate the previous collision result until the node is executed again;
- fail closed if a mission starts inside the current collision envelope;
- later Gate 7 CONFIRMED_FREE/visibility evidence may augment the collision query without changing route-plan files.

Exit: no emitted camera frame passes through known P9 geometry under enabled collision policy.

### DR6 — Gate 4 / Gate 5 / Gate 6 integration — COMPLETED / CI PASS / USER RUNTIME PENDING
- route editor output drives Gate 4 evidence;
- artist-authored route bypasses automatic route interpolation;
- control and camera manifests v0.2 preserve route authority, route hash, mission order, mission mode and frame counts;
- WAN validates exact graph-tensor parity against the Gate 4 manifest before generation;
- WAN fails closed if a window loses any authored frame instead of silently shortening the route;
- split WAN windows preserve their original drone mission identity;
- Gate 6 validates route authority/hash/mission order parity between WAN and camera manifests before COLMAP materialization;
- known-camera COLMAP dataset retains the same route identity without changing P9-derived pose/intrinsics authority;
- an untouched auto-created seed remains EDITABLE_SEED; the first artist edit promotes it to ARTIST_AUTHORED;
- automatic planning remains fallback only when no route-editor payload exists.

Exit at code/CI level: the artist-route graph is wired route editor → Gate 4 evidence → Gate 5 WAN → Gate 6 known-camera reconstruction, with exact mission/frame identity enforced. Real ComfyUI runtime acceptance remains part of DR9.

### DR7 — Persistence / resume / deterministic identity — COMPLETED / CI PASS / USER RUNTIME PENDING
- the serialized route is bound to both `scene_contract_id` and `source_run_id`;
- artist-authored routes from another scene/run fail closed instead of being silently reused;
- untouched `EDITABLE_SEED` state may be regenerated for a new current scene, while `ARTIST_AUTHORED` state is never silently transplanted;
- `ConceptGhost.P10BoundDroneRoutePlan.v0.1` adds deterministic SHA-256 identity over the route, scene/run binding and route authority;
- every editor change removes the old hash, marks the route dirty and promotes the route to `ARTIST_AUTHORED`; the next node execution rebinds/re-hashes the exact current plan;
- a visible `Resetar cena` control intentionally discards the saved route so the current scene can create a fresh editable seed;
- Gate 4 persists the bound plan as `control_sequence/route_plan.json` and rebuilds its owned frame/mask directories exactly, preventing stale artifacts when a route becomes shorter;
- control/camera manifests carry the route-plan filename, route hash, scene contract and source run;
- Gate 5 verifies the persisted route file/hash/binding before WAN generation and invalidates previous WAN outputs when route/control/WAN-generation context changes;
- Gate 5 removes stale WAN windows and the previous WAN manifest before regeneration, so a failed new run cannot expose an old manifest as current;
- Gate 6 dataset manifests hash every source composite image plus the ordered source-image set;
- Gate 6 resume requires WAN manifest, camera manifest and source-composite hashes to remain identical; changed/missing source images force dataset rebuild;
- Gate 6 continues to enforce scene/run/route/mission parity before COLMAP.

Exit at code/CI level: a saved route has deterministic scene-bound identity, changed route/camera/image context cannot silently reuse stale downstream reconstruction, and cross-scene artist-route reuse fails closed. Real ComfyUI save/reload acceptance remains part of DR9.

CI evidence: GitHub Actions run `35813649004` — SUCCESS on head `02c72585a312e26fda011e128e27dd9eae4f1cc2`.

### DR8 — Diagnostics / quality controls / tests — ACTIVE

#### DR8A — Pre-WAN route diagnostics summary — COMPLETED / CI PASS
- deterministic `ConceptGhost.P10DroneRouteDiagnostics.v0.1` manifest;
- one record per active drone/mission;
- mode, authored route length, emitted translation length and exact frame count;
- minimum/mean/maximum P9 coverage and hole fraction;
- collision hold/resume counts and minimum candidate/output clearance;
- active drone count, mission order, total emitted frames and total held frames;
- deterministic PASS / WARN / FAIL semantics:
  - PASS = exact route/frame contract and no collision hold;
  - WARN = valid contract but collision hold or zero-P9-coverage advisory;
  - FAIL = mission/frame/diagnostic contract mismatch;
- low P9 coverage remains descriptive rather than automatic failure because WAN is explicitly responsible for missing-P9 completion;
- persisted before expensive WAN generation at `p10_gate4/<run_id>/diagnostics/drone_route_diagnostics.json`;
- the same summary is embedded in the Gate 4 diagnostics JSON.

CI evidence: GitHub Actions run `35816433877` — SUCCESS on `efb7a39b0a53c2035ab8ae58ca34a26c339ea92a`.

#### DR8B — Per-drone final composite GIF previews — COMPLETED / CI PASS
- one animated GIF is generated per drone from the final Gate 5 composite frames;
- every authored frame is included; the preview does not drop frames for convenience;
- one mission split across multiple WAN windows is reassembled by original global frame index before GIF creation;
- frames from different drones cannot be mixed; missing/duplicate/out-of-range composite frames fail closed;
- default preview profile: maximum width 640 px, aspect ratio preserved, 10 fps, infinite loop;
- mission names are sanitized for Windows-safe filenames;
- output folder: `p10_gate5/<run_id>/drone_previews/`;
- example names: `drone_01_drone_1_preview.gif`, `drone_02_drone_2_preview.gif`;
- each GIF records SHA-256 plus an ordered source-frame-set SHA-256;
- a preliminary `drone_preview_index.json` is already emitted as part of DR8B and becomes the formal surfacing contract in DR8C.

CI evidence: GitHub Actions run `35816862522` — SUCCESS on `6c9931c63ed18ad3d6c3ad97b59175b44a4bad22` across Windows/Python 3.12, Windows/Python 3.14 and Ubuntu/Python 3.12 jobs.

#### DR8C — Preview index / output surfacing — COMPLETED / CI PASS
- `drone_preview_index.json` is now a formal `ConceptGhost.P10DronePreviewIndex.v0.2` contract;
- index identity includes run ID, scene contract, source run, route-plan hash, control-manifest hash and WAN generation-context hash;
- mission order and mission modes are repeated explicitly and must exactly match the authored/control manifest;
- every preview records drone index, mission, mode, exact global frame range, frame count, fps, dimensions, source-frame-set SHA-256, GIF SHA-256, filename, output subfolder and absolute path;
- formal validation fails closed on missing GIFs, hash mismatch, mission/order/mode mismatch or wrong route/control/generation context;
- the WAN manifest stores both the preview-index path and preview-index SHA-256;
- Gate 5 diagnostics expose preview count, index path/hash and the individual preview metadata;
- the WAN node adds a fifth string output `drone_preview_index_path` while preserving all previous output slot numbers;
- GIFs are also surfaced through ComfyUI's standard output-image UI metadata so the artist can access the animated per-drone previews directly from the Gate 5 node;
- portable `filename + subfolder + type=output` metadata is emitted in addition to absolute paths.

CI evidence:
- `35817184829` — SUCCESS on `3c8ef10772799cd73c63c198794a0fe198bf37ab` for the formal preview-index contract;
- `35817189070` — SUCCESS on `397074acc741f6277d551dd29e2f84734b4185e0` for Gate 5 workflow/output surfacing.

#### DR8D — Preview invalidation / freshness — COMPLETED / CI PASS
- previous preview state is classified before regeneration with explicit reasons such as `ROUTE_PLAN_CHANGED`, `CONTROL_MANIFEST_CHANGED`, `WAN_SETTINGS_CHANGED`, `PREVIEW_INDEX_MISSING`, `PREVIEW_INDEX_HASH_MISSING`, `PREVIEW_INDEX_HASH_CHANGED` or `SAME_CONTEXT_EXPLICIT_REGENERATION`;
- previous preview-index bytes are checked against the SHA-256 recorded by the prior WAN manifest before deletion;
- every Gate 5 regeneration deletes the ConceptGhost-owned `drone_previews` package before publishing new previews, so a stale index/GIF set cannot remain authoritative;
- preview freshness is tied to route-plan hash + control-manifest hash + WAN generation-context hash + exact final-composite bytes;
- after GIF generation, the current final-composite sequence is reassembled again and its ordered SHA-256 is compared with every preview's recorded `source_frame_set_sha256`;
- changing a composite PNG after GIF creation makes freshness validation fail closed;
- GIF hash validation remains mandatory, so edited/corrupted GIF bytes also fail closed;
- the WAN manifest and diagnostics now record both previous-output and previous-preview invalidation reasons plus the freshness policy;
- preview package policy is `ROUTE_CONTROL_WAN_CONTEXT_PLUS_EXACT_FINAL_COMPOSITE_BYTES`.

CI evidence:
- `35817845135` — SUCCESS on implementation commit `5ee52c8edf0b84ecbaec0c3f3458fb6543ef8e2e`;
- `35817871526` — SUCCESS on regression commit `1dc4c5c44b88cd313adf48ae0da92e8bb96b5c3d`.

#### DR8E — Final regression closeout — COMPLETED / CI PASS
- dedicated aggregate closeout suite: `tests/test_dr8_closeout.py`;
- explicit CI gate: `Validate DR8 route-authoring closeout regressions`;
- Baseline/P9 isolation is locked: workflow integration operates on a deep copy and the Baseline export node remains unchanged;
- release-facing P10 workflow alone receives the `High Fidelity Split Clean` default;
- two-drone PATH + SPIN_360 sampling/identity/diagnostics are tested together;
- cross-run artist route reuse fails closed;
- split WAN windows are reassembled into one exact sequence per drone without cross-drone mixing;
- preview freshness is tested against route/control/WAN identity plus exact final-composite bytes;
- frontend artist controls, stale-route hash removal and blocked-segment visualization are locked by the aggregate suite;
- Linux/Windows matrix is green.

CI evidence: GitHub Actions run `35818321869` — SUCCESS on `de1201374c7a633dbdb1ff7654520cb79d08212d`:
- Ubuntu latest / Python 3.12 — SUCCESS;
- Windows latest / Python 3.12 — SUCCESS;
- Windows latest / Python 3.14 — SUCCESS.

Formal closeout matrix:
`docs/15_DR8_FINAL_REGRESSION_CLOSEOUT.md`.

Exit: DR8 is COMPLETE at code/CI level and ready for DR9 packaging/runtime acceptance.

### DR9 — Preview package + user runtime acceptance — PENDING
- publish next complete installer/workflow;
- install/verify BAT regression;
- visible editor instructions;
- user authors at least one curved/descending PATH and one SPIN_360 test;
- confirm route preview, generated drone frames, WAN, and reconstructed mesh;
- document accepted behavior and remaining ergonomic refinements.

Exit: artist-driven route workflow accepted in real ComfyUI runtime.

## Current progress

Completed: DR0, DR1, DR2
Implemented / awaiting user runtime: DR3, DR4
Implemented / awaiting CI + user runtime: DR5
Completed at code/CI level; user runtime acceptance pending: DR6, DR7
DR8 COMPLETE: DR8A–DR8E code/CI PASS
DR9 NEXT: complete package + real ComfyUI runtime acceptance

There are 10 subgates total. DR0–DR2 are complete; DR3–DR7 are implemented and CI-green but still need real ComfyUI runtime acceptance where applicable; DR8 remains the active engineering subgate and DR9 is the final packaged user acceptance.

## Immediate implementation order

1. package DR9 with the complete route-editor workflow;
2. validate installer/extracted bundle/release integrity and sync GitHub + Google Drive;
3. perform real ComfyUI acceptance using a curved/descending PATH plus a SPIN_360 mission and inspect the per-drone GIFs;
4. record final ergonomics refinements before returning to required Gate 7 fusion work.
