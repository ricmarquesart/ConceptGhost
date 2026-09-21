# Baseline Completion Bundle Contract

## User input

One file only:

`ConceptGhost_Baseline_CompletionBundle.zip`

## Required

- `manifest.json`
- `source_image.png`
- `camera.json`
- `primary_mesh.ply` or `primary_mesh.obj`
- `run_metadata.json`

## Strongly recommended

- `point_cloud.ply`
- depth map / array
- source material references
- geometry-health report

## Optional future P9 enrichment

- confidence
- semantics
- normals
- boundaries
- ground/sky masks
- canonical Scene Contract
- region provenance

The P10 laboratory must still start if every P9-only optional field is absent.

## Reference only

A `.ma` file may be included for audit but is not the technical source of truth between Baseline and P10.

## Output

- completed mesh
- dense cloud
- Maya scene
- defect/provenance maps
- generated-view manifest
- validation report
- reconstruction references
