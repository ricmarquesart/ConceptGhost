# P9 Completion Bundle Contract — P9 = Baseline

## User input

One file only:

`ConceptGhost_P9_CompletionBundle.zip`

The integrated Refined branch produces this package at the boundary between P9 and P10. During isolated laboratory testing, a Baseline-equivalent package is also accepted because P9 is defined to be identical to Baseline.

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

## Optional auxiliary evidence

- confidence
- semantics
- normals
- boundaries
- ground/sky masks
- canonical scene metadata
- region provenance

These fields are not "P9-only refinements." P9 remains Baseline-identical. If any auxiliary evidence is later formalized, it must be compatible with the P9 = Baseline identity.

## Manifest identity

The canonical integrated manifest declares:

- `source_stage = "p9"`
- `source_equivalent_to = "baseline"`

For isolated lab compatibility only, `source_stage = "baseline"` may be accepted as an equivalent source.

## Reference only

A `.ma` file may be included for audit but is not the technical source of truth between P9 and P10.

## Output

- completed mesh
- dense cloud
- Maya scene
- defect/provenance maps
- generated-view manifest
- validation report
- reconstruction references

## Identity gate

P10 must reject or clearly flag an input that claims to be P9 but is not marked Baseline-equivalent.
