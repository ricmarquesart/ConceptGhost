# ConceptGhost v0.30 — Gate 8 Review RC3 Delivery

Date: 2026-09-18

## Trigger
The first RC2 Windows run failed in `ConceptGhostMoGe3Inference` with:

`NameError: _conceptghost_moge3_runtime_root is not defined`

RC3 restores the isolated MoGe-3 runtime locator and worker-tensor bridge and re-audits Gates 1–8.

## Local validation
- compileall: PASS
- pytest: 26 PASS
- workflow: 26 nodes / 66 links
- no active DA3 / DepthAnythingV3 / compare_both / Semantic controls
- packaged-source extraction + regression suite: PASS
- runtime-helper regression: PASS
- real ViT-G RAW -> High Fidelity PrimaryMesh reference proof preserved
- PRE_MAYA topology/normal proof: PASS

Gate 8 runtime acceptance still requires one fresh Windows/Maya RC3 run because Autodesk Maya is not available in the build environment.

## Google Drive
Folder:
https://drive.google.com/drive/folders/1LqeC5SUmKmrBGA4RSKjpNHWWPnog6tF7

Files:
- ConceptGhost_v0.30_GATE8_REVIEW_RC3_COMPLETE.zip
- ConceptGhost_v0.30_GATE8_REVIEW_RC3_SOURCE.zip
- GATES_1_TO_8_REVIEW_RC3.md

## SHA256
```text
e09322e40dd9c123cdb5a258b4ccb3ee6c20a2661bf4e3d23271773fc4604065  ConceptGhost_v0.30_GATE8_REVIEW_RC3_COMPLETE.zip
79b94475aee3eb7f84b10241a2f12a0a220942ce4f3d477893f2f0b30a88442d  ConceptGhost_v0.30_GATE8_REVIEW_RC3_SOURCE.zip
```

## GitHub source authority
The exact RC3 source ZIP is stored in this release folder as ordered base64 parts `SOURCE_ZIP.part*.b64`.
