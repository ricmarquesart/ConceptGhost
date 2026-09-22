# ConceptGhost v1.54 P10 — Gate 4 Integrated Refined Preview

This preview is applied to the full proven `ConceptGhost_Master_v1.53.0.json`
from the COMPLETE_INSTALLER. It is not a P10-Lab mini-workflow.

## User-facing behavior

Select the existing **Refined / P9 Clone** mode. The full P9 clone runs as
before. Its official `ConceptGhostExportBundle.run_dir` then feeds the new
**REFINED/P10 · 08 · VISUAL EVIDENCE · ERP + DRONE + HOLES** node.

The node produces tangible evidence:
- P9 3D partial ERP;
- source-authority ERP;
- source-lock mask;
- automatic flight views;
- per-frame raw hole masks;
- top-down trajectory map;
- animated GIF path comparing raw P9 view vs highlighted missing geometry;
- diagnostics with per-path coverage and robust local flight scale.

## Panorama meaning

P9 does **not** contain truthful unseen 360 geometry. Therefore the input ERP is
deliberately partial. Known source/P9 evidence is populated; unknown areas stay
black until Gate 5 WAN completion. A fake full 360 panorama is not created just
to satisfy the SplatKit shape.

## Flight scale correction

The farthest mesh point is not used as the drone radius. Gate 4 uses median
positive canonical `camera_depth` so long streets/outliers do not launch the
camera out of the useful scene.

## Integration safety

Baseline/P9 is untouched. The patch adds one downstream output node only to the
Refined export. The full workflow is generated deterministically from the proven
v1.53 master by `p10_lab.workflow_integration.integrate_gate4_refined_preview`.
