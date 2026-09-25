# Gate 8.1 — Defect Analysis & Bounded Repair Regions — Checkpoint

Date: 2026-09-25 UTC  
Status: SOURCE/CI COMPLETE — runtime promotion blocked until Gate 7/R6F5 target-PC acceptance

## Purpose

Gate 8.1 is diagnostic only. It converts Gate 7 evidence into bounded repair regions without editing official geometry.

## Frozen taxonomy

- SUPPORTED_SURFACE
- VALID_OPENING
- FALSE_SURFACE_IN_CONFIRMED_FREE
- MISSING_SURFACE_UNKNOWN
- LOW_CONFIDENCE_SURFACE
- CONFLICT_REGION

## Inputs

- Gate 7.4 protected-fusion candidate + per-face reason codes;
- Gate 7.3 free-space constraints (CONFIRMED_FREE / UNKNOWN / CONFLICT);
- Gate 7.2C geometry-confidence virtual-hole evidence;
- P10 pre-fusion mesh in P9 canonical world coordinates.

## Implemented behavior

- Gate 7 face reasons are translated into Gate 8 defect classes.
- Adjacent actionable faces are grouped into bounded connected regions.
- CONFIRMED_FREE-veto surface regions also emit a companion VALID_OPENING region whose action is PRESERVE_NO_FILL.
- Virtual-hole confidence samples become MISSING_SURFACE_UNKNOWN only when their voxel is UNKNOWN; CONFIRMED_FREE is never converted into missing-surface authority.
- CONFLICT regions cannot trigger automatic edits.
- LOW_CONFIDENCE regions are candidates for later local remesh but are not automatically modified.
- Large connected components keep exact NPZ region IDs even when verbose JSON face-index lists are truncated.

## Safety contract

- official_geometry_changed = false
- p9_authority_changed = false
- destructive_cleanup_performed = false
- automatic_geometry_edit_allowed = false
- confirmed_free = NEVER_FILL_AUTOMATICALLY
- unknown = NOT_FREE_NOT_A_DELETION_AUTHORITY
- conflict = NO_AUTOMATIC_EDIT

## Source

- `Experimental/P10_Lab/p10_lab/gate8_defect_analysis.py`
- `Experimental/P10_Lab/tests/test_gate8_defect_analysis.py`

## Validation

ConceptGhost Tests run for the G8.1 implementation: SUCCESS across the CI matrix.

## Next

G8.2 source-only:
1. bounded local remesh/cleanup contract;
2. safety gates around source-observed HIGH-confidence geometry;
3. Structural Analysis + Preview ON by default;
4. Apply Structural Regularization OFF by default;
5. no promotion into the runtime validation bundle until Gate 7/R6F5 is accepted on the target RTX 2080 Ti.
