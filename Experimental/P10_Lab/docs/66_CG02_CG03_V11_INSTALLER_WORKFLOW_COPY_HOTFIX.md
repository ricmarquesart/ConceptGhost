# CG-02 / CG-03 Panorama v1.1 — Installer Workflow Copy Hotfix

## Root cause

The v1.0 package inherited the v0.6 installer. That installer still referenced:

`02_ConceptGhost_CG02_CG03_PANORAMA_v0.6.json`

but v1.0 contained:

`02_ConceptGhost_CG02_CG03_PANORAMA_v1.0.json`

Therefore the custom node payload updated successfully and the installer then failed at the workflow-copy stage with:

`[FAIL] Could not copy workflows.`

## v1.1 fix

- installer references `02_ConceptGhost_CG02_CG03_PANORAMA_v1.1.json`;
- source workflow existence is checked explicitly;
- all standard ComfyUI workflow directories are attempted;
- an unwritable candidate is WARN-only until all candidates fail;
- the copied file is verified;
- verifier checks the v1.1 workflow;
- graph/panorama behavior is unchanged from v1.0.

## Release

- Drive file id: `1rFL6Yt4F3qXOeo-tE_c47WWyEnRkQU-K`
- SHA-256: `5a234a0e30125f4a829ddcc4cba865864ba7d3fae37b404572ccac6b65604211`
