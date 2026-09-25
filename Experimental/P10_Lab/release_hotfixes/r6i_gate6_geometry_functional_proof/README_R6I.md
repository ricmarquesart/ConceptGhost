# ConceptGhost R6I — Gate 6 Geometry Functional Proof r1

This package reopens Gate 6 as a functional acceptance boundary.

Gate 6 must deliver a non-empty new 3D reconstruction from the existing
drone/WAN images before Gate 7 is allowed to filter or combine it with P9.

## Run order

1. `01_APPLY_GATE6_GEOMETRY_PROOF.bat`
2. `02_VERIFY_GATE6_GEOMETRY_PROOF.bat`
3. `03_RESUME_LAST_GATE6.bat`

The resume helper reuses the latest existing Gate 4 camera manifest and Gate 5
WAN output. It does not regenerate WAN.

## Expected Gate 6 output

Inside the P10 attempt:

`gate6/gate6_output/GATE6_RAW_P10_GEOMETRY.ply`
`gate6/gate6_output/GATE6_RAW_P10_GEOMETRY.obj`
`gate6/gate6_output/GATE6_DENSE_POINTS.ply`
`gate6/gate6_output/GATE6_OUTPUT_MANIFEST.json`

A compact copy of the raw mesh is also written beside the P9 run under:

`<P9_RUN>/P10_GATE6_OUTPUT/<p10_attempt_id>/`

This output is BEFORE Gate 7. Gate 7 cannot delete or hide it.

After applying the package, restart ComfyUI before using Workflow 02 normally.
The Production workflow is labeled with GATE 4 / GATE 5 / GATE 6 groups and
each group identifies its gate output.

R6I does not change P9 authority, existing WAN images, MoGe runtime, shared
ComfyUI Python packages or the RTX 2080 Ti runtime stack.
