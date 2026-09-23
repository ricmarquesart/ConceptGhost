# ConceptGhost P10 DR9R-F — Workflow UX, Storage Lifecycle, P9 Continuity & Dual Maya Export

Date: 2026-09-23

## Why this corrective block exists

The first real r6 Route Setup session confirmed that the two-stage architecture is directionally correct, but exposed several artist-facing and lifecycle issues that must be corrected before Gate 7:

- the two workflows need explicit numeric ordering and in-workflow instructions;
- Route Setup reset behavior can invalidate the node/widget state and erase the useful scene workspace;
- the 4-view editor needs independent zoom/pan while preserving locked TOP/SIDE/FRONT axes;
- the Perspective view currently mixes a dynamic point-cloud render with a static baked background copy;
- orthographic routes can move outside the visible viewport after edits made from another axis;
- P10 handoff/cache/output locations need explicit lifecycle and cleanup rules;
- Production AUTO_LATEST needs to show exactly which entry/P9 run/route it resolved;
- the package should not leave the old Master v1.53 workflow installed as a user-facing workflow;
- the split-workflow architecture needs a formal P9 dependency audit so future Gate 7–10 stages cannot accidentally lose upstream evidence;
- P9 Maya output and future P10 refined Maya output must be separate immutable deliverables.

P9 remains accepted immutable upstream authority. DR9R-F does not reopen or modify P9 geometry.

## F1 — Workflow ordering + embedded artist instructions

Status: COMPLETE / CI PASS

User-facing workflow names become:

1. `01_ConceptGhost_P10_ROUTE_SETUP_r7.json`
2. `02_ConceptGhost_P10_PRODUCTION_r7.json`

Route Setup must visibly state:
- RUN #1: solve/load P9 and prepare route workspace; expected stop before WAN/Gate6;
- edit drones;
- RUN #2: commit artist route only; P9 should remain cached;
- then open workflow 02.

Production must visibly state:
- keep AUTO_LATEST for normal use;
- RUN #3: execute P10 production from committed P9+route;
- every run creates a new immutable P10 attempt.

## F2 — Route workspace viewport + reset safety

Status: COMPLETE / CI PASS / USER RUNTIME PENDING

Replace the mixed static-image/dynamic rendering path with one dynamic scene renderer for all four panels.

Required behavior:
- no frozen duplicate geometry behind Perspective;
- higher point-sample budget and smaller point marks;
- wheel zoom in Perspective, TOP, SIDE and FRONT;
- Perspective drag = orbit; optional pan remains inspection-only;
- TOP/SIDE/FRONT remain axis-locked forever;
- Shift+drag or middle-drag pans an orthographic viewport without changing its axis;
- route edits made in one panel cannot silently disappear outside another panel: auto-fit/visibility guard expands only when needed;
- point picking uses the active orthographic viewport transform;
- all drawing is clipped to the panel;
- viewport reset restores framing only, never clears P9 or route data.

The old destructive `Resetar cena` control is removed/redefined. New controls:
- `Resetar rota`: restore the server-seeded route for the current P9 scene while preserving the scene/preview and valid numeric node settings;
- `Enquadrar tudo`: reset all four viewport zoom/pan states without touching the route.

## F3 — Storage lifecycle + cleanup contract

Status: COMPLETE FOR CURRENT P10 / FINAL AUTO-CLEANUP DEFERRED TO FINAL P10 CLOSEOUT

Canonical local paths:

### P9 authoritative run
`<ConceptGhost output root>/<scene run id>/...`

Owned by P9. DR9R-F must never delete it.

### Route handoff
`<ComfyUI output>/conceptghost/p10_route_setup/<p9_run_id>/`
Contains:
- `committed_route.json`
- `production_entry.json`
- `route_setup_status.json` when waiting

Pointer:
`<ComfyUI output>/conceptghost/p10_route_setup/LATEST_PRODUCTION_ENTRY.json`

These files are tiny and may remain until replaced or manually cleaned. They are not a hidden cache; they are explicit handoff contracts.

### P10 attempts
`<ComfyUI output>/conceptghost/p10_attempts/<p9_run_id>/<p10_attempt_id>/`

Contains attempt-specific Gate4 evidence, drone frames/GIFs, WAN composites, reconstruction data and diagnostics. A new Production run never overwrites an earlier attempt.

### Cleanup policy
- failed/cancelled attempts are preserved for diagnosis until the artist explicitly cleans them;
- successful attempt heavy intermediates must not auto-delete until all downstream P10 gates/final deliverables that depend on them are validated;
- final P10 success will emit a cleanup manifest and then auto-delete only intermediates marked disposable;
- final deliverables, diagnostic package, route contract, P9 run and both Maya files are preserved;
- manual cleanup tool must be P10-scoped and refuse to delete P9.

DR9R-F will add a visible storage report and a safe manual cleanup/open-storage utility to the bundle.

## F4 — AUTO_LATEST observability

Status: COMPLETE / CI PASS

The Production Entry loader must visibly report, before/downstream of execution:

- resolution mode: AUTO_LATEST or explicit path;
- resolved `production_entry.json` absolute path;
- resolved file name;
- committed route path;
- source P9 `run_dir`;
- source P9 run id;
- scene contract id;
- route-plan SHA-256;
- latest-pointer path;
- newly created `p10_attempt_id` and attempt root.

AUTO_LATEST is convenience only; the resolved path must never be hidden.

## F5 — P9 dependency closure audit

Status: COMPLETE / CI PASS / FUTURE GATES FAIL-CLOSED ON MISSING P9 EVIDENCE

The two-stage split does **not** mean P10 loses P9 data. Production Entry stores the P9 run directory as authority, and every P10 stage can reopen the full run from disk.

Current validated P9 boundary already requires:
- official `manifest.json`;
- `source/source.png`;
- `camera/camera.json`;
- authoritative PrimaryMesh NPZ;
- `maya/primary_mesh_payload.json`;
- `package/official_outputs_contract.json`;
- `output_index.json`;
- identity-chain / scale-authority consistency.

It also exposes optional:
- canonical P9 point cloud;
- geometry health.

However, future P10 Gates 7–10 may need additional P9 artifacts beyond today’s minimum boundary. DR9R-F therefore adds a dependency inventory contract: future P10 code must request named P9 evidence through the run directory/boundary rather than rely on in-memory links from the old single workflow.

Required future classes of P9 evidence include:
- canonical coordinate/scale/camera authority;
- source observation and source-lock evidence;
- PrimaryMesh + source UV/grid mapping;
- P9 geometry/point-cloud evidence;
- semantic/normals/boundaries/confidence evidence where Gate 7/8 policy uses them;
- metric/manual-authority decisions;
- provenance/diagnostic manifests needed for fusion and texture recovery.

Gate 7 implementation is blocked if any required artifact is not persisted in the P9 run.

## F6 — Dual Maya deliverable contract

Status: CONTRACT IMPLEMENTED / ACTUAL P10 MAYA EXPORT DEFERRED TO LATER MAYA/EXPORT GATE

The existing P9 Maya file remains immutable and is never overwritten.

Required outputs:

1. **P9 Maya**
   - existing working P9 scene;
   - contains current P9 geometry including known holes;
   - remains the recovery/reference deliverable.

2. **P10 Refined Maya**
   - a second, separately named `.ma`;
   - starts from the accepted P9 scene authority;
   - contains Gate 7/8/9 P10 geometry/texture refinements and reconstructed missing regions;
   - preserves provenance so P9-known vs P10-generated/refined geometry can be distinguished;
   - never overwrites or renames the P9 Maya file.

Suggested final naming:
- `ConceptGhost_<run_id>_P9.ma`
- `ConceptGhost_<run_id>_P10_Refined.ma`

The P10 Maya exporter must fail closed if its output path resolves to the P9 Maya file.

## F7 — Current-only installer cleanup

Status: COMPLETE IN r7 PACKAGE

The final DR9R-F bundle must install only workflows 01 and 02 as user-facing current workflows.

The legacy `ConceptGhost_Master_v1.53.0.json` may remain inside the bundle only if old installer regression tests require it as a private fixture, but it must not be copied into the user workflow folder by the final installer. Historical ConceptGhost P10 workflows are removed under current-only policy.

## F8 — Regression + package acceptance

Status: COMPLETE / r7 PUBLISHED / USER RUNTIME ACCEPTANCE PENDING

Release-blocking checks:
- reset-route preserves scene + valid numeric widgets;
- viewport reset does not modify route/P9;
- Perspective has no static duplicate geometry;
- zoom works in all four panels;
- orthographic pan remains axis-locked;
- waypoint/target projections remain visible or auto-fit;
- Production loader exposes resolved paths;
- storage/cleanup tool refuses P9 deletion;
- only numbered workflows 01/02 are installed;
- P9 dependency inventory is complete for currently implemented P10 gates;
- dual Maya non-overwrite contract is locked in roadmap/tests;
- all existing DR9R tests remain PASS.

No user runtime retest is requested until F1–F8 are complete and a replacement bundle is published.


## r7 final package checkpoint — 2026-09-23

Final bundle:
`ConceptGhost_v1.54_P10_DR9R_COMPLETE_TWO_STAGE_INSTALLER_r7.zip`

Published locations:
- Google Drive Evaluation_Builds file id: `1hAp4qqbCVxUyHLXrKuWQUPHERLcFNFWR`
- GitHub Release tag: `p10-dr9r-r7`

Integrity:
- bytes: `12,234,655`
- SHA-256: `0e38a75b5b4736a6b09e99fcfe71f3a361cf03946ac0bed0ef47eed889d8f756`
- runtime source commit: `2b35f61057c1131520d21059c183ab02fbdca635`
- GitHub source CI run `35897710951`: SUCCESS
- JavaScript syntax: PASS
- static runtime verifier: PASS
- bundle test: PASS
- extracted SHA256SUMS: PASS
- Drive re-download digest: PASS
- GitHub release asset digest: PASS

The r7 package installs only:
1. `01_ConceptGhost_P10_ROUTE_SETUP_r7.json`
2. `02_ConceptGhost_P10_PRODUCTION_r7.json`

The legacy Master v1.53 remains only as a private compatibility fixture inside the ZIP because the inherited base installer still uses it during setup; r7 removes it from the user's workflow folder before installation completes.

Storage utility:
`06_P10_STORAGE_AND_CLEANUP.bat`

Runtime acceptance remains PENDING. Gate 7 remains blocked until the user validates r7 in ComfyUI.


## F9 — Optional MoGe Depth Diagnostics

Status: **IMPLEMENTED / CI PASS / r8 PACKAGE PUBLISHED**

Add a diagnostic-only Refined/P9 MoGe side lane, OFF by default, inside Workflow 01.

Requirements locked:
- main Enable MoGe Diagnostics switch defaults OFF;
- optional raw outputs, 3D preview and extra depth visual switches;
- exact native-vs-derived distinction;
- original / grayscale / heatmap / inverse-depth / bands / contours / discontinuities / normals / mask / point-cloud diagnostics where source data exists;
- raw depth/points/normals/mask/intrinsics + optional per-step evidence when explicitly enabled;
- separate diagnostic storage under <ConceptGhost output root>/_diagnostics/moge_depth/...;
- explicit diagnostic runs preserved until manual cleanup;
- fail-open diagnostic failure with zero official geometry authority;
- visible notes containing Purpose / Inputs / What it does / Outputs / Authority / Geometry impact / Default state / Failure/fallback / TEMP-retention / Next stage;
- existing official P9 Primary Master remains the authoritative mesh preview.

Detailed spec: `docs/21_P9_MOGE_DEPTH_DIAGNOSTICS.md`.


### F9 package checkpoint — 2026-09-23

- Source authority commit for r8 payload: `e6823e4617c394aedec4796a2e277d8f9bf4429b`.
- CI: ConceptGhost Tests run `35900795172` — SUCCESS.
- Source snapshot run `35900795335` — SUCCESS.
- Final package: `ConceptGhost_v1.54_P10_DR9R_MOGE_DIAGNOSTICS_TWO_STAGE_INSTALLER_r8.zip`.
- ZIP size: 12,752,338 bytes.
- SHA-256: `9774a887e397e18d9dcb76c65dea29ce4496ec95f0fa75570b400238dad0139c`.
- Google Drive file id: `1wyRBo_RqXJQXm8JCmRUpMyaPHk11X0Vr`.
- GitHub release tag: `p10-dr9r-r8`; release asset digest matches the same SHA-256.
- r8 installs only stable numbered user workflows:
  - `01_ConceptGhost_P10_ROUTE_SETUP.json`
  - `02_ConceptGhost_P10_PRODUCTION.json`
- Diagnostic group lives only in Workflow 01 and remains OFF by default.
- Extracted bundle SHA256SUMS: PASS.
- Static runtime verifier: PASS.
- Bundle contract test: PASS.
- User runtime diagnostic acceptance remains pending.


## r9 installer/runtime corrective checkpoint — 2026-09-23

Status: **PACKAGE PUBLISHED / STATIC + CI VALIDATION PASS / USER RUNTIME PENDING**.

The r8 target-machine install exposed two package-level issues and one source-audit issue:

1. The shared-Python guard used raw `pip freeze` text hash as the mutation authority. r9 keeps raw freeze as evidence but enforces the complete normalized installed distribution name+version set. Actual package changes still fail closed with a package-level diff.
2. The inherited v1.53 verifier could place `ConceptGhost_Master_v1.53.0.json` in the user workflow folder before the outer installer cleaned it. If installation failed during the base step, the old Master remained visible. r9 runs the base verifier in private-workflow mode and failure-cleanup removes legacy/internal workflows from the user tree.
3. Route editor audit found a duplicated `onExecuted` callback wrapper. It is removed and a regression test now requires exactly one callback.

Storage clarification:
- route handoff is retained while P10 can still reuse it;
- r9 exposes an explicit route-handoff-only cleanup action;
- final closeout will auto-delete only artifacts proven disposable after final provenance/deliverables validate;
- P9 remains outside P10 cleanup authority.

F6 remains intentionally split:
- dual-Maya **non-overwrite contract is implemented**;
- actual P10 Refined Maya generation is deferred until the final refined P10 geometry/export gate exists.

Detailed audit: `docs/22_DR9R_R9_INSTALLER_HOTFIX_AND_REQUIREMENT_AUDIT.md`.


### r9 final package — 2026-09-23

- `ConceptGhost_v1.54_P10_DR9R_MOGE_DIAGNOSTICS_TWO_STAGE_INSTALLER_r9.zip`
- SHA-256: `1143e94e0fcbfcf25809efa0a21fae162fa79079c3223b8ea2eec677069609bf`
- bytes: `12,234,987`
- Google Drive Evaluation_Builds file id: `1YUTpjOJzAIwYJwhgk87f8Dr-WONzwo7T`
- GitHub Release: `p10-dr9r-r9`
- final source/test head: `9fa358c7ad7078b4f7bfa4e2e181848daf37cf2b`
- final tests: run `35906865640` SUCCESS
- final source snapshot: run `35906865630` SUCCESS

r9 is the only package to use for the next runtime pass.
