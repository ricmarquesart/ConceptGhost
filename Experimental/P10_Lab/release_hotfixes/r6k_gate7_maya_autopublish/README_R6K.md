# ConceptGhost R6K r2 — Gate 7 Maya Comparison + Automatic Gate Outputs

R6K fixes two separate problems discovered on the target PC.

## 1. Future outputs are automatic

New Workflow 02 executions do **not** require the old manual
03_BACKFILL_LAST_RUN_GATE_OUTPUTS.bat step.

Gate 6 publishes Gate 1-6 at reconstruction closeout.
Gate 7 publishes Gate 7 on both fresh and resumed executions.

Canonical location:

<P9_RUN>/GATE_OUTPUTS/<P10_ATTEMPT_ID>/

## 2. Maya diagnostic scale is explicit

P9/P10 canonical geometry is stored in meters.
The accepted P9 Maya scene is authored in centimeters.

Previous Gate 6/7 diagnostic OBJ/camera imports used meter numbers directly in a
centimeter Maya scene, making P10 appear 100x too small. R6K keeps canonical
geometry unchanged and creates Maya-only x100 representations.

Gate 6 adds:

- reconstructed_mesh_MAYA_CM.obj
- Gate06_Reconstruction_Diagnostic.ma

Gate 7 adds:

- P10_reconstructed_mesh_MAYA_CM.obj
- P10_ACCEPTED_FILL_MAYA_CM.obj
- P10_REJECTED_MAYA_CM.obj
- P9_PLUS_P10_FILLED_CANDIDATE_MAYA_CM.obj
- Gate07_Fusion_Diagnostic.ma

The Gate 7 Maya scene references the immutable P9 Maya scene and keeps:
- P9_ORIGINAL
- P10_RAW_RECONSTRUCTION
- P10_ACCEPTED_FILL

as separate namespaces. This lets the artist toggle P9 and the reconstructed fill
independently before any later cleanup/final fusion.

## Important

The x100 correction fixes Maya inspection only. It does not claim that the
current COLMAP reconstruction is geometrically good. The prior target-PC run is
still artist-rejected because the raw reconstruction did not correspond to the
expected holes.

R6K therefore improves observability and prevents the diagnostic scale mismatch
from hiding the real reconstruction-quality problem. Gate 8 remains blocked.
