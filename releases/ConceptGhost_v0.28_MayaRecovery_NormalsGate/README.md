# ConceptGhost v0.28 — Maya Output Recovery + Normal Integrity Gates

v0.28 fixes a packaging regression that omitted `custom_nodes/ConceptGhost_Stage68/run_maya_worker.bat`. Without that launcher, ConceptGhost produced only the five pre-Maya intermediates and skipped Autodesk mayapy, so `.ma`, the official FBX, the camera-only FBX, `maya_manifest.json`, and the historical `.fbm` media folder were not generated.

## Restored output contract

A successful run now restores:
- `ConceptGhost_<scene>_Ghost.fbm/`
- `ConceptGhost_<scene>_CameraOnly.fbx`
- `ConceptGhost_<scene>_Ghost.fbx`
- `ConceptGhost_<scene>_Ghost.ma`
- `ConceptGhost_<scene>_Ghost.usda`
- `ConceptGhost_<scene>_PrimaryMesh.npz`
- `ConceptGhost_<scene>_PrimaryTexture.png`
- `maya_manifest.json`
- `maya_worker_input.json`
- `primary_mesh_payload.json`

The build also writes `normal_validation_pre_maya.json`.

## Normal/winding gates

The final triangle topology is authoritative. Normals are derived from the final faces and validated, rather than fixing the symptom by globally reversing the mesh.

Mandatory stages:
1. PRE_MAYA
2. MAYA_LIVE
3. MAYA_REOPEN
4. FBX_ROUNDTRIP

Metrics include total/valid/degenerate faces, camera-facing/away faces, aligned/opposed normals, zero normals, winding reversals, and min/median/p05/p95 dot statistics.

## Recovery without recomputing geometry

`RECOVER_EXISTING_MAYA_OUTPUT.bat` can reuse an already-computed incomplete run containing `maya_worker_input.json`, `PrimaryMesh.npz`, texture and USDA. It runs only the v0.28 Maya/FBX stage plus all normal gates.

## Isolation

The MoGe-3 private runtime remains untouched. MoGe-2, Single View, Multi View/Trellis, ComfyUI Python/Torch/CUDA and unrelated custom nodes are not modified.

Local validation:
- complete package: 20/20 tests PASS
- source package: 19/19 PASS, one pinned-vendor test deselected
- workflow: 33 nodes / 85 links
- active Semantic/SAM tokens: zero

Google Drive complete package:
https://drive.google.com/file/d/1CJjxSzStdyp68utjbrINXyL-mQSfLTpR/view?usp=drivesdk

SHA256 COMPLETE:
`8191c1a3ecfd7f7e6989fb361ce81134652b2d74fdfb30bae50ac84f4a33b861`

SHA256 SOURCE:
`6df48cce5c9962c6070d2cac43d3d243d53ef8c65bf4372202dccff45b657275`
