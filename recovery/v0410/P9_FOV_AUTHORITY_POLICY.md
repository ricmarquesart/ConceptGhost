# P9.4 FOV Authority — v0.41.0

v0.41 retires v0.40.2 bounded-threshold relaxation and v0.40.3 ambiguous-median continuation as automatic FOV authority.

## Modes
- AUTO: Atlas, MoGeIndependent and DepthPro provide native FOV seeds. Solver identity has no voting weight. Candidate cameras are evaluated against independent scene evidence.
- MANUAL: artist FOV is sovereign. Default horizontal FOV = **50°**.

## AUTO evidence families
- Depth Surface Orientation: 35%
- Ground ↔ Gravity Consistency: 30%
- Vertical Structure ↔ Gravity: 25%
- Known Height Metric Consistency: 10% when available

Generic same-camera reprojection is excluded because it is circular. Planarity alone is excluded as an FOV discriminator; plane residual is only a fit-quality gate.

## Artist-visible result
The P9.4 node and P9.3 Dashboard expose:
- Selected Solver / Seed
- Native Seed FOV
- Canonical FOV
- Confidence
- per-candidate score / coverage

Known Height remains optional for FOV validation and sovereign for final global scale. Scene metric extents are surfaced in the dashboard.

New solvers added: **0**. Windows/ComfyUI/Maya runtime validation remains pending.
