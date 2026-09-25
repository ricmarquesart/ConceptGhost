# ConceptGhost R6J — Gate Output Contract

Date: 2026-09-25
Status: SOURCE IMPLEMENTED / TARGET-PC ACCEPTANCE PENDING

## Policy change

A green ComfyUI node no longer proves a Gate passed.

Every Gate must publish its required product under the immutable P9 run:

`<P9_RUN>/GATE_OUTPUTS/<P10_ATTEMPT_ID>/GATE_XX_<NAME>/`

Every published Gate contains:

- `INPUTS/`
- `OUTPUTS/`
- `PREVIEWS/`
- `LOGS/`
- `GATE_STATUS.json`
- `INPUT_MANIFEST.json`
- `OUTPUT_MANIFEST.json`
- `SHA256SUMS.txt`

The P9 run root also receives `GATE_OUTPUT_INDEX.json` and
`LATEST_GATE_OUTPUTS.txt`, beside `RUN_AUDIT_BUNDLE.zip`.

## Status semantics

`runtime_status`: did the code execute?
`functional_status`: did the Gate produce its required product?
`quality_status`: how good is that product?

Low quality alone is not missing output. A poor but non-empty Gate 6
reconstruction can be functional PASS + quality WARN. A missing/empty Gate 6
geometry is functional FAIL. Runtime PASS never overrides functional FAIL.

## Gate 4

Publishes every control-frame PNG, every hidden-area mask, route/camera
manifests, flight GIF, camera-path preview and contact sheets.

## Gate 5

Publishes every raw WAN PNG and every final source-preserved composite PNG,
plus the per-drone GIF previews and view manifest.

## Gate 6

Mandatory inspectable product:

- `sparse_points.ply`
- `dense_points.ply`
- `reconstructed_mesh.ply`
- `reconstructed_mesh.obj`
- `reconstruction_camera_set.json`
- `reconstruction_manifest.json`
- `geometry_quality.json`
- reconstruction logs/previews
- `Gate06_Reconstruction_Diagnostic.ma`

The diagnostic Maya imports the raw P10 reconstruction and materializes sampled
reconstruction cameras. Gate 6 may not close with empty geometry.

## Gate 7

Publishes P9 reference, raw P10 reconstruction, fused candidate, provenance /
reason codes, confidence, free-space constraints, visual summary and
`Gate07_Fusion_Diagnostic.ma`.

The Maya diagnostic references the accepted P9 Maya and separates:
- raw P10 reconstruction;
- accepted P10;
- rejected P10.

Zero accepted P10 is functional FAIL even if Gate 7 runtime is PASS.

## Gate 1–3 backfill

R6J creates explicit historical snapshots for the current attempt. Gate 3 is
intentionally fail-closed: if explicit free-space/conflict products do not exist
at Gate 3, the status remains FAIL instead of borrowing later Gate-7 evidence.

## Existing-run backfill

R6J includes `03_BACKFILL_LAST_RUN_GATE_OUTPUTS.bat`.
It publishes the latest existing Gate 1–7 evidence into the new output tree
without rerunning WAN, COLMAP, MoGe or geometry.

This allows the current target run to be inspected immediately while future runs
publish outputs automatically at Gate boundaries.
