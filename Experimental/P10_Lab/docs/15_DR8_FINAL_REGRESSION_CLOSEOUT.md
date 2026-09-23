# P10 DR8 — Final Regression Closeout Matrix

Status: COMPLETE / CI PASS  
Date: 2026-09-23  
Branch: `work/v1.54-p10-multiview-completion`  
Closeout CI run: `35818321869`  
Closeout implementation head: `de1201374c7a633dbdb1ff7654520cb79d08212d`

## Purpose

DR8 closes the diagnostic, preview and regression layer for artist-authored P10 drone routes before DR9 packaging/runtime acceptance.

This closeout does not alter Baseline/P9 solver authority.

## DR8A — Route diagnostics

PASS.

Validated contracts:
- deterministic `ConceptGhost.P10DroneRouteDiagnostics.v0.1`;
- exact active-drone count and mission order;
- PATH / SPIN_360 modes;
- expected/emitted frame counts;
- authored and emitted route lengths;
- collision hold/resume statistics;
- clearance metrics;
- P9 coverage and hole-fraction metrics;
- deterministic PASS / WARN / FAIL semantics.

## DR8B — Per-drone final-composite GIF previews

PASS.

Validated contracts:
- exactly one GIF per drone/mission;
- final Gate 5 composites are the preview source;
- all authored frames are included;
- split WAN windows reassemble by global frame index;
- mission isolation prevents cross-drone frame mixing;
- Windows-safe GIF filenames;
- default 640 px maximum width / preserved aspect / 10 fps / infinite loop;
- GIF SHA-256 and ordered source-frame-set SHA-256.

## DR8C — Preview index / ComfyUI output surfacing

PASS.

Validated contracts:
- `ConceptGhost.P10DronePreviewIndex.v0.2`;
- run / scene / source-run identity;
- route-plan / control-manifest / WAN-generation hashes;
- exact mission order and modes;
- per-preview exact global frame range/count;
- GIF filename/subfolder/path/hash;
- Gate 5 fifth output `drone_preview_index_path`;
- WAN manifest output remains slot 2 for Gate 6 compatibility;
- GIFs surface through standard ComfyUI output-image metadata.

## DR8D — Freshness / invalidation

PASS.

Validated contracts:
- route changes invalidate prior preview authority;
- control-manifest changes invalidate prior preview authority;
- WAN setting/context changes invalidate prior preview authority;
- missing/tampered preview index is detected;
- GIF hash mismatch is detected;
- final composite byte mutation is detected;
- stale `drone_previews` package is removed before republishing;
- freshness policy:
  `ROUTE_CONTROL_WAN_CONTEXT_PLUS_EXACT_FINAL_COMPOSITE_BYTES`.

## DR8E — Final aggregate regressions

PASS.

Dedicated suite:
`Experimental/P10_Lab/tests/test_dr8_closeout.py`

The suite locks these cross-stage invariants:

1. **Baseline/P9 isolation**
   - Gate 6 integration operates on a deep copy;
   - original workflow input remains byte-equivalent at the Python object level;
   - Baseline/P9 export node remains unchanged;
   - only the release-facing P10 clone receives the `High Fidelity Split Clean` default.

2. **Artist route identity**
   - two-drone PATH + SPIN_360 plan;
   - deterministic scene/run-bound route hash;
   - exact frame sampling;
   - cross-run route reuse fails closed.

3. **Diagnostics**
   - exact mission order;
   - exact total frame count;
   - collision hold produces WARN rather than silent mutation/failure;
   - unaffected mission remains PASS.

4. **WAN window reassembly**
   - one drone can span several WAN windows;
   - global-frame ordering is preserved;
   - different drones remain isolated.

5. **Preview freshness**
   - preview index is bound to route/control/WAN context;
   - GIF and ordered source-frame hashes are authoritative;
   - post-publication final-composite byte mutation fails closed.

6. **ComfyUI artist editor contract**
   - add/remove drone controls;
   - PATH / SPIN_360;
   - scene reset;
   - artist-authority promotion;
   - stale hash removal;
   - collision-stale state;
   - blocked-segment visualization.

## CI evidence

Workflow now has an explicit step:

`Validate DR8 route-authoring closeout regressions`

Command:
`python -m unittest tests.test_dr8_closeout -v`

Closeout run `35818321869`:
- Ubuntu latest / Python 3.12 — SUCCESS
- Windows latest / Python 3.12 — SUCCESS
- Windows latest / Python 3.14 — SUCCESS

The normal P10 test suite also executes in the same matrix after the explicit closeout gate.

## DR8 exit decision

DR8 is COMPLETE at code/CI level.

Remaining work is DR9:
- build the next complete installer/workflow;
- validate installer and extracted-bundle integrity;
- sync GitHub + Google Drive release mirrors;
- real ComfyUI runtime test of the interactive Top/Side/Front route editor;
- author at least one curved/descending PATH and one SPIN_360 mission;
- inspect per-drone GIFs;
- confirm Gate 4 → Gate 5/WAN → Gate 6 reconstruction on the authored routes.

Gate 7 fusion/free-space work remains after the bounded route-authoring runtime acceptance, per the current roadmap.
