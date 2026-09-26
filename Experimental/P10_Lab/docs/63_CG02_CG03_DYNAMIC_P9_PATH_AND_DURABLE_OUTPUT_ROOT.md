> **MANDATORY PRIVATE REFERENCE POLICY (2026-09-25)**  
> Purchased/original author-reference files remain Google Drive only and must not be copied to GitHub. Concept Art + accepted P9 camera/source authority remain the product authority.

# CG-02 / CG-03 Dynamic P9 Path + Durable Output Root

Date: 2026-09-26  
Status: SOURCE + EVALUATION BUNDLE COMPLETE / TARGET-PC ACCEPTANCE PENDING

## Why this change exists

The accepted P9 workflow does not use one fixed run path. Workflow 01 exposes `output_root` and `scene_name`, and the exporter creates a unique run directory below that selection. A real target-PC example used:

`G:\My Drive\ConceptGhost\Outputs\ConceptGhost_90frames\concept_scene_90frames\20260925T235541_033332Z_a723ab75`

The scene root also owns `LATEST_RUN.txt`, which points to the currently selected/latest P9 run.

CG-02/CG-03 must therefore discover P9 from the workflow's own pointer contract rather than hard-coding an Output ID, Scene Name, Run ID, or a specific drive letter.

## AUTO_LATEST_P9

The panorama loader now supports `AUTO_LATEST_P9`.

Resolution policy:

1. Probe configured/default ConceptGhost output roots.
2. On Windows, probe mounted drive letters for `My Drive\ConceptGhost\Outputs`.
3. Search bounded scene-local `LATEST_RUN.txt` locations.
4. Read the target run directory from the pointer.
5. Validate the target through the existing official P9 run contract.
6. Create a source-only handoff for CG-02/CG-03.
7. If the artist uses a completely non-standard root, an explicit P9 run directory or `LATEST_RUN.txt` remains accepted.

The obsolete route-backed Production workflow is not required for this stage.

## Durable P10 output policy

The accepted P9 run remains immutable.

P10 durable data is now written beside the P9 scene:

`<P9_SCENE_ROOT>\P10\p10_attempts\<P9_RUN_ID>\<P10_ATTEMPT_ID>\RESULTS`

Gate-output evidence is likewise written under:

`<P9_SCENE_ROOT>\P10\GATE_OUTPUTS\<P10_ATTEMPT_ID>`

The ComfyUI C: output tree is limited to small locator JSON files such as:

`...\ComfyUI-Shared\output\conceptghost\p10_locators\LATEST_P10_RUN.json`

Those locator files exist only so helper BATs can print/open the real durable result path.

## Evaluation bundle v0.5

Bundle:

`ConceptGhost_P9_PLUS_CG02_CG03_TEST_v0.5.zip`

SHA-256:

`375b78aeb201258ce235fa4ede28a2725b6d3272a5fd82f9a5c9ff8a0a6b1bdc`

Google Drive Evaluation_Builds file ID:

`1NaSP0dqJbBMUAGGrZqo0hxelvos4Cr4Z`

The bundle contains exactly two user workflows:

- `01_ConceptGhost_P9_MASTER_REQUIRED_v1.53.0.json`
- `02_ConceptGhost_CG02_CG03_PANORAMA_v0.5.json`

The old `02_ConceptGhost_P10_PRODUCTION.json` is intentionally not included.

Workflow 01 is byte-identical to the proven R6K P9 Master workflow.

## Source commits

- `0728a9d114ccebc9ff2cc403f0a0d08090028d6d` — Gate outputs moved outside immutable P9 run.
- `10163b7cf3e58edce8edc14e69b3ddbc01673a9d` — dynamic Output ID / Scene pointer discovery.
- `31318c3fa36af9f1cfda44ecdbb57ba6c69a8ffc` — source handoff stored beside P9 scene.
- `d535ba8d5b5b93a174dfaf0459343200f34e58d7` — P10 attempts stored beside selected P9 scene.
- `fbef2547e3aa16a8d8136361c9ecadd7553217e9` — local/scene result locators.
- `dc55f557ee89bb3db59ba81970b2ec106628519a` — explicit `AUTO_LATEST_P9` mode.
- `7b0af3df0c0908c3fb8aaf1a1a54af5244498f8c` — dynamic-path and sibling-storage regression tests.

## Acceptance state

No CG gate is promoted by packaging alone.

Next target-PC evidence is still:

- CG-02 physical panorama outputs.
- CG-03 source-lock / ERP seam validation.
- confirmation that the resolved P9 run shown by the loader is the intended run.
- confirmation that durable outputs appear under the P9 scene's sibling `P10` folder.
