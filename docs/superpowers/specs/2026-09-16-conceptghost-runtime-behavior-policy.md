# ConceptGhost — Runtime Behavior Policy

Date: 2026-09-16
Status: Active design policy — camera Auto, geometry selection, Compare Both behavior, preset scope/default, mandatory Maya Ghost, and mandatory canonical evidence approved
Project: ConceptGhost

> Where this policy conflicts with earlier high-level wording in the Master Workflow Architecture, this policy is authoritative until the final architecture spec is consolidated.

## Purpose

Define deterministic runtime behavior for the user-facing `ConceptGhost_Master.json`.
This document complements the architecture, roadmap, and UI-layout specifications.

## 1. Camera control

User-facing camera choices:
- `Auto`
- `Atlas Learned`
- `Atlas VP`

### 1.1 `Camera = Auto` — approved behavior

```text
1. Run Atlas Learned
2. Evaluate the camera-quality acceptance criteria
3. If Atlas Learned PASSES:
      use Atlas Learned
4. If Atlas Learned FAILS:
      run Atlas VP as fallback
5. If Atlas VP PASSES:
      use Atlas VP and record the fallback
6. If both fail:
      camera stage FAIL
      preserve diagnostics
      do not publish a valid Maya Ghost
```

`Auto` must never silently choose an unvalidated camera.

### 1.2 Explicit camera modes

If the user selects `Atlas Learned`, ConceptGhost runs that requested solver and does not silently replace it with Atlas VP.

If the user selects `Atlas VP`, ConceptGhost runs Atlas VP directly.

## 2. Camera-quality decision

The exact numerical/visual thresholds are defined from Stage 3 evidence and benchmark scenes before the production Master Workflow is frozen.

Fixed policy:
- a solver must pass the documented quality gate before becoming authoritative;
- fallback occurs because the primary solver failed the gate;
- quality-gate evidence is preserved.

## 3. Camera provenance

Every run records at minimum:

```text
camera.requested_mode
camera.primary_solver
camera.primary_status
camera.fallback_attempted
camera.fallback_reason
camera.final_solver
camera.final_status
```

The user-facing result clearly shows the solver actually used.

## 4. Geometry control — approved V1 behavior

V1 deliberately has no `Geometry = Auto`.

Choices:
- `DA3` — default geometry engine
- `MoGe`

`Compare Both` controls whether the alternate engine is also executed.

### 4.1 Default geometry

```text
Geometry = DA3
Compare Both = OFF
```

### 4.2 No silent geometry fallback

DA3 is not silently replaced by MoGe, and MoGe is not silently replaced by DA3.

The selected engine is part of the reproducible run configuration.

### 4.3 Compare Both remains comparison, not Auto

```text
selected engine = primary branch
alternate engine = secondary comparison branch
both execute independently
both preserve native outputs
both normalize independently
no automatic fusion
no hidden engine substitution
```

## 5. Compare Both — primary failure / secondary success policy

Example:

```text
Geometry = DA3
Compare Both = ON

DA3  = FAIL
MoGe = PASS
```

Result:

```text
run.status = PARTIAL
DA3 remains requested/primary
MoGe outputs are preserved and reported as PASS
MoGe is not promoted to primary
no authoritative Maya Ghost is published from MoGe in that run
```

To make MoGe authoritative, the user starts a new explicit run with `Geometry = MoGe`.

The reverse case follows the same rule.

Required provenance includes:

```text
geometry.requested_engine
geometry.primary_engine
geometry.primary_status
geometry.secondary_engine
geometry.secondary_status
geometry.secondary_usable
geometry.promoted_to_primary = false
run.status
maya_ghost.authoritative
```

## 6. Preset scope and default — approved V1 behavior

Presets control **quality, speed, resource use, filtering, and output density**. They do not choose Camera, DA3/MoGe, or Compare Both.

User-facing presets:

- `Max Reference` — **DEFAULT**
- `Balanced`
- `Fast Test`

### 6.1 Default policy

ConceptGhost opens with:

```text
Preset = Max Reference
Geometry = DA3
Compare Both = OFF
Camera = Auto
```

The default prioritizes the **highest validated reference quality available in the current ConceptGhost version**, even when this costs more processing time, VRAM/RAM, disk usage, or point-cloud size.

`Max Reference` means the highest-quality **validated and stable** settings, not blindly setting every numerical parameter to its theoretical maximum. A setting that causes instability, out-of-memory failures, severe noise, or worse reference fidelity does not qualify as a better default.

### 6.2 What presets may change

Presets may adjust validated parameters such as:
- input/processing resolution where supported;
- point-cloud sampling/density;
- confidence/validity thresholds;
- edge/noise filtering;
- diagnostic/output density;
- runtime/memory trade-offs;
- other quality-versus-cost parameters demonstrated by baseline/benchmark evidence.

Presets must not silently change:

```text
camera.requested_mode
geometry.requested_engine
geometry.compare_both
```

### 6.3 Reproducibility

The manifest records:

```text
preset.name
preset.version
preset.resolved_parameters
preset.manual_overrides
```

A preset name alone is not sufficient because preset internals may evolve.

Design principle:

```text
Preset -> how much validated quality/cost?
Camera/Geometry/Compare Both -> what processing path?
```

## 7. Maya Ghost is mandatory in the production-facing V1

The main ConceptGhost product is the Maya Ghost Scene.

Therefore the production-facing `ConceptGhost_Master.json` has **no `Maya Ghost ON/OFF` toggle**.

When all mandatory upstream gates pass:

```text
valid Camera
+ valid authoritative Canonical Geometry
+ Reprojection PASS
```

ConceptGhost automatically attempts to generate the Maya Ghost package.

A valid end-to-end run cannot be marked `PASS` unless the Maya Ghost package is successfully generated and usable under the current acceptance criteria.

If camera, geometry, and reprojection succeed but Maya export/assembly fails:

```text
run.status = PARTIAL
maya_ghost.status = FAILED
maya_ghost.authoritative = false
```

Useful upstream outputs are preserved for diagnosis.

Internal development/baseline workflows may bypass Maya generation when a stage specifically tests only an upstream component. That exception does not create a Maya toggle in the production-facing Master.

## 8. Canonical Point Cloud and essential diagnostics are mandatory

The production-facing Master automatically preserves the canonical evidence required to construct, validate, reproduce, and debug the Maya Ghost.

The user does **not** perform an extra step for this and does not need any non-local service. These artifacts are produced by the same local run.

### 8.1 Mandatory canonical geometry

For every run that reaches canonical geometry, ConceptGhost saves the authoritative **Canonical Point Cloud** used by the downstream Maya Ghost path.

Expected canonical outputs include, where supported by the final exporter:

```text
geometry/canonical/pointcloud.ply
geometry/canonical/pointcloud.usda
geometry/canonical/geometry.json
```

The exact interchange file set may evolve during Maya validation, but at least one reusable canonical point-cloud representation plus its metadata must be preserved.

The Canonical Point Cloud is not an extra geometry engine. It is the normalized ConceptGhost representation created from:

```text
source pixels
+ selected DA3 or MoGe depth/geometry evidence
+ authoritative Atlas camera
= ConceptGhost Canonical Point Cloud
```

### 8.2 Mandatory essential diagnostics

The following evidence is always generated/saved when the corresponding stage is reached:

```text
manifest.json
diagnostics/reprojection_report.json
diagnostics/reprojection_overlay.png
```

`manifest.json` records run configuration, versions, source identity, selected engines, resolved preset parameters, warnings, and generated outputs.

`reprojection_report.json` records the machine-readable reprojection gate result and metrics.

`reprojection_overlay.png` provides a visual check that canonical 3D points project back consistently through the authoritative Atlas camera.

The user is not expected to open these files in normal operation. They exist so ConceptGhost can be audited and problems can be diagnosed without rerunning blindly.

### 8.3 Optional diagnostics remain optional

Large or specialist diagnostic artifacts may remain optional, for example:
- additional full-resolution depth visualizations;
- confidence-map exports beyond what the selected engine already needs internally;
- normals previews;
- verbose native-engine dumps;
- extra comparison renders;
- other heavy review artifacts not required for the core quality gate.

A future UI control labeled along the lines of `Extra Diagnostics` may control these optional artifacts only. It must not disable the manifest, reprojection report, reprojection overlay, or required canonical point cloud.

### 8.4 Local-only execution policy

The normal ConceptGhost processing path is local:

```text
source image
-> Atlas
-> DA3 or MoGe
-> canonicalization
-> reprojection
-> Maya Ghost
```

No cloud upload, external API, or remote compute is required by this output policy.

Google Drive is used for ConceptGhost project documentation/tools according to the project workflow, not as a dependency of an individual image-processing run.

## 9. No hidden success substitution

A successful node execution is not automatically a valid ConceptGhost result.

- camera solvers must pass the camera-quality gate;
- geometry engines remain explicit user choices;
- successful secondary comparison geometry is not silently promoted;
- canonical evidence and essential diagnostics are preserved automatically;
- `PASS` requires the mandatory end-to-end Maya Ghost product.

## Related documents

- `docs/superpowers/specs/2026-09-16-conceptghost-master-workflow-design.md`
- `docs/superpowers/specs/2026-09-16-conceptghost-master-workflow-ui-layout.md`
- `docs/superpowers/plans/2026-09-16-conceptghost-master-workflow-addendum.md`
