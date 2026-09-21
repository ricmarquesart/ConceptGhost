# ConceptGhost v0.41.10 — Legacy Workflow Compatibility Layer

A frozen ComfyUI workflow JSON freezes graph topology and widget values, but it does **not** freeze the Python implementation registered for each custom-node type.

Observed case:
- the user loaded the original frozen `ConceptGhost_Master_v0.36.json`;
- that workflow has no `scene_contract_id` input because it predates P9;
- the currently installed `ConceptGhostExportBundle` / Maya worker is newer and requires a Scene Contract identity;
- result: `[MAYA_WORKER_FINAL] missing scene_contract_id`.

Compatibility policy:
- existing P9 Scene Contract IDs are preserved;
- pre-P9 `ConceptGhost.SceneBundle` schemas older than v0.38 may receive a run-local **identity-only** compatibility contract;
- the adapter may not change camera math, geometry, scale, solver output, model settings or artist input;
- modern v0.38+ SceneBundle missing its required contract remains fail-closed;
- historical workflow JSONs are preserved by the installer instead of deleting the ConceptGhost workflow folder;
- the exact user-supplied v0.36 workflow is included in the package regression fixture (SHA-256 `adef327696630fbdf7b39d0c6429be2f4a1290d26fac352b63fa396d57afe4ef`).

This moves backward compatibility to the installed runtime boundary, where it belongs. Old JSON files do not need to be rewritten.
