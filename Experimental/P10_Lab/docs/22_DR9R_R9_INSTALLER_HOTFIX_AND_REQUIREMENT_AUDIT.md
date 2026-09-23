# ConceptGhost P10 DR9R — r9 Installer Hotfix & Requirement Audit

Date: 2026-09-23

## Why r9 exists

The first r8 installation on the target machine completed the MoGe runtime checks and the Maya capability verification, then stopped at the PROJECT_CONTROL shared-Python fingerprint guard.

The r8 guard compared only the raw textual output of `pip freeze`. That text is useful evidence but is not a stable package-identity contract: editable/direct-URL/metadata rendering may differ even when the installed distribution name/version set is unchanged.

r9 changes the protected-environment invariant to compare the **complete installed distribution set as normalized package-name + exact version**. The raw `pip freeze` snapshot is still retained for evidence.

Policy:
- canonical package name/version set changed -> FAIL CLOSED and print the exact before/after package differences;
- canonical set unchanged but raw `pip freeze` text changed -> WARNING only, because this is representation/metadata drift;
- no package installation/downgrade is permitted in protected shared ComfyUI Desktop.

This preserves PROJECT_CONTROL safety and removes the ambiguous raw-text-only failure mode.

## Legacy Master workflow

The inherited v1.53 base verifier still needs its full Master workflow JSON as a private compatibility fixture.

r9 sets `CONCEPTGHOST_INTERNAL_BASE_WORKFLOW_ONLY=1` while inherited Gate5/Gate6/base verification runs. The Master JSON is copied only to:

`%LOCALAPPDATA%\ConceptGhost\internal\workflows\ConceptGhost_Master_v1.53.0.json`

It is **not** installed in the ComfyUI user workflow folder.

After base verification, the visible ConceptGhost workflow folder contains exactly:

1. `01_ConceptGhost_P10_ROUTE_SETUP.json`
2. `02_ConceptGhost_P10_PRODUCTION.json`

Failure cleanup also removes legacy Master / internal Gate5 / Gate6 preview workflows from the user workflow tree.

## Route editor runtime hotfix found during audit

The post-r8 source audit found one duplicated JavaScript `onExecuted` callback wrapper in the route editor. It could cause duplicated scene ingestion/refresh behavior.

Corrected in source and protected with a frontend contract test that requires exactly one execution callback.

This is included in r9.

## Requirement audit

### Workflow order / Run sequence

Implemented.

Workflow 01:
- Run #1: P9 solve/load + route workspace; expected stop before WAN/Gate6.
- Artist edits route.
- Run #2: route commit; emits `production_entry.json`.

Workflow 02:
- AUTO_LATEST resolves the committed production entry.
- Run #3: creates a new immutable P10 attempt and runs current P10 Production.

### Storage / handoff / cleanup

Implemented for current P10 stage.

Canonical P10-owned storage:
- route handoff: `<ComfyUI output>/conceptghost/p10_route_setup/<p9_run_id>/`
- latest handoff pointer: `<ComfyUI output>/conceptghost/p10_route_setup/LATEST_PRODUCTION_ENTRY.json`
- attempts: `<ComfyUI output>/conceptghost/p10_attempts/<p9_run_id>/<p10_attempt_id>/`
- route editor cache: `<ComfyUI output>/conceptghost/p10_route_editor/`

Per-attempt current evidence:
- Gate4 drone/control evidence: `<attempt>/gate4/`
- raw drone flight frames: `<attempt>/gate4/control_sequence/frames/`
- hole masks: `<attempt>/gate4/control_sequence/masks/`
- route/camera/control manifests: `<attempt>/gate4/control_sequence/`
- flight GIF: `<attempt>/gate4/P10_drone_flights_P9_holes.gif`
- Gate5 WAN data: `<attempt>/gate5/`
- WAN raw output: `<attempt>/gate5/wan_raw/`
- source-preserving composites: `<attempt>/gate5/composite/`
- per-drone GIFs + index: `<attempt>/gate5/drone_previews/`
- Gate6/reconstruction: `<attempt>/gate6/`
- diagnostics: `<attempt>/diagnostics/`

`06_P10_STORAGE_AND_CLEANUP.bat` is the explicit safe cleanup/report tool. It cannot delete P9.

r9 adds a dedicated **route handoff only** cleanup choice. This allows the small cross-workflow contract to be removed when the artist no longer needs to run/re-run P10 from it without deleting attempts or P9.

Automatic deletion is intentionally not performed yet because later P10 gates may still need current route/attempt evidence. Final P10 closeout will delete only artifacts marked disposable after provenance/final outputs have been embedded and validated.

### Reset / route workspace

Implemented in source; runtime acceptance still required.

- old destructive `Resetar cena` removed;
- `Resetar rota` restores the route seed only;
- `Enquadrar tudo` changes viewport framing only;
- numeric widgets are sanitized rather than being reset to invalid values;
- P9 scene/preview remains loaded.

### Four-view navigation

Implemented in source; runtime acceptance still required.

- Perspective: orbit / zoom / inspection pan;
- TOP/SIDE/FRONT: independent zoom/pan with axis orientation locked;
- higher scene point budget / smaller projected points;
- no baked duplicate background geometry;
- visibility guard / fit behavior keeps edited route inspectable;
- drawing is clipped per viewport.

### Production AUTO_LATEST observability

Implemented.

The Production Entry node reports:
- AUTO_LATEST vs explicit mode;
- latest pointer path;
- resolved `production_entry.json` path + filename;
- committed route path;
- P9 run directory + run id;
- scene contract id;
- route-plan SHA-256;
- P9 dependency inventory path/count;
- newly created P10 attempt id/root.

### P9 continuity after workflow split

Implemented as a persisted dependency contract, not an in-memory shortcut.

Workflow 01 stores the authoritative P9 run directory and a dependency inventory. Workflow 02 reopens that entire P9 run and validates critical hashes. Future Gates 7–10 must request named P9 evidence from that persisted run and fail closed if required evidence is missing.

The split therefore does not intentionally discard camera/scale/PrimaryMesh/source/provenance/semantic/confidence evidence that was persisted by P9.

### Dual Maya

Contract implemented; final P10 Maya exporter is not yet implemented because P10 refined/fused final geometry does not exist yet.

- existing P9 `.ma` remains immutable;
- future P10 refined `.ma` must be a second file;
- P10 exporter is contractually forbidden to resolve to/overwrite the P9 `.ma`;
- actual second Maya export belongs to the later P10 final Maya/export gate.

### MoGe diagnostics

Implemented in Workflow 01, OFF by default, diagnostic-only. No official geometry authority when ON and zero output impact when OFF.

## r9 acceptance gates

Before r9 can be called runtime-accepted:
1. installer canonical environment fingerprint must PASS on the target machine;
2. ComfyUI user workflow folder must contain only numbered 01/02;
3. Workflow 01 Run #1 must produce P9 workspace;
4. route editor reset/zoom/pan/visibility behavior must be tested;
5. Workflow 01 Run #2 must produce READY production entry;
6. Workflow 02 Run #3 must visibly resolve that entry and create a unique attempt;
7. drone/Gate4/Gate5 outputs must land inside that attempt root;
8. optional MoGe diagnostic ON test may be performed separately;
9. P9 Maya must remain untouched.

Gate 7 remains blocked until runtime acceptance of this corrected package.
