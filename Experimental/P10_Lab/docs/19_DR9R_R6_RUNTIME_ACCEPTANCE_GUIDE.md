# ConceptGhost v1.54 P10 DR9R r6 — Runtime Acceptance Guide

## Install

1. Extract `ConceptGhost_v1.54_P10_DR9R_COMPLETE_TWO_STAGE_INSTALLER_r6.zip` to a normal writable folder.
2. Close ComfyUI.
3. Run `03_INSTALL_ALL.bat`.
4. If installation reports PASS, run `04_VERIFY_INSTALL.bat`.
5. Restart ComfyUI Desktop once.
6. `05_RUN_CONCEPTGHOST.bat` is optional; it only prints the two-stage flow and selects the Route Setup workflow in Explorer.

## Workflow A — Route Setup

Load `ConceptGhost_v1.54_P10_DR9R_ROUTE_SETUP_r6.json`.

### Queue Prompt #1

Queue once. This runs/loads the authoritative P9 solve and produces the route workspace, then intentionally stops before P10 Evidence, WAN and Gate 6.

Expected state: the route commit may report `WAITING_FOR_ARTIST_ROUTE`. This is normal.

### Edit the route

Use Perspective for orbit/zoom inspection. Use TOP/SIDE/FRONT for authoritative waypoint placement.

For PATH missions:
- prefer `LOOK_AT_TARGET` when following a building/region;
- use `LOOK_ALONG_PATH` only when the camera should look in the flight direction;
- use `MANUAL_DIRECTION` for explicit yaw/pitch direction.

SPIN_360 keeps the rotating camera behavior.

Check both position and visible aim/frustum.

### Queue Prompt #2

After editing, Queue Workflow A a second time.

Expected behavior:
- P9 stays cached instead of running the expensive solve again;
- the route becomes `ARTIST_AUTHORED`;
- `committed_route.json` and `production_entry.json` are created;
- `LATEST_PRODUCTION_ENTRY.json` points to the newest committed entry;
- WAN/Gate6 still do not run.

Do not continue until the commit node shows `status = READY` and `production_ready = true`.

## Workflow B — P10 Production

Load `ConceptGhost_v1.54_P10_DR9R_PRODUCTION_r6.json`.

Leave the first node at `AUTO_LATEST` for the normal flow.

Queue once.

Production contains no P9 solver. It loads the committed P9 run + route and runs:

`P10 Evidence -> WAN -> source-preserving composite -> known-camera sparse/dense reconstruction -> pre-fusion mesh -> geometry-quality authority`.

Every Production queue creates a new immutable directory:

`ComfyUI/output/conceptghost/p10_attempts/<p9_run_id>/<p10_attempt_id>/`

Prior attempts are not overwritten.

## Expected Queue Prompt count for a new scene

1. Route Setup #1 — expensive P9 solve + route workspace; STOP before WAN/Gate6.
2. Edit route.
3. Route Setup #2 — lightweight route commit; P9 should be cached; STOP before WAN/Gate6.
4. Production #1 — one P10 Production run.

Therefore: three Queue Prompt clicks, one expensive P9 solve, one P10 Production run.

## What to inspect after Production

- one final-composite GIF per authored drone;
- whether each camera is aimed at the intended subject;
- WAN/source-preserving composites;
- P9-only reconstruction audit;
- per-mission selected/dropped/contributing frame diagnostics;
- metric P9/P10 overlay;
- Gate 6 geometry-quality PASS/WARN/FAIL and its alerts;
- RECONSTRUCTED PRE-FUSION MESH, which is still pre-Gate-7 geometry rather than the final fused scene.

If Geometry Quality is FAIL, do not promote the result to Gate 7. WARN means usable evidence exists but requires review.
