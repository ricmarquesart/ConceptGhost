# v0.36 Isolated Runtime A/B Test

Date: 2026-09-25 UTC  
Status: PACKAGE BUILT / STATIC VALIDATION PASS / TARGET-PC RUNTIME TEST PENDING

## Purpose

Determine whether the recent MoGe/Triton/FlexGEMM runtime changes are a primary cause of the PrimaryMesh topology regression.

This diagnostic holds the **current Turing-compatible runtime dependency stack constant** while restoring the **frozen v0.36 P9 code**. This is a controlled A/B test against the current R6F12 quality-restore candidate.

## Package

`ConceptGhost_v0.36_ISOLATED_RUNTIME_AB_TEST_r1`

Google Drive:
`ConceptGhost/Storage/Evaluation_Builds/ConceptGhost_v0.36_ISOLATED_RUNTIME_AB_TEST_r1`

ZIP:
`ConceptGhost_v0.36_ISOLATED_RUNTIME_AB_TEST_r1.zip`

ZIP SHA-256:
`7e65718b99499bf1b5863baf976b02cb838339885d97dbf84dbd6d74b9014e08`

## Isolation contract

The diagnostic does not replace the normal production paths.

Normal paths preserved:
- `%LOCALAPPDATA%\ConceptGhost-MoGeRuntime-v1`
- `custom_nodes\ConceptGhost_Stage68`
- normal ConceptGhost workflow folder
- normal ConceptGhost output root

Diagnostic paths:
- runtime: `%LOCALAPPDATA%\ConceptGhost-MoGeRuntime-v036-ABTEST`
- custom node package: `ConceptGhost_Stage68_V036_Isolated`
- registry suffix: `_V036_ISOLATED`
- workflow folder: `ConceptGhost_v036_AB_TEST`
- output root: `%USERPROFILE%\ConceptGhost_Output_v036_ABTEST`

The installer hashes the normal `ConceptGhost_Stage68/nodes.py` before and after the isolated payload copy and fails if it changes.

## Controlled runtime

The production inference worker remains the frozen v0.36 `moge_worker.py`.

The runtime compatibility layer is the current Turing-supported stack:
- Python 3.11.9 embedded
- Torch 2.6.0
- torchvision 0.21.0
- CUDA wheel index cu124
- triton-windows >=3.2,<3.3
- R6F11 FlexGEMM/Triton 3.2 compatibility bridge

The bundled MoGe source is the exact frozen v0.36 source archive:
`b9a28e6a1aa86bd23399f995feb9d496a461405fe22b53b9878c21b48d46fe6d`.

This is also the MoGe source SHA recorded by the current Turing runtime. Therefore the test changes the runtime dependency compatibility layer while preserving the underlying MoGe source and frozen v0.36 P9 path.

## Interpretation

- v0.36 isolated GOOD + current R6F12 GOOD: P9 topology regression is sufficient to explain the failure; runtime change is not required.
- v0.36 isolated GOOD + current R6F12 BAD: runtime remains the strongest suspect.
- v0.36 isolated BAD: runtime remains implicated; next step is a second isolated pinned runtime matrix.

## Future runtime replacement

If the runtime is confirmed as the cause, P9/P10 functionality can remain intact. ConceptGhost already crosses the runtime boundary through a worker request/result contract. A replacement runtime should preserve that contract while the higher-level route editor, diagnostics, canonical camera, multiview reconstruction, provenance and Gate 7/8 logic remain unchanged.
