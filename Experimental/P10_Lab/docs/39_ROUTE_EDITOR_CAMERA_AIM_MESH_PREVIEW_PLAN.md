# ConceptGhost — Route Editor Camera Aim + Mesh Preview Plan

Date: 2026-09-24
Status: R6A IMPLEMENTED / CI PENDING · R6B-R6F PLANNED · USER VALIDATION DEFERRED TO R6F

## 1. Current route-editor facts

The Route Authoring node already receives the accepted P9 PrimaryMesh before WAN/P10 reconstruction.
The current interactive editor does not render the full mesh. It transforms the P9 PrimaryMesh into
P9 camera-local coordinates and sends a bounded point sample to the browser. The current interactive
metadata budget is 50,000 points. Collision preflight uses a separate bounded P9 surface sample.

Therefore a mesh/surface preview does not require waiting for Gate 6 or Gate 7. The P9 mesh already
exists at Route Setup time.

## R6 execution policy

The artist requested no intermediate target-PC validation. R6A-R6E are source/CI checkpoints only.
The first user validation package is R6F after all editor improvements are integrated.

Current sequence:
- R6A Points/Mesh LOD + Point Size — IMPLEMENTED / CI PENDING
- R6B Selected Camera View + frustum — NEXT
- R6C Per-waypoint camera pose + SPIN_360 pitch/yaw — PLANNED
- R6D Perspective pivot/gimbal + orbit-direction correction — PLANNED
- R6E Route schema/export/import v0.2 + readable CSV/TXT — PLANNED
- R6F aggregate regression + Evaluation_Builds bundle — PLANNED / ONLY USER VALIDATION POINT

## 2. Preview representation

Add a display-only preview selector:

- POINTS_LOW
- POINTS_MEDIUM
- POINTS_HIGH
- MESH_SURFACE
- MESH_WIREFRAME

Point mode:
- preserve the current transparent/read-through benefit;
- add point-size control;
- keep deterministic point budgets.

Mesh mode:
- derive a display LOD from the accepted P9 PrimaryMesh;
- never replace P9 geometry authority;
- never feed preview simplification back into collision, camera, WAN or reconstruction;
- cache the display LOD by P9 run identity;
- use source-derived vertex colors when available.

Do not send the full multi-million-face PrimaryMesh to the browser. The display mesh must be bounded
to an interactive face/vertex budget.

R6A implementation uses deterministic point LODs (15k / 50k / up to 100k points) and a bounded
24k-face mesh LOD. The backend caches up to three preview payloads by PrimaryMesh bytes/timestamp,
source-image identity, camera transform and LOD budgets. The mesh/point payload is explicitly marked
DISPLAY_ONLY and is never fed back into route, collision, WAN, reconstruction or official geometry.

## 3. Selected camera preview

Add two complementary views.

### Live editor preview

When the artist selects a PATH waypoint or the SPIN_360 anchor, show a Selected Camera View panel
inside the Route Editor using the same preview geometry. Update immediately while route position or
camera aim changes.

### Authoritative refresh node

Add a dedicated P10 Selected Drone Camera Preview node. Inputs:
- run_dir
- route_plan_json
- mission index/name
- waypoint index or sampled frame index
- preview mode / resolution

It renders from the accepted P9 geometry and exact route-camera transform when the node is queued.
This is the high-confidence verification path when the live browser preview is not sufficient.

## 4. Per-waypoint camera aim

Upgrade the route schema with backward compatibility.

PATH:
- every control waypoint may own an optional look direction;
- artist can select a waypoint and adjust camera aim independently;
- if no per-waypoint aim exists, preserve mission-level LOOK_AT_TARGET / LOOK_ALONG_PATH /
  MANUAL_DIRECTION behavior;
- sampled frame directions interpolate continuously between authored waypoint directions;
- collision HOLD_AND_RESUME preserves the authored/interpolated look direction while translation is held.

SPIN_360:
- keep one translation anchor;
- add explicit vertical aim / pitch offset for the whole spin;
- optional yaw start offset;
- the spin remains 360 degrees around the anchor and is not converted to a path.

## 5. Camera manipulation UI

For the selected waypoint:
- draw camera frustum/direction arrow in Perspective, Top, Side and Front;
- selected camera preview panel shows exactly what that camera sees;
- camera aim can be changed without moving the route waypoint;
- support yaw/pitch numeric fields plus direct target/aim manipulation.

## 6. Perspective pivot / orbit gizmo

Replace the current implicit fixed scene center with an explicit 3D orbit pivot:
- visible X / Y / Z gizmo at pivot;
- drag X/Y/Z handles to move pivot in P9 local coordinates;
- orbit rotates around that pivot;
- Reset Pivot returns to P9 preview-geometry center;
- Frame Selection can set pivot to selected route point.

Review horizontal orbit sign. Current implementation applies positive yaw for positive horizontal drag;
the next preview must validate expected artist behavior and invert the default if the visual motion is
opposite to natural viewport navigation.

## 7. Export / import

Portable route JSON remains the authoritative editable interchange and will be schema-versioned.
It must include:
- route positions;
- per-waypoint camera aim;
- SPIN_360 pitch/yaw settings;
- mission orientation fallback;
- scene/run binding metadata.

Also add a human-readable TXT/CSV-style export with one row per control point/frame containing at
minimum:
mission, mode, waypoint/frame, right, up, forward, look_right, look_up, look_forward, yaw, pitch.

Import must restore both translation and camera orientation.

## 8. Performance policy

Higher point density affects only Route Setup preview preparation, metadata transfer and browser drawing.
It does not rerun Atlas, MoGe or Maya. Mesh preview is more expensive than points because faces must be
transported, depth-sorted/projected and filled/wireframed.

Use cached bounded LODs rather than the full P9 mesh.

## 9. Acceptance

- POINTS/MESH switch works without changing route authority.
- point size is adjustable.
- selected waypoint camera view is correct.
- per-waypoint aim survives save/reload/export/import.
- SPIN_360 pitch adjustment works.
- perspective pivot gizmo works on X/Y/Z.
- horizontal orbit direction feels consistent with standard viewport navigation.
- old v0.1/v0.2 route files still load.
- P9 critical file hashes remain unchanged.
