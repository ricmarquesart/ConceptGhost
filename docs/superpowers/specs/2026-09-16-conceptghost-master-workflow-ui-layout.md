# ConceptGhost Master Workflow — UI Layout Policy

Date: 2026-09-16
Status: Approved visual-direction decision
Project: ConceptGhost

## Decision

`ConceptGhost_Master.json` uses a left-to-right visual flow.

- Left: user controls and camera branch.
- Center: geometry routing, normalization, canonicalization, and reprojection/quality gates.
- Right: run status, standardized outputs, Maya Ghost, and optional mesh outputs.

This is an architectural usability rule, not a cosmetic preference. The workflow must remain readable as DA3, MoGe, Maya, diagnostics, and mesh branches are added.

## Primary canvas zones

### 01 — Master Input & Run Control
Contains the single source-image input and the small set of normal user controls:
- preset;
- camera mode;
- geometry engine;
- Compare Both;
- output switches.

### 02 — Atlas Camera
Contains the camera-solving branch and emits the standardized CameraBundle.

### 03 — Geometry Router
Contains DA3 and MoGe branches. Normal mode runs one engine. Compare Both runs both independently.

### 04 — ConceptGhost Normalizer
Converts engine-specific camera/geometry evidence into CameraBundle, GeometryBundle, CanonicalGeometry, and SceneBundle-compatible data.

### 05 — Reprojection / Quality Gate
Validates canonical geometry against the selected Atlas camera before Maya acceptance.

### 06 — Run Result
Shows PASS / PARTIAL / FAIL and makes Maya Ghost readiness visually obvious.

### 07 — Standard Outputs
Shows the run-bundle outputs and paths: source, camera, diagnostics, geometry, Maya, compare, logs, and manifest.

### 08 — Optional Meshes
Contains Atlas relief, MoGe mesh, and DA3 mesh branches. These remain outside the mandatory success path.

## Readability rules

- User-editable controls stay concentrated at the left edge of the graph.
- Internal processing is grouped by responsibility rather than by individual node type.
- Long connections should be routed through clear lanes/reroute points rather than crossing unrelated groups.
- Engine-native details remain inside their engine group and do not leak into downstream Maya/export groups.
- Downstream groups consume standardized ConceptGhost contracts rather than direct DA3/MoGe internals whenever the contract is available.
- Output and status groups live at the right edge so the graph reads naturally from input to result.
- Development/debug fixtures may expose additional nodes, but the production-facing master workflow should preserve this spatial organization.

## Approved visual direction

```text
LEFT                          CENTER                              RIGHT

Master Input                  Geometry Router                    Run Result
Atlas Camera       ->         Normalizer              ->         Standard Outputs
                              Reprojection Gate                   Maya Ghost
                                                                   Optional Meshes
```

## Related documents

- `docs/superpowers/specs/2026-09-16-conceptghost-master-workflow-design.md`
- `docs/superpowers/plans/2026-09-16-conceptghost-master-workflow-addendum.md`
