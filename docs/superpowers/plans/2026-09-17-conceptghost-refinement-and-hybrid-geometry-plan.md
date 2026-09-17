# ConceptGhost Refinement + Hybrid Geometry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Date:** 2026-09-17  
**Status:** Approved planning baseline before refinement implementation. No production-code change is authorized by this document alone; it defines the order, contracts, evidence, and acceptance criteria for the refinement cycle after the Stage 14 full skeleton.  
**Baseline:** ConceptGhost v0.16 — Stage 14 Full Skeleton.  
**Reference Run:** `20260917T031354_668101Z_a6b09ba1`.  

**Goal:** Refine the existing end-to-end ConceptGhost skeleton into a useful artist-facing Ghost while preserving all current stages, fixing camera/texture/scale/export defects, recovering lost geometry evidence, and adding a third geometry mode — **MoGe + DA3 Hybrid** — that produces one official geometry rather than two competing final results.

**Architecture:** Atlas remains the camera/projection authority. DA3 and MoGe remain independently selectable for baseline/debug use. A new `MoGe + DA3 Hybrid` mode uses MoGe as the initial dense geometry support and DA3 as registered structural/depth evidence that can refine the same geometry along Atlas camera rays. Native DA3/MoGe outputs remain available only as intermediate diagnostics; the Hybrid mode must emit one canonical point/depth representation, one Hero Mesh, one matched camera, and one official export set.

**Tech Stack:** Windows, ComfyUI, Atlas Camera / GeoCalib, DA3, MoGe-2, DA3-Blender filtering concepts, Python, NumPy, OpenUSD, MayaUSD, Autodesk Maya, FBX, GLB, PLY, JSON.

**Primary specs to read together:**
- `docs/superpowers/specs/2026-09-16-conceptghost-integrated-architecture-v2.md`
- `docs/superpowers/specs/2026-09-16-conceptghost-runtime-behavior-policy.md`
- `docs/superpowers/specs/2026-09-16-conceptghost-stage7-normalizer-design.md`
- `docs/superpowers/specs/2026-09-16-conceptghost-stage8-maya-export-design.md`
- `docs/superpowers/specs/2026-09-16-conceptghost-stage10-atlas-relief-mesh-design.md`
- `docs/superpowers/specs/2026-09-16-conceptghost-stage11-moge-mesh-design.md`
- this plan, which supersedes only the earlier blanket rule that DA3 and MoGe may never collaborate in a final geometry. The independent DA3 and MoGe modes remain valid and unchanged.

## Global Constraints

- Preserve the current Stage 0–14 end-to-end skeleton; refinement must not regress structural continuity.
- Quality warnings do not block pipeline continuation; runtime/contract failures do.
- Keep the three geometry modes explicit: `DA3`, `MoGe`, `MoGe + DA3 Hybrid`.
- `Compare Both` remains diagnostic only and must not silently change the official output.
- No silent fallback or hidden promotion of a secondary engine.
- Atlas remains the camera authority. DA3/MoGe may cross-check camera evidence but may not silently replace Atlas pose/FOV/intrinsics.
- Hybrid output must be **one geometry**, not two overlaid meshes or two final point clouds.
- Do not average DA3 and MoGe depths blindly.
- Perform hybrid collaboration in a common Atlas camera/ray space before final triangulation.
- Preserve all native upstream evidence separately from cleaned/fused ConceptGhost outputs.
- Source RGB remains the texture/color authority.
- Maya `.ma` remains the richest artist handoff. FBX is an interchange output, not the authoritative point-cloud container.
- Stage 15 alternative engines stay out of the production path until the current stack has been refined and benchmarked.
- Every refinement milestone that changes the workflow must generate a separately testable workflow JSON in addition to updating `ConceptGhost_Master.json`.

---

# 1. Baseline facts from the uploaded v0.16 Run

The refinement cycle must start from observed evidence, not assumptions.

## 1.1 What already works

- The pipeline reaches Stage 14 and produces camera, DA3 evidence, canonical PLY/USDA, Maya scene, FBX, Atlas relief mesh, DA3 mesh track, packaging, logs, and Stage 14 validation artifacts.
- Atlas Learned / GeoCalib produced a plausible working camera for the reference concept.
- The user found the MoGe mesh visually useful: it produced readable foreground/background separation, road depth, and a tower placed substantially farther into the scene.
- The Atlas relief path produced a plausible 2.5D scale/depth extent and is valuable as a metric/structural reference.
- Atlas and DA3 intrinsics in this Run were much closer than in the earlier V10/V11 experiments, so the current dominant quality problem is not simply a large focal mismatch.

## 1.2 Camera observations from the reference Run

Recorded values from the Run analysis:

- Atlas horizontal FOV: approximately `36.83 deg`.
- Atlas focal: approximately `2174 px` / `54.06 mm`.
- pitch: approximately `1.81 deg`.
- roll: approximately `0.57 deg`.
- camera-height estimate: approximately `1.733 m`.
- focal confidence: approximately `0.675`.
- scale/depth confidence used by the height path: approximately `0.438`.

Interpretation: usable as a provisional working camera, but not yet frozen as final ground truth.

## 1.3 DA3 evidence-loss problem

Reference image size corresponds to `1,572,528` pixels.

The current DA3 confidence cutoff `confidence >= 0.10` rejected approximately:

- `326,995` pixels;
- `20.79%` of the image.

More importantly, the rejection was depth-biased:

- the farthest ~10% of DA3 depth samples were retained at approximately `0%` under the current filter;
- the preceding far-depth band retained only about `45.7%`.

This is a critical product problem because distant buildings/towers are useful for blockout even when their confidence is lower.

The DA3-Blender-inspired depth-edge filter detected roughly `24,949` pixels (`1.59%`) as strong edges, but after confidence filtering it removed only about `945` additional points. In this Run, confidence filtering is therefore much more destructive than edge filtering.

The sky mask was effectively empty/zero for this image, so low confidence is currently acting as an accidental substitute for a background/sky classifier and is removing valid distant geometry together with uncertain sky.

## 1.4 Metric-scale problem

The metric-registration path proposed a scale factor of approximately `21.358`, but rejected it because estimated ground support was around `12.48%`, below the current `20%` gate.

Consequences:

- canonical DA3 point geometry remained in non-metric units;
- canonical bounding box was approximately `0.373 x 0.448 x 1.520` in those units;
- it must not be presented as reliable meters.

This all-or-nothing ground-support gate must be replaced by a more robust multi-evidence metric-registration policy.

## 1.5 Atlas relief observation

The Run's Atlas relief mesh was approximately:

- `39,643` vertices;
- `72,330` triangles;
- extent around `14.6 x 14.6 x 54.5 m`;
- depth approximately `Z -7 m` to `Z -62 m` in the current canonical interpretation.

It contained multiple disconnected components and was not watertight, which is acceptable for a 2.5D reference shell. Its scale/depth extent is much more plausible for the street scene than the current unscaled DA3 canonical point cloud.

## 1.6 User-observed MoGe mesh strengths

The user explicitly found value in the E2 MoGe result despite its defects:

- readable depth progression;
- foreground/background separation;
- tower visibly far into the scene;
- a particular camera angle made the 3D mesh strongly resemble the 2D concept.

This means the refinement plan must preserve these strengths rather than replacing the mesh path simply because the point cloud is easier to analyze.

## 1.7 User-observed MoGe/Maya defects

The following are required refinement items:

- the reference image/texture appeared vertically inverted on the mesh;
- sky that correctly had no mesh support appeared projected onto ground geometry;
- tower texture appeared projected onto ground/incorrect surfaces;
- the imported result did not contain a matched camera that immediately reproduced the concept view;
- the user manually adjusted the Maya camera until the view approximately matched;
- the mesh did not arrive in a clearly documented metric/canonical scene package;
- E1 and E3 visual outputs were much less discoverable than the E2 MoGe output.

## 1.8 Maya batch reliability defect

The Maya worker produced the requested files but the process ended with Windows code `0xC0000409` (`3221226505`). Logs also showed an external Fab Maya plugin/userSetup failure with `initialize_plugin` not defined.

This must be treated as an environment/reliability defect. ConceptGhost should detect/report external startup failures and, where possible, launch the batch worker in a mode that minimizes unrelated user-plugin interference without modifying the user's Maya installation.

---

# 2. Product decision after the Stage 14 skeleton

The refinement phase changes the product emphasis from "which solver produced the prettiest isolated output" to "one coherent artist-facing result".

## 2.1 Geometry modes

The Master workflow must expose three explicit modes:

```text
Geometry = DA3
Geometry = MoGe
Geometry = MoGe + DA3 Hybrid
```

Meaning:

### DA3
One official output built from DA3 evidence + Atlas camera.

### MoGe
One official output built from MoGe evidence + Atlas camera.

### MoGe + DA3 Hybrid
MoGe provides the initial geometry support. DA3 does not create a competing final mesh. Instead, registered DA3 depth/confidence/boundary evidence refines the MoGe-supported geometry. The result is one fused canonical point/depth field and one Hero Mesh.

`Compare Both` remains an advanced diagnostic feature only.

## 2.2 Official vs intermediate outputs

Intermediate/debug outputs may remain multiple:

```text
DA3 native depth / points / mesh
MoGe native points / depth / normals / mesh
Atlas relief mesh
registered DA3 depth
DA3-vs-MoGe residual map
conflict map
reliability map
fused point map
```

Official Hybrid outputs must be singular:

```text
ONE matched camera
ONE canonical fused point/depth geometry
ONE Hero Mesh
ONE Maya scene
ONE FBX interchange asset
ONE USD scene
ONE canonical PLY point set
```

The user must never have to choose between two contradictory "final" towers at different distances.

---

# 3. Hybrid collaboration design

## 3.1 Collaboration happens before final mesh creation

Do not fuse two independently triangulated meshes.

Preferred order:

```text
MoGe point/depth map
+
DA3 raw depth/confidence
+
MoGe normals/mask
+
Atlas camera/rays
        ↓
common registered per-pixel geometry evidence
        ↓
Hybrid refinement / conflict handling
        ↓
ONE fused canonical point/depth field
        ↓
boundary-aware triangulation
        ↓
ONE Hero Mesh
```

This avoids mesh-to-mesh correspondence problems and guarantees only one point/depth answer per source pixel/ray.

## 3.2 Common Atlas ray space

For each source pixel, ConceptGhost must use the Atlas-authoritative camera ray. MoGe and DA3 observations are registered to this common pixel/ray domain.

Corrections are primarily applied **along the camera ray**, not as arbitrary XYZ displacement, so source-image correspondence is preserved.

## 3.3 DA3 is structural evidence, not absolute authority

The first Hybrid implementation must use DA3 primarily for:

- relative depth ordering;
- plane separation;
- depth discontinuities;
- confidence/reliability;
- foreground/background boundary evidence;
- local residual correction after robust registration to the MoGe/Atlas space.

If MoGe puts two surfaces nearly at the same depth but registered DA3 strongly and reliably detects a depth discontinuity, the Hybrid path may separate those surfaces by adjusting MoGe-supported samples along Atlas rays.

## 3.4 Do not blindly average disagreement

Example:

```text
MoGe tower ≈ 30 m
DA3 tower ≈ 60 m
```

Forbidden:

```text
final tower = 45 m
```

Required behavior:

1. register DA3 depth scale/shift to the MoGe/Atlas domain using robust agreement regions;
2. calculate local residual and confidence;
3. classify the region as agreement / DA3-supported correction / MoGe-supported hold / conflict / both-weak;
4. bound correction magnitude;
5. record the decision in the Conflict and Reliability maps.

## 3.5 First Hybrid version must not invent a parallel DA3 surface

In the initial Hybrid milestone, DA3 is allowed to refine samples where MoGe has support. It must not silently create a second surface layer.

A later controlled hole-recovery experiment may allow DA3 to create missing support only if:

- MoGe is invalid at that pixel/region;
- DA3 is reliable;
- neighboring geometry provides continuity evidence;
- the output is tagged as recovered/low-confidence.

That later capability must be separately benchmarked and is not required for the first Hybrid Hero Mesh.

---

# 4. Camera refinement policy

Atlas remains authoritative, but DA3 and MoGe should contribute to **camera confidence and diagnostics**.

## 4.1 Inputs to camera confidence

Use when available:

- Atlas Learned / GeoCalib FOV/intrinsics/gravity;
- Atlas VP solve when architectural VP evidence is valid;
- MoGe inferred/conditioned FOV behavior;
- DA3 intrinsics/camera-decoder evidence where the selected checkpoint supports it;
- reconstructed ground/surface normals as structural cross-checks.

## 4.2 No silent camera replacement

If geometry evidence indicates Atlas may be wrong, report:

```text
Atlas original camera
cross-check evidence
suggested delta
reason
confidence
```

Do not silently move or rotate the camera in V17.

A future camera-refinement experiment may alter the camera only if it improves explicit measurable tests and preserves a full audit trail.

## 4.3 Difficult top-down/no-horizon scenes

For images looking strongly downward with little/no visible horizon:

- prioritize Atlas Learned / GeoCalib gravity/orientation;
- use VP only where real line evidence supports it;
- use MoGe/DA3 ground/plane/FOV evidence as validation rather than a hidden replacement.

---

# 5. Texture and projection refinement

The Maya screenshots showed that texture quality is currently limited more by projection/UV integration than by whether a surface exists.

Required fixes:

1. verify vertical UV convention (`V`) end-to-end and correct the observed upside-down source mapping;
2. derive projective texture coordinates from the matched Atlas camera or a provably equivalent source-pixel mapping;
3. create a geometry-support/projection mask so pixels with no valid surface support do not project onto unrelated geometry;
4. sky pixels must not fall onto ground merely because ground lies on the same projection ray;
5. tower/building pixels must not bleed onto foreground ground surfaces across a depth discontinuity;
6. validate the four source-image corners and a set of interior landmarks against mesh UV/projective coordinates;
7. preserve original source RGB; do not use display-normalized depth images as texture sources.

The final Hero Mesh texture must be evaluated from the matched camera and from a modest off-axis orbit.

---

# 6. Metric scale refinement

Replace the current single weak-ground-support gate with a multi-evidence metric-registration system.

Candidate evidence sources already available in the current stack:

- Atlas camera-height estimate;
- Atlas relief/metric-depth geometry;
- stable ground candidates;
- gravity orientation;
- large planar facade/road constraints;
- robust DA3/MoGe agreement regions.

The registration must produce:

```text
scale_applied: bool
scale_factor
scale_sources[]
source_confidences[]
residual_error
reason_if_not_applied
units: meters | relative
```

If metric evidence is insufficient, keep relative units and label them clearly. Never silently label arbitrary units as meters.

---

# 7. Point cloud role after refinement

Point clouds remain valuable, but their product role changes:

- native DA3/MoGe point outputs = diagnostics;
- fused Hybrid canonical point set = official geometric evidence;
- Hero Mesh = primary artist-facing 2.5D blockout reference;
- Maya/USD may show both Hero Mesh and the fused point set with visibility controls.

In Hybrid mode, the official PLY must correspond to the same fused geometry used to create the Hero Mesh.

---

# 8. Maya / FBX / USD target contract

## 8.1 Maya `.ma` — authoritative artist scene

Expected hierarchy:

```text
CG_ROOT
├── CG_CAMERA
│   ├── CG_MATCHED_CAMERA
│   └── CG_ARTIST_CAMERA
├── CG_SOURCE
│   └── source image plane / plate
├── CG_GEOMETRY
│   ├── CG_HERO_MESH
│   └── CG_FUSED_POINTS
├── CG_DIAGNOSTICS (optional visibility)
│   ├── CG_ATLAS_RELIEF
│   ├── CG_MOGE_NATIVE
│   └── CG_DA3_NATIVE
└── CG_METADATA
```

The matched camera must open already aligned to the 2D concept. The user must not need to manually find the matching angle.

## 8.2 FBX — practical interchange

FBX target:

```text
Matched Atlas Camera
+
Hero Mesh
+
material/texture where safely portable
```

Do not force a million-point cloud into FBX. PLY/USD remain the point formats.

## 8.3 USD — richest interchange

USD should be able to carry:

- matched camera;
- fused points;
- Hero Mesh;
- material/reference metadata where practical.

---

# 9. E1/E2/E3 discoverability and comparison

Current outputs must remain available because they are valuable for debugging, but all three need a common viewing contract.

- E1 = Atlas Relief
- E2 = MoGe native/official mesh
- E3 = DA3 mesh/bas-relief

Refinement requirement:

- canonicalize their coordinate metadata for comparison;
- provide a matched Atlas camera reference with each preview/package where possible;
- expose explicit file paths in the Run manifest and UI;
- add clear labels: `INTERMEDIATE / DIAGNOSTIC`, not `FINAL`.

Add a fourth preview for Hybrid when implemented:

- `Hero Hybrid Preview` = official candidate.

---

# 10. Visual Synergy Evidence Report

Every refinement Run must make solver collaboration visible.

Required diagnostic images/data:

```text
01_source.png
02_moge_depth.png
03_moge_normals.png
04_moge_mask.png
05_da3_depth.png
06_da3_confidence.png
07_da3_boundary.png
08_registered_da3_depth.png
09_moge_da3_residual.png
10_conflict_map.png
11_reliability_map.png
12_fused_depth.png
13_projection_support_mask.png
14_final_reprojection.png
```

The report must also include counts/percentages for:

- MoGe valid support;
- DA3 valid support;
- far-field DA3 support before/after confidence policy;
- agreement pixels;
- corrected pixels;
- conflict pixels;
- unchanged MoGe pixels;
- rejected triangulation edges/faces;
- final fused point count;
- final Hero Mesh vertex/triangle count;
- metric-scale status.

This is the user-facing proof that the additional layers are actually contributing.

---

# 11. Implementation sequence and testable builds

The refinement cycle deliberately uses incremental workflows so the user can test each material change.

## Milestone R1 — v0.17: Canonical Mesh Viewing + Matched Camera + Projection Fix

**Purpose:** Make the mesh result already liked by the user usable in Maya before introducing hybrid geometry.

**Files:**
- Modify: `custom_nodes/ConceptGhost_Stage68/conceptghost_maya_worker.py`
- Modify: `custom_nodes/ConceptGhost_Stage68/nodes.py`
- Modify: `custom_nodes/ConceptGhost_Stage68/conceptghost_io.py`
- Modify: `Tools/Stage06_08/build_conceptghost_master.py`
- Modify: `Workflows/Project/ConceptGhost_Master.json`
- Test: `tests/test_maya_worker.py`
- Test: `tests/test_export_bundle.py`
- Test: `tests/test_master_builder.py`

**Deliverables:**
- `ConceptGhost_Master_R1_v0.17.json`
- matched camera packaged with Hero/MoGe preview path;
- corrected V orientation / texture mapping;
- projection-support mask that prevents obvious sky-to-ground bleed;
- E1/E2/E3 paths clearly exposed in manifest/UI;
- Maya scene opens with matched camera, source plate, current mesh candidate, and point cloud.

**Acceptance:** User can open the generated Maya scene and immediately switch to the matched camera without manually searching for the concept angle.

## Milestone R2 — v0.18: DA3 Evidence Recovery + Robust Metric Registration

**Purpose:** Stop discarding useful far-field DA3 structure and improve scale handling before hybrid fusion.

**Files:**
- Modify: `custom_nodes/ConceptGhost_Stage68/conceptghost_geometry.py`
- Modify: `custom_nodes/ConceptGhost_Stage68/nodes.py`
- Test: `tests/test_geometry.py`
- Test: `tests/test_nodes.py`

**DA3 policy changes:**
- separate `invalid` from `low confidence`;
- preserve low-confidence far-field evidence for diagnostics/refinement rather than hard-deleting it;
- record confidence classes;
- keep hard rejection for non-finite/physically invalid samples;
- benchmark the current `0.10` threshold against softer/weighted behavior on the same Run.

**Metric changes:**
- combine Atlas camera height, Atlas relief/metric geometry, ground support, and robust residual checks;
- remove the current single `ground_support >= 20%` all-or-nothing decision as the only metric gate.

**Deliverables:**
- `ConceptGhost_Master_R2_v0.18.json`
- far-field retention report;
- scale-evidence report;
- clear `meters` vs `relative` unit status.

## Milestone R3 — v0.19: Hybrid Registration Core

**Purpose:** Add `MoGe + DA3 Hybrid` without creating a second final surface.

**Files:**
- Modify: `custom_nodes/ConceptGhost_Stage68/conceptghost_geometry.py`
- Modify: `custom_nodes/ConceptGhost_Stage68/conceptghost_contracts.py`
- Modify: `custom_nodes/ConceptGhost_Stage68/nodes.py`
- Modify: `Tools/Stage06_08/build_conceptghost_master.py`
- Test: `tests/test_geometry.py`
- Test: `tests/test_contracts.py`
- Test: `tests/test_nodes.py`
- Test: `tests/test_master_builder.py`

**New contracts:**

```text
RegisteredDepthEvidence
HybridReliabilityMap
HybridConflictMap
HybridGeometry
```

**Core behavior:**
- resample/align DA3 and MoGe evidence into the same source pixel grid;
- map both into Atlas-authoritative ray semantics;
- robustly estimate DA3-to-MoGe scale/shift where depth semantics require it;
- output registered residual, reliability, and conflict maps;
- do not triangulate yet in the first subgate.

**Tests:**
- identical planes remain unchanged;
- two planes that MoGe flattens but DA3 reliably separates produce a bounded residual correction;
- large disagreement does not average blindly;
- low-confidence DA3 cannot override strong MoGe support;
- invalid MoGe does not automatically create a parallel DA3 surface;
- DA3-only and MoGe-only modes remain bitwise/semantically unchanged where expected.

**Deliverable:** `ConceptGhost_Master_R3_v0.19.json` with a Hybrid point/depth preview and visual conflict/reliability maps.

## Milestone R4 — v0.20: Hybrid Hero Geometry + Boundary-Aware Triangulation

**Purpose:** Convert the fused evidence into one artist-facing Hero Mesh.

**Files:**
- Modify: `custom_nodes/ConceptGhost_Stage68/conceptghost_geometry.py`
- Modify: `custom_nodes/ConceptGhost_Stage68/nodes.py`
- Test: `tests/test_geometry.py`
- Test: `tests/test_nodes.py`

**Boundary evidence:**
- MoGe raw depth discontinuities;
- MoGe normals discontinuities;
- MoGe mask boundaries;
- DA3 registered depth boundaries;
- DA3 confidence/reliability;
- source-image support where useful only as secondary evidence.

**Triangulation rule:** Do not bridge pixels/vertices across a boundary when the combined boundary score exceeds the validated threshold.

**Deliverables:**
- one fused canonical PLY;
- one Hero Mesh;
- visual boundary/rejected-face diagnostics;
- `ConceptGhost_Master_R4_v0.20.json`.

## Milestone R5 — v0.21: Hero Maya / FBX / USD Package

**Purpose:** Turn the refined geometry into the actual product.

**Files:**
- Modify: `custom_nodes/ConceptGhost_Stage68/conceptghost_maya_worker.py`
- Modify: `custom_nodes/ConceptGhost_Stage68/conceptghost_io.py`
- Modify: `custom_nodes/ConceptGhost_Stage68/nodes.py`
- Test: `tests/test_maya_worker.py`
- Test: `tests/test_export_bundle.py`

**Required official outputs:**

```text
ConceptGhost_<scene>_Hero.ma
ConceptGhost_<scene>_Hero.fbx
ConceptGhost_<scene>_Hero.usda
pointcloud_fused.ply
HeroMesh.glb (or equivalent portable mesh)
```

FBX must contain matched camera + Hero Mesh. Maya must also contain source plate + fused points. Native E1/E2/E3 remain optional diagnostic groups/files.

**Deliverable:** `ConceptGhost_Master_R5_v0.21.json`.

## Milestone R6 — v0.22: Reliability, Camera Cross-Check, Evidence Report, Acceptance

**Purpose:** Stabilize the refined pipeline and decide whether current technology is good enough before Stage 15.

**Files:**
- Modify: `custom_nodes/ConceptGhost_Stage68/nodes.py`
- Modify: `custom_nodes/ConceptGhost_Stage68/conceptghost_maya_worker.py`
- Modify: `custom_nodes/ConceptGhost_Stage68/conceptghost_io.py`
- Modify: `README_EVALUATION.md`
- Test: `tests/test_nodes.py`
- Test: `tests/test_maya_worker.py`
- Test: `tests/test_stage14.py`
- Add: `tests/test_hybrid_geometry.py`

**Work:**
- generate full Synergy Evidence Report;
- report Atlas-vs-MoGe-vs-DA3 camera evidence without silent camera changes;
- isolate/report Maya startup plugin failures;
- re-run the same reference image for DA3, MoGe, and Hybrid;
- compare the same matched-camera view and off-axis views;
- record whether Hybrid materially improves plane separation, far-field depth, edge quality, and artist usability.

**Deliverable:** `ConceptGhost_Master_R6_v0.22.json` and a final refinement acceptance report.

---

# 12. Test strategy

## 12.1 Geometry unit tests

Add synthetic tests for:

- smooth planar region -> no unnecessary correction;
- MoGe-flat / DA3-separated two-plane case -> bounded separation appears in Hybrid;
- MoGe strong / DA3 weak -> MoGe preserved;
- MoGe weak / DA3 strong -> correction allowed within limits;
- both strong but disagree strongly -> conflict, no blind mean;
- depth discontinuity -> triangulation does not bridge;
- normal discontinuity with modest depth change -> boundary still recognized;
- invalid masks -> no geometry;
- far-field low confidence -> retained as weak evidence rather than automatically removed;
- UV vertical orientation -> source top remains mesh top;
- no valid support -> source sky does not project onto ground.

## 12.2 Workflow regression tests

For every milestone:

- DA3 mode loads and runs;
- MoGe mode loads and runs;
- Hybrid mode loads when introduced;
- Compare Both remains diagnostic;
- no hidden fallback;
- Stage 10–14 outputs still execute;
- package manifest lists all generated official/intermediate assets correctly.

## 12.3 Runtime acceptance image

Use the exact same concept image from Run `20260917T031354_668101Z_a6b09ba1` for the first A/B sequence so changes are attributable.

Required comparison screenshots:

- matched camera, textured;
- matched camera, wireframe + texture;
- side view;
- top view;
- moderate 3/4 orbit;
- Hybrid reliability/conflict overlays.

---

# 13. Stage 15 hold / escalation criteria

Do not add new solvers merely because current outputs are imperfect.

First finish R1–R6 and determine the dominant remaining failure mode.

Only then consider:

- Depth Anything V2 Metric Outdoor as a low-cost exterior metric benchmark, especially because Atlas relief already showed promising depth/scale behavior on this image;
- MoGe-3 if MoGe-2 geometry is close but refinement quality remains limiting;
- VGGT if an independent camera + geometry cross-check is needed;
- UniDepth V2 if metric-depth consistency is the dominant failure;
- Depth Pro if edge/boundary fidelity remains the dominant failure;
- Metric3D V2 if normals/planarity remain the dominant failure;
- GeoWizard if DA3/MoGe specifically fail on stylized/concept-art imagery.

Any Stage 15 engine must enter through the existing GeometryAdapter/Normalizer contracts and must not require rewriting the Maya/export stack.

---

# 14. Definition of success for the refinement cycle

The refinement cycle is successful when, for the reference concept image:

1. opening the generated Maya file immediately presents a matched camera whose view closely reproduces the concept without manual camera hunting;
2. texture is upright and does not obviously project sky/tower pixels onto unrelated ground surfaces;
3. the scene has one official Hero Mesh and one official fused point set in Hybrid mode;
4. DA3 and MoGe disagreements are visible in diagnostics but do not create contradictory final geometry layers;
5. far-field structures are preserved materially better than the v0.16 DA3 confidence-filtered baseline;
6. metric scale is either credibly applied and labeled in meters, or explicitly reported as relative;
7. FBX contains the matched camera and Hero Mesh;
8. USD/Maya retain richer points/diagnostics;
9. E1/E2/E3 remain accessible as intermediate comparisons but are clearly not the official result;
10. Maya batch execution either exits cleanly or clearly isolates/reports external plugin interference;
11. a Synergy Evidence Report shows exactly how MoGe, DA3, Atlas, masks, normals, boundaries, and scale registration changed the official output.

---

# 15. Implementation stop rules

Stop and review before adding more complexity if any of these occur:

- Hybrid repeatedly degrades the MoGe-only result on the reference image;
- DA3 corrections cannot be robustly registered to MoGe/Atlas depth semantics;
- correction maps become dominated by arbitrary scale/shift rather than structural evidence;
- camera changes are required to hide geometry errors;
- texture fixes require destructive changes to source RGB or native geometry;
- a new dependency threatens the protected ComfyUI environment.

In those cases, preserve the last good milestone and evaluate Stage 15 alternatives rather than layering more heuristics blindly.

---

# 16. Execution rule

Implement in milestone order. After every milestone:

1. run the targeted tests;
2. run the full test suite;
3. compile Python modules;
4. deterministically build the workflow;
5. generate the milestone-specific `.json` workflow;
6. package BAT + ZIP into `Google Drive/ConceptGhost/Storage/Evaluation_Builds`;
7. run the same reference image locally in ComfyUI;
8. inspect the produced Run folder before advancing.

Do not claim artist-quality success from unit tests alone. Distinguish:

```text
implemented structurally
build/unit tested
runtime verified locally
artist-useful
```

This document is the refinement baseline to use before changing the v0.16 Stage 14 skeleton.
