# R6K r2 — Automatic Gate Outputs + Maya Centimeter Bridge

Date: 2026-09-25 UTC

## Target-PC finding

The artist compared P9 and the Gate 6 reconstruction directly in Maya and found
that the Gate 6 reconstruction appeared approximately two orders of magnitude
smaller. The accepted P9 Maya export is authored in centimeters while canonical
P9 geometry is metric. The P9 Maya manifest records a 100.0 authoring factor.

The R6J diagnostic scene imported canonical P10 meter-valued OBJ coordinates
directly into a centimeter Maya scene and copied camera translations without the
meter-to-centimeter bridge. This made the diagnostic comparison misleading even
though the canonical reconstruction itself remained in P9-world meters.

This does NOT explain the full quality failure: the artist manually scaled the
P10 result and still could not align it to useful P9 holes. The old reconstruction
remains artist-rejected.

## R6K correction

Canonical geometry stays untouched in meters.

Maya-facing diagnostics now materialize centimeter-only representations:

- Gate 6: reconstructed_mesh_MAYA_CM.obj
- Gate 7: P10_reconstructed_mesh_MAYA_CM.obj
- Gate 7: P10_ACCEPTED_FILL_MAYA_CM.obj
- Gate 7: P10_REJECTED_MAYA_CM.obj
- Gate 7: P9_PLUS_P10_FILLED_CANDIDATE_MAYA_CM.obj

Camera translations written into diagnostic Maya ASCII are also multiplied by
100. Rotations and intrinsics are not rescaled.

Gate07_Fusion_Diagnostic.ma exposes four separate namespaces:
- P9_ORIGINAL;
- P9_PLUS_P10_FILLED_CANDIDATE;
- P10_RAW_RECONSTRUCTION;
- P10_ACCEPTED_FILL.

This supports both full original-vs-filled comparison and fill-only provenance inspection.

## Automatic output contract

Future Workflow 02 production runs must not depend on a manual backfill BAT.

- Gate 6 closeout publishes Gate 1-6.
- Gate 7 fresh runtime publishes Gate 7.
- Gate 7 resumed runtime also republishes Gate 7 before returning.
- Workflow 02 is verified to contain Reconstruction Runtime -> Gate 7 Runtime.
- Output root remains <P9_RUN>/GATE_OUTPUTS/<P10_ATTEMPT_ID>/.

The manual R6J backfill remains a recovery tool for historical attempts only.

## Acceptance

R6K fixes inspection, publication and unit parity. It does not promote the
current target-PC reconstruction to accepted geometry. Gate 8 remains blocked.
