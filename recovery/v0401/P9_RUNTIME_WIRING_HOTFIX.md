# v0.40.1 runtime-wiring hotfix

Observed on the first real ComfyUI runtime attempt of v0.40.0:

- Refined node `ConceptGhostMoGeEvidence` had mandatory input `atlas_fov_x_deg` disconnected.
- Stable branch already had the equivalent connection.
- Hotfix adds only the missing Refined workflow edge:
  `ConceptGhostCameraRouter.atlas_fov_x_deg -> ConceptGhostMoGeEvidence.atlas_fov_x_deg`.
- Algorithms changed: **no**.
- New solvers: **0**.
- Canonical bundle SHA-256: `02d261b331970a9569beaf6aff6b56579e88d44e183cacec458d72979a987780`.
- Runtime acceptance remains pending the next Windows/ComfyUI/Maya execution.
