# ConceptGhost Master Workflow — UI Layout Policy

Date: 2026-09-16
Status: Approved visual direction, field guidance, Advanced collapse, mandatory Maya Ghost, Max Reference default, and mandatory canonical evidence
Project: ConceptGhost

> Runtime behavior is governed by `2026-09-16-conceptghost-runtime-behavior-policy.md`.

## Decision

`ConceptGhost_Master.json` uses a left-to-right visual flow.

- Left: user controls and camera branch.
- Center: geometry routing, normalization, canonicalization, and reprojection/quality gates.
- Right: run status, standardized outputs, Maya Ghost, and optional mesh outputs.

## Primary canvas zones

### 01 — Master Input & Run Control

Normal user controls:
- source image;
- preset;
- camera mode;
- geometry engine;
- Compare Both;
- optional-output controls where justified.

There is **no Maya Ghost enable/disable control** in the production-facing Master.

There is also **no toggle to disable the Canonical Point Cloud, manifest, reprojection report, or reprojection overlay**. These are core evidence/output artifacts generated automatically by a valid run.

The initial production defaults are:

```text
Preset = Max Reference
Camera = Auto
Geometry = DA3
Compare Both = OFF
```

### 02 — Atlas Camera

Contains camera solving and emits the standardized CameraBundle.

### 03 — Geometry Router

Contains DA3 and MoGe. Normal mode runs one engine. Compare Both runs both independently.

### 04 — ConceptGhost Normalizer

Converts engine-native evidence into standardized CameraBundle, GeometryBundle, CanonicalGeometry, and SceneBundle-compatible data.

The authoritative normalized geometry is referred to in the user-facing documentation as the **Canonical Point Cloud**.

### 05 — Reprojection / Quality Gate

Validates canonical geometry against the selected Atlas camera before Maya acceptance.

Core evidence is saved automatically:
- reprojection report;
- reprojection overlay.

### 06 — Run Result

Shows PASS / PARTIAL / FAIL and makes Maya Ghost readiness visually obvious.

### 07 — Standard Outputs

Shows run-bundle paths for:
- source;
- camera;
- canonical geometry;
- essential diagnostics;
- Maya;
- compare outputs when used;
- logs;
- manifest.

### 08 — Optional Meshes / Extra Diagnostics

Atlas relief, MoGe mesh, and DA3 mesh remain optional and outside the mandatory success path.

Heavy/non-essential diagnostic exports may also be optional. An `Extra Diagnostics` control, if implemented, affects only those additional artifacts and never disables required evidence.

## Readability rules

- User-editable controls remain concentrated at the left edge.
- Internal processing is grouped by responsibility.
- Long connections use clear lanes/reroutes rather than crossing unrelated groups.
- Engine-native details remain inside their engine groups.
- Downstream consumers use ConceptGhost standardized contracts whenever available.
- Output/status groups live at the right edge.
- Critical warnings remain visible even when Advanced groups are collapsed.

## Main versus Advanced controls

### Main controls

Keep visible:
- source image;
- preset — default `Max Reference`;
- camera mode;
- geometry engine;
- Compare Both;
- genuinely optional controls such as optional meshes or extra diagnostics.

Do **not** expose toggles for:
- Maya Ghost;
- Canonical Point Cloud;
- manifest;
- reprojection report;
- reprojection overlay.

### Advanced groups

- `ADVANCED — ATLAS`
- `ADVANCED — DA3`
- `ADVANCED — MoGe`
- future export/mesh Advanced groups only when justified.

All Advanced groups open **collapsed by default**.

Collapsing a group:
- does not disable the engine;
- does not alter configured values;
- never hides a critical run-invalidating warning.

## Mandatory field-help policy

Every user-editable field must explain:

1. **What does this control?**
2. **What does changing it affect?**
3. **What is ideal/recommended?**

When useful, it also states risks/trade-offs.

Normal presentation:
- short one-line hint near the field where practical;
- fuller tooltip/help text;
- if native ComfyUI widgets cannot provide a tooltip, use an adjacent note/help element.

## Preset-aware guidance

The UI communicates:

- `Max Reference` — **default**; highest validated reference-quality configuration, accepting greater runtime/resource cost.
- `Balanced` — reduced cost while maintaining useful reference quality.
- `Fast Test` — rapid iteration and low resource use.

“Highest quality” means highest **validated stable reference quality**. The UI must not imply that numerically maximizing every parameter always improves results.

## Local-processing clarity

Normal production use must not imply any cloud dependency. The source image, camera solve, geometry, canonicalization, reprojection, and Maya Ghost path are intended to execute locally.

Google Drive synchronization used for project documentation/tools is separate from runtime image processing.

## Approved visual direction

```text
LEFT                          CENTER                              RIGHT

Master Input                  Geometry Router                    Run Result
Atlas Camera       ->         Normalizer              ->         Standard Outputs
                              Reprojection Gate                   Maya Ghost (mandatory)
                                                                   Optional Meshes
                                                                   Extra Diagnostics
```

## Related documents

- `docs/superpowers/specs/2026-09-16-conceptghost-master-workflow-design.md`
- `docs/superpowers/specs/2026-09-16-conceptghost-runtime-behavior-policy.md`
- `docs/superpowers/plans/2026-09-16-conceptghost-master-workflow-addendum.md`
