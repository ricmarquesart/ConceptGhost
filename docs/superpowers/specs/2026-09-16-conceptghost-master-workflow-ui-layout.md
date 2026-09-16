# ConceptGhost Master Workflow — UI Layout Policy

Date: 2026-09-16
Status: Approved visual-direction and field-guidance decisions
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

## Main versus Advanced controls

The production-facing master workflow separates normal-use controls from engine-specific tuning.

### Main controls
Keep visible and easy to understand:
- source image;
- preset;
- camera mode;
- geometry engine;
- Compare Both;
- output switches.

### Advanced groups
Keep engine-specific tuning in clearly marked groups:
- `ADVANCED — ATLAS`;
- `ADVANCED — DA3`;
- `ADVANCED — MoGe`;
- later optional export/mesh-specific advanced groups when required.

Advanced parameters remain accessible, but should not dominate normal workflow use.

## Mandatory field-help policy

Every user-editable field must include concise guidance. No exposed setting may rely on the user already knowing Atlas, DA3, MoGe, camera intrinsics, depth filtering, reprojection, MayaUSD, or mesh terminology.

For every exposed field, the UI/documentation must answer three questions:

1. **What does this control?** — plain-language description of the parameter.
2. **What does changing it affect?** — practical effect on camera, geometry, quality, runtime, memory, filtering, export, or reliability.
3. **What is ideal for normal use?** — recommended/default value or preset, including when a different value is appropriate.

Where useful, also include a short warning for risky values or known trade-offs.

### Example

```text
Confidence Threshold: 0.10

What it controls:
Removes DA3 points whose confidence is below the selected value.

Effect:
Higher values produce cleaner geometry but can remove useful surfaces.
Lower values preserve more points but may increase noise.

Recommended:
0.10 for Balanced. Increase only when low-confidence noise is visibly harmful.
```

### Presentation rule

The normal canvas should remain compact. Field guidance should therefore use a two-level presentation:

- a short always-visible one-line hint beside or below the field when practical;
- a fuller tooltip/help description for the effect, recommended value, and trade-offs.

If ComfyUI limitations prevent a true tooltip for a specific field, the same information must be provided through an adjacent note/help node or clearly linked field reference. Missing explanation is not acceptable simply because a native widget lacks tooltip support.

### Preset-aware recommendations

When a recommended value depends on the selected preset, the guidance should say so explicitly, for example:

- `Fast Test`: prioritize speed and low resource use;
- `Balanced`: default recommendation for normal work;
- `Max Reference`: prioritize reference fidelity even when runtime and file size increase.

The UI should distinguish **recommended/default** from merely **allowed** values.

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
