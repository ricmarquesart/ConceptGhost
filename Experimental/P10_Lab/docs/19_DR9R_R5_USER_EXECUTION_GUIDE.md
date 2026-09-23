# ConceptGhost v1.54 P10 DR9R r5 — User Execution Guide

## Installation

1. Extract `ConceptGhost_v1.54_P10_DR9R_COMPLETE_TWO_STAGE_INSTALLER_r5.zip`.
2. Close ComfyUI.
3. Run `03_INSTALL_ALL.bat`.
4. Run `04_VERIFY_INSTALL.bat`.
5. Restart ComfyUI Desktop once.
6. `05_RUN_CONCEPTGHOST.bat` is optional; it prints the flow and selects the Route Setup workflow in Explorer.

## Workflow A — Route Setup

Open `ConceptGhost_v1.54_P10_DR9R_ROUTE_SETUP_r5.json`.

### Queue Prompt #1

Queue once. This runs/loads the accepted P9 scene and exposes the Perspective + TOP/SIDE/FRONT route workspace. It intentionally stops before P10 evidence, WAN and Gate 6. The commit node may show `WAITING_FOR_ARTIST_ROUTE`; that is expected.

### Edit the route

Use Perspective for orbit/zoom inspection. Use TOP/SIDE/FRONT for authoritative 3D waypoint placement. Prefer `LOOK_AT_TARGET` when the drone should keep watching a building/region. Use `LOOK_ALONG_PATH` only when forward-flight viewing is intended, and `MANUAL_DIRECTION` for explicit artist direction. Inspect the visible direction/frustum.

### Queue Prompt #2

After editing, queue Workflow A a second time. P9 should remain cached. This commits `committed_route.json`, creates the scene/run-bound `production_entry.json`, and updates `LATEST_PRODUCTION_ENTRY.json`. It still does not run WAN or Gate 6. Continue only when the commit node reports `READY` / `production_ready=true`.

## Workflow B — P10 Production

Open `ConceptGhost_v1.54_P10_DR9R_PRODUCTION_r5.json`.

Leave the loader at `AUTO_LATEST`. It automatically resolves the most recently committed Route Setup entry.

### Queue Prompt #3

Queue Production once. This workflow contains no P9 solver. It loads the committed P9 run + route and executes:

`P10 Evidence -> WAN -> source-preserving composite -> known-camera sparse/dense reconstruction -> pre-fusion mesh -> geometry-quality diagnostics`.

Every Production queue creates a new immutable folder:

`ComfyUI/output/conceptghost/p10_attempts/<p9_run_id>/<p10_attempt_id>/`

A later Production queue never overwrites the previous attempt.

## What to inspect

- per-drone GIFs and whether each camera looks at the intended subject;
- source-preserving WAN composites;
- metric P9/P10 overlay;
- Gate 6 geometry-quality `PASS/WARN/FAIL` and alerts;
- per-mission selected/dropped-frame contribution;
- P9-only round-trip audit;
- `RECONSTRUCTED PRE-FUSION MESH` as P10 pre-fusion geometry, not the final Gate-7 scene.

## Expected number of queues

For a new P9 scene/route: **three Queue Prompt clicks** total:
1. Route Setup #1 — one expensive P9 solve, no WAN/Gate6.
2. Route Setup #2 — route commit, P9 cache reuse expected, no WAN/Gate6.
3. Production #1 — one P10 Production run.

This removes the old wasted first WAN/Gate6 execution that existed only to reveal the route map.