# ConceptGhost v0.31.1 — PrimaryMesh Authority / Maya-FBX Parity RC1

## Verifier correction
The first v0.31 RC1 install could fail `VERIFY_CONCEPTGHOST.bat` with `v0.31 workflow profile/default contract missing` even when the installed workflow was correct.

Root cause: the verifier searched the serialized Comfy workflow JSON for the inactive combo option `"Low Resolution"`. Comfy serializes the selected combo value (`"High Fidelity"`) in `widgets_values`; the available options live in the node implementation.

v0.31.1 validates the workflow structurally instead:
- exactly one `ConceptGhostMasterConfig`;
- exactly one `ConceptGhostGeometryProfile`;
- exactly one `ConceptGhostHFVariantExporter`;
- serialized default `MoGe-3`;
- serialized default `High Fidelity`;
- profile options are validated against installed node code.

No geometry, PrimaryMesh, Maya, FBX, UV, normal, camera, or material quality path was downgraded by this verifier fix.

## Local validation
- compileall: PASS
- pytest: 40 PASS
- workflow: 27 nodes / 68 links
- structural verifier regression: PASS

## Google Drive
Full COMPLETE and SOURCE bundles are stored in:
https://drive.google.com/drive/folders/1bdFZChQt4uy0eIeMoIkbj7iTJkBZfgE1

## Runtime still pending
Autodesk Maya runtime validation remains user-side for High Fidelity, High Fidelity Split Clean, and GhostFullScene.fbx round-trip.
