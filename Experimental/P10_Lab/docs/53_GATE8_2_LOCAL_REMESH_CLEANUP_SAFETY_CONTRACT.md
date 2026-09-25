# ConceptGhost P10 — Gate 8.2 Local Remesh / Cleanup Safety Contract

Status: **SOURCE/CI IMPLEMENTATION — runtime promotion intentionally blocked**

Branch: `work/v1.54-p10-gate8-source`

Upstream freeze point: `19fe7066da92233d234adac056863420c052257c`

## Why Gate 8.2 exists

Gate 8.1 identifies bounded defect regions but intentionally does not edit geometry. Gate 8.2 turns that diagnosis into an explicit cleanup/remesh **preview plan** while preserving the project authority rules:

- P9 remains identical to the accepted Baseline contract.
- Gate 7 protected-fusion output remains a non-official candidate.
- CONFIRMED_FREE may nominate false P10 candidate faces for removal in a non-official preview only.
- VALID_OPENING is always preserved and never filled.
- UNKNOWN is not FREE and can only nominate a future local-remesh region; it cannot authorize deletion or filling by itself.
- LOW_CONFIDENCE and CONFLICT regions are held until stronger evidence exists.
- No source/CI Gate 8.2 operation may change official geometry.

## Structural controls

Gate 8.2 hard-locks the requested safety posture:

- **Structural Analysis: ON**
- **Structural Preview: ON**
- **Apply Structural Regularization: OFF**

Passing `apply_structural_regularization=True` fails closed with a `ContractError`.

## New source contract

Module:

`Experimental/P10_Lab/p10_lab/gate8_local_remesh.py`

Primary function:

`plan_gate8_local_remesh_cleanup(...)`

Output schema:

`ConceptGhost.P10Gate8LocalRemeshCleanupPlan.v0.1`

The output includes a deterministic NPZ preview contract with:

- `p10_face_preserve_mask`
- `p10_face_cleanup_preview_remove_mask`
- `p10_face_hold_mask`
- `p10_face_supported_mask`
- inherited Gate 7 reason/confidence evidence
- bounded UNKNOWN missing-surface voxel keys

No mesh is rewritten by this source checkpoint. The masks are instructions for a later preview/apply layer and therefore cannot silently become official geometry.

## Region policy

| Gate 8.1 class | Gate 8.2 behavior |
| --- | --- |
| SUPPORTED_SURFACE | preserve |
| VALID_OPENING | preserve; no fill |
| FALSE_SURFACE_IN_CONFIRMED_FREE | nominate removal in non-official preview only |
| MISSING_SURFACE_UNKNOWN | local-remesh plan only; requires new supported boundary |
| LOW_CONFIDENCE_SURFACE | hold; no automatic edit |
| CONFLICT_REGION | hold; stronger evidence required |

## Promotion locks

Gate 8.2 emits:

- `preview_candidate_is_official_geometry=false`
- `official_geometry_changed=false`
- `p9_authority_changed=false`
- `destructive_cleanup_performed=false`
- `automatic_geometry_edit_allowed=false`
- `ready_for_gate8_3_source_only=true`
- `ready_for_runtime_promotion=false`

Runtime promotion remains blocked by:

1. Gate 7 / R6F target-PC acceptance.
2. Gate 8.2 Structural Preview runtime acceptance with Apply OFF.

This branch intentionally isolates Gate 8 source development from the frozen R6F12 target-PC candidate on `work/v1.54-p10-multiview-completion`.

## Acceptance evidence

Focused tests cover:

- exact false-surface cleanup-preview mask;
- preservation/hold masks;
- valid-opening no-fill policy;
- UNKNOWN remesh requiring new support;
- hard rejection of Apply Structural Regularization ON;
- hard rejection of upstream official-geometry mutation;
- face-region identity mismatch;
- source tokens that keep the non-destructive policy explicit.

Next bounded subgate after CI acceptance: **Gate 8.3 — UV preservation/recovery source contract**. Gate 8.3 may be developed source-only, but no runtime promotion may bypass the blockers above.
