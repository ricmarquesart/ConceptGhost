> **MANDATORY PRIVATE REFERENCE POLICY (2026-09-25)**  
> Before acting on this roadmap/policy document, consult `G:\\My Drive\\ConceptGhost\\Drones\\00_PRIVATE_AUTHOR_REFERENCE_SOURCE_OF_TRUTH_DO_NOT_GITHUB`. Purchased/original reference files remain Google Drive only and must not be copied to GitHub. Concept Art + accepted P9 camera/source authority remain the product authority.

# CG-02 / CG-03 AUTO_LATEST P9 Source Handoff Fix

Date: 2026-09-26  
Status: SOURCE FIX COMPLETE / TARGET-PC RUNTIME ACCEPTANCE PENDING

## Runtime failure reproduced

The isolated CG-02/CG-03 panorama workflow stopped at `ConceptGhostP10ProductionEntryLoader` before panorama execution because `AUTO_LATEST` required `LATEST_PRODUCTION_ENTRY.json`. That pointer is only written after Route Setup commits an `ARTIST_AUTHORED` route.

This ordering is incompatible with the result-first CG pipeline:

`P9 -> CG-02 panorama -> CG-03 panorama validation -> CG-04 camera rails`

CG-02 and CG-03 must not require CG-04 route authority.

## Corrected contract

`AUTO_LATEST` now resolves in this order:

1. If a committed production entry exists, preserve the established behavior and use it.
2. Otherwise discover the newest valid accepted P9 source from existing ConceptGhost/Route Setup evidence and normal ConceptGhost `LATEST_RUN.txt` pointers.
3. Validate that candidate through the existing `validate_official_run` contract.
4. Create a source-only immutable handoff under `conceptghost/p10_source_handoff/<P9_RUN_ID>/source_entry.json`.
5. Freeze/validate the P9 dependency inventory exactly as the route-backed handoff does.
6. Create the P10 attempt with `source_only_entry=true`, `route_plan_sha256=null`, and `route_required_from_stage=CG_04_CAMERA_RAILS`.

No fake artist route and no fake route hash are created.

## Fail-closed boundary retained

The source-only handoff is valid only for the route-independent start of the result-first chain. Its explicit route state is:

- `route_authority = DEFERRED_UNTIL_CG04`
- `route_required_from_stage = CG_04_CAMERA_RAILS`
- deferred route status = `ROUTE_NOT_REQUIRED_FOR_CG02_CG03`

A committed `ARTIST_AUTHORED` route remains mandatory once the workflow enters the camera-rail contract.

## Regression coverage

Added tests verify:

- existing committed-route `AUTO_LATEST` resolution remains unchanged and has priority;
- route-free `AUTO_LATEST` creates a validated P9 source entry for CG-02/CG-03;
- source-only P10 attempts carry no fabricated route hash;
- source-only attempts state that the route becomes mandatory at CG-04.

Source commits:

- `3e87e4c249269fc747bff68986045eb9a2743596` — runtime handoff fix.
- `3c30e79f49bc61bd770856f4e3f3ebd17bbed82b` — regression coverage.

## Evaluation build

Bundle: `ConceptGhost_CG02_CG03_PANORAMA_TEST_v0.4.zip`  
SHA-256: `7a971b011d9bf7377138ac09bf6fff726a4836744a3de1c24471893be644b97f`

Google Drive `ConceptGhost/Storage/Evaluation_Builds` file ID:
`1qiYwMkX8N441su1zns6temDi2unaQE9J`

The v0.4 installer also corrects two result-path display lines in the v0.3 BAT that were accidentally interpreted as commands.

## Acceptance state

This source/package fix does **not** promote CG-02 or CG-03 to DONE.

Next required evidence remains one real target-PC run that physically creates and allows inspection of:

- `RESULTS/CG_02_PANORAMA_360/...`
- `RESULTS/CG_03_PANORAMA_VALIDATION/...`

If CG-03 fails its actual source-lock/seam thresholds, its evidence remains valuable and downstream gates stay blocked.
