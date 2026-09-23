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

### DR7 — Persistence / resume / deterministic identity — PENDING
- save route plan with scene_contract_id and source_run_id;
- reject route from another scene;
- version/hash plan;
- preserve plan across workflow save/reload;
- checkpoint invalidation when route changes;
- resume only when route/camera/image hashes still match.

Exit: saved workflow reproduces identical camera manifests.

### DR8 — Diagnostics / quality controls / tests — PARTIAL
- route length / min clearance;
- active drone count;
- per-mission frame count;
- blocked/held/resumed counts;
- trajectory preview before WAN;
- unit tests on Linux/Windows CI;
- workflow wiring regression tests;
- no mutation of Baseline/P9.

Exit: GitHub Actions PASS and diagnostic manifest available before expensive generation.

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
Completed at code/CI level; user runtime acceptance pending: DR6
Partially implemented: DR8
Pending: DR7, DR9

There are 10 subgates total. DR0–DR2 are complete; DR3–DR4 are implemented and CI-green but still need real ComfyUI runtime acceptance; DR5–DR9 remain to be closed.

## Immediate implementation order

1. finish DR3 frontend editor;
2. finish DR4 drone controls and PATH/SPIN interaction;
3. add collision visualization and strengthen DR5;
4. complete DR6 end-to-end route wiring;
5. add DR7 persistence/hash invalidation;
6. close DR8 CI/diagnostics;
7. package DR9 for user runtime validation.
