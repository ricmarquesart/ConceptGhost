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

### DR3 — Interactive ComfyUI route editor — IN PROGRESS
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

### DR4 — Multi-drone UX + mission modes — PARTIAL BACKEND / UI PENDING
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

### DR5 — Collision protection / external-space safety — PARTIAL BACKEND
- initial P9-geometry clearance query;
- hold last safe position while requested route intersects collision envelope;
- resume when authored path is safe again;
- visualize blocked/held segments;
- fail closed if a mission starts inside geometry;
- later Gate 7 free-space evidence may augment the collision query without changing route-plan files.

Exit: no emitted camera frame passes through known P9 geometry under enabled collision policy.

### DR6 — Gate 4 / Gate 5 / Gate 6 integration — PARTIAL
- route editor output drives Gate 4 evidence;
- artist-authored route bypasses automatic route interpolation;
- control/camera manifests preserve drone identity;
- WAN receives frames in exact authored mission order;
- known-camera COLMAP receives the resulting cameras without changing calibration authority;
- automatic route remains only fallback when no authored plan exists.

Exit: one manually authored route completes WAN + Gate 6 reconstruction.

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
Active: DR3
Partially implemented in backend: DR4, DR5, DR6, DR8
Pending: DR7, DR9

There are 10 subgates total. At the start of this plan, 3 are complete and 7 remain including the active DR3.

## Immediate implementation order

1. finish DR3 frontend editor;
2. finish DR4 drone controls and PATH/SPIN interaction;
3. add collision visualization and strengthen DR5;
4. complete DR6 end-to-end route wiring;
5. add DR7 persistence/hash invalidation;
6. close DR8 CI/diagnostics;
7. package DR9 for user runtime validation.
