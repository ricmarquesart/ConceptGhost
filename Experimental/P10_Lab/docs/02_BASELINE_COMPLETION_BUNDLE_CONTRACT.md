# P9 Completion Bundle Contract — P9 = Baseline

## User input

One file only:

`ConceptGhost_P9_CompletionBundle.zip`

The integrated Refined branch will produce this package automatically at the
boundary between P9 and P10. During isolated laboratory testing, Gate 2 may build
the package from an already completed official Baseline/P9 run directory.

## Current authoritative source boundary

ConceptGhost v1.53 already emits the information P10 needs. Gate 2 consumes that
official run pack rather than adding a second P9 export system.

Required source authority:

- `source/source.png`;
- `camera/camera.json`;
- one `maya/ConceptGhost_*_PrimaryMesh.npz`;
- `maya/primary_mesh_payload.json`;
- `manifest.json`;
- `output_index.json`;
- `package/official_outputs_contract.json`.

The current PrimaryMesh NPZ is the preferred authority because it is the exact
modeling mesh already transported to Maya. PLY/OBJ may be produced later as
derivatives for external tools, but P10 must not force P9 to replace its
authoritative NPZ merely to satisfy the laboratory.

## Completion Bundle v0.3 required files

- `manifest.json`
- `source_image.png`
- `camera.json`
- `primary_mesh.npz` for current official v1.53 runs; validated PLY/OBJ remain accepted by the generic loader
- `run_metadata.json`

The manifest records SHA-256 for every required and optional packaged artifact.
The loader re-hashes the bytes on every fresh validation and rejects a mismatch.

## Optional packaged evidence

When present in the official run, Gate 2 carries forward:

- `point_cloud.ply`;
- `geometry_health.json`;
- `primary_mesh_payload.json`;
- `official_outputs_contract.json`;
- `output_index.json`.

Future auxiliary evidence may include depth, confidence, semantics, normals,
boundaries, ground/sky masks and region provenance. Those remain optional until
a later gate formalizes them.

## Manifest identity

The canonical integrated manifest declares:

- `source_stage = "p9"`
- `source_equivalent_to = "baseline"`
- `source_branch_mode = "Refined / P9 Clone"`
- the exact `scene_contract_id`;
- `identity_status = "PASS"`;
- the source manifest schema;
- per-artifact SHA-256.

For isolated laboratory compatibility only, a verified `Baseline / P9` run is
encoded as `source_stage = "baseline"` while still declaring
`source_equivalent_to = "baseline"`.

## Gate 2 source-run validation

Before a Completion Bundle is created, Gate 2 rejects the run if:

- the branch mode is not one of the two approved P9-equivalent branches;
- manifest, camera, canonical geometry or PrimaryMesh disagree on Scene Contract identity;
- the run is not authoritative;
- P10 global-scale override is permitted;
- camera validity fails;
- the official PrimaryMesh is missing or ambiguous;
- official core outputs are missing;
- output-index identity conflicts with the run.

## Reference only

A `.ma` file may be included for audit but is not the technical source of truth between P9 and P10.

## Output after later P10 gates

- completed mesh
- dense cloud
- Maya scene
- defect/provenance maps
- generated-view manifest
- validation report
- reconstruction references

## Identity gate

P10 must reject any input that cannot prove a Baseline-equivalent P9 boundary.
A valid-looking filename is never sufficient authority.
