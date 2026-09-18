# ConceptGhost v0.29.1 — DA3Evidence scope hotfix

Observed failure:
`ConceptGhostDA3Evidence -> NameError: geometry_profile is not defined`

Root cause:
v0.29 accidentally inserted `geometry_profile` and `resolved_profile` metadata references inside `ConceptGhostDA3Evidence.build()`, although that node does not receive either value. The High Fidelity profile belongs to the MoGe branch, not DA3Evidence.

Fix:
- remove the two accidental DA3Evidence references;
- keep MoGe-3 Standard / High Fidelity routing unchanged;
- add a scope-regression verifier that parses `nodes.py` and fails if those profile symbols leak into DA3Evidence again;
- current v0.29 users can apply only the ComfyUI payload hotfix; the isolated MoGe-3 runtime and cached ViT-L/ViT-G models do not need reinstalling.

Google Drive complete bundle:
https://drive.google.com/file/d/1H3Pd_o6LcLUXqpPRK_URaSOmLKx8HIcF/view?usp=drivesdk

Google Drive release folder:
https://drive.google.com/drive/folders/1iE_LubFNw2ntU5zHZlhq1n8pHy_9n4cR

SHA256:
- COMPLETE: 6ca63af1b38b749874df0bb2112b3152d2aef3822c125fc74414ec28e4f0a668
- SOURCE: 985de75a9b2efe20184b6bc74487744b8157557692a2402fae85c1476915cb16
