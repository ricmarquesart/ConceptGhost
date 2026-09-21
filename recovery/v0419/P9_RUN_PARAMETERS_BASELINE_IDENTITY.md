# ConceptGhost v0.41.9 — Run Parameters + Baseline Identity

Two runtime needs are addressed.

## Baseline export identity
Frozen Baseline v0.36 predates the P9 scene-contract identity. The modern Maya/export contract now requires a non-empty scene_contract_id. v0.41.9 creates a run-local identity wrapper only when the incoming scene has no contract, then propagates the same ID through camera, canonical geometry, PrimaryMesh, Maya worker and manifests.

This is identity-only:
- camera math unchanged
- geometry unchanged
- scale unchanged
- solver selection unchanged
- new solvers: 0

## Human-readable execution audit
Both Baseline and Refined write:
- <run_id>/RUN_PARAMETERS.txt
- concept_scene/LATEST_RUN_PARAMETERS.txt

The report is refreshed at PRE_EXPORT, PRE_MAYA and FINAL, and records branch/mode, scene identity, Geometry Profile/model parameters, camera/FOV evidence and decision, scale/Known Height, metric evidence, Semantic/depth/refinement, Maya/export contract and final output paths. Heavy tensors are summarized by shape/dtype.

Bundle ZIP SHA-256:
99cb553f6fdb9dff0e57031dc7c834b273c4113c73a75c2871033a6c784e9827
