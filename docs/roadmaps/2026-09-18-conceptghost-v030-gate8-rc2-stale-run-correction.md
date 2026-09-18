# ConceptGhost v0.30 — Gate 8 RC2 / stale-run correction

Date: 2026-09-18

## User-observed verifier FAIL

The user's Gate-8 verifier output showed Standard / stride 3 / missing ViT-G metadata while Maya/FBX normal gates passed.

Investigation proved the verifier selected historical run:

`20260918T195826_428213Z_67686e0e`

That run is pre-v0.30:
- PrimaryMesh schema: `ConceptGhost.PrimarySolverMeshPayload.v0.29`
- Maya worker input schema: `ConceptGhost.MayaWorkerInput.v0.29`
- Maya manifest schema: `ConceptGhost.MayaManifest.v0.28`
- mesher: `standard_transport_stride`
- stride: 3

Therefore the displayed FAIL reproduced the known v0.29 regression and was not a fresh v0.30 runtime result.

## RC2 correction

The Gate-8 RC2 bundle now:
- installs uniquely named `ConceptGhost_Master_v0.30_CANONICAL.json`;
- makes the MASTER node visibly say `v0.30 CANONICAL`;
- writes `%LOCALAPPDATA%\ConceptGhost-v0.30-install.json` with canonical workflow SHA256;
- verifies installed workflow = 26 nodes / 66 links;
- refuses all pre-v0.30 run artifacts in `VERIFY_HIGH_FIDELITY_OUTPUT.bat`;
- requires v0.30 PrimaryMesh, Maya manifest and final manifest schemas before evaluating High Fidelity;
- includes `PREPARE_GATE8_VALIDATION.bat` so a restored old ComfyUI tab is not mistaken for the new graph.

Local validation after the correction:
- compileall: PASS
- pytest: 20 PASS
- canonical workflow: 26 nodes / 66 links
- retired DA3 tokens in active workflow: 0
- stale-run guard regression: PASS

## Gate status

Gates 0–7: completed to the currently testable boundary.

Gate 8 implementation: complete.

Gate 8 final acceptance: PENDING one fresh Windows/Maya run using the versioned v0.30 canonical workflow, followed by `VERIFY_HIGH_FIDELITY_OUTPUT.bat`.

Do not call Gate 8 complete until that fresh run returns full PASS.
