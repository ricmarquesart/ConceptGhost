> MANDATORY: Read `docs/superpowers/specs/2026-09-16-conceptghost-synergy-architecture-v1.md` before implementation.

# ConceptGhost Stage 6–8 Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the first complete ConceptGhost vertical slice: one source image enters one `ConceptGhost_Master.json` workflow and produces an Atlas-authoritative camera, DA3 or MoGe canonical colored point cloud, required validation evidence, and the first Maya Ghost package (`.ma + .usda + .fbx + .ply`) without blocking progress on fine quality tuning.

**Architecture:** ComfyUI remains the orchestrator. Atlas is the authoritative camera/projection source; DA3 or MoGe supplies engine-native depth/shape evidence; ConceptGhost adapters normalize both into a shared right-handed Y-up canonical space; the canonical point cloud is validated for integration consistency and basic geometry health; Stage 8 exports the same SceneBundle to PLY/USD and delegates Maya/FBX construction to a separate Maya Worker.

**Tech Stack:** Windows, ComfyUI Desktop, Atlas Camera/GeoCalib, Depth Anything V3, MoGe-2, Python, JSON/YAML, NumPy/PyTorch where already available, PLY, OpenUSD/USDA, Autodesk Maya/MayaUSD, FBX.

**Specs:**
- `Documentation/Architecture/2026-09-16-conceptghost-integrated-architecture-v2.md`
- `Documentation/Architecture/2026-09-16-conceptghost-synergy-architecture-v1.md`
- `Documentation/Architecture/2026-09-16-conceptghost-runtime-behavior-policy.md`
- `Documentation/Architecture/2026-09-16-conceptghost-master-workflow-ui-layout.md`
- `Documentation/Architecture/2026-09-16-conceptghost-output-handoff-contract.md`
- `Documentation/Architecture/2026-09-16-conceptghost-stage8-maya-export-design.md`
- `Documentation/Research/2026-09-16-conceptghost-consolidated-research-and-implementation-guidance.md`
- `Documentation/Roadmap/2026-09-16-conceptghost-master-workflow-addendum.md`

## Global Constraints

- Primary objective is an end-to-end artist-judgable result, not parameter perfection.
- Do not stop for cosmetic holes, edge streamers, small threshold differences, or mesh quality during Stages 6–8.
- Smoke tests exist only to prove that a branch runs, contracts are structurally valid, and required files are produced.
- Atlas is the final camera authority.
- DA3 is the default geometry engine; MoGe remains selectable; there is no `Geometry = Auto`.
- `Compare Both` runs engines independently and never silently fuses/promotes results.
- Production defaults: `Preset = Max Reference`, `Camera = Auto`, `Geometry = DA3`, `Compare Both = OFF`.
- Canonical coordinates: right-handed, Y-Up, +X right, +Y up, -Z camera forward.
- Use raw geometric depth/evidence for XYZ reconstruction, never display-normalized depth.
- Preserve native engine evidence separately from canonical output.
- Required production evidence cannot be toggled off: Canonical Point Cloud, manifest, reprojection report, reprojection overlay, Maya Ghost attempt.
- Geometry Health FAIL must not delete/hide evaluation evidence; preserve the canonical cloud marked non-authoritative so the user can judge whether the project is worth continuing.
- Optional meshes are outside this sprint and must not block Stage 8.
- Maya runtime dependencies must remain outside the protected ComfyUI Python process; use a separate Maya Worker.
- Project is Drive/version-file based rather than a Git working tree. Every implementation artifact is versioned, hashed, and uploaded without overwriting previous stage artifacts.

---

## Synergy amendment — overrides any isolated-branch interpretation

The vertical slice is not complete if Atlas, DA3/MoGe, normalization, filtering, and export only coexist in one graph. The selected DA3 or MoGe path must produce one integrated Canonical Ghost using the Synergy Architecture v1 contract.

Minimum V0.1 cooperation required before the First Tangible Ghost:

```text
Atlas camera authority
→ camera conditioning hook where the selected engine supports it
→ selected engine EvidencePack
→ explicit depth-semantics adapter
→ Atlas-ray Canonical reconstruction
→ confidence/mask/sky validity
→ edge-aware streamer reduction
→ MoGe normal-boundary evidence when available
→ optional confidence-gated ground stabilization when safely available
→ Integration Consistency + Geometry Health
→ one CanonicalGeometry
→ PLY + USDA + MA
```

Do not add automatic DA3+MoGe fusion. `Compare Both` remains two independent end-to-end Ghosts for comparison.

## File Structure Locked for This Sprint

### Project/source artifacts

- `Tools/Stage06_08/build_conceptghost_master.py` — builds the unified ComfyUI workflow from validated reference workflows and ConceptGhost custom nodes.
- `Tools/Stage06_08/conceptghost_contracts.py` — typed/schema helpers for CameraBundle, GeometryEvidence, CanonicalGeometry, SceneBundle, manifest/status payloads.
- `Tools/Stage06_08/conceptghost_geometry.py` — depth/point-map canonicalization, coordinate conversion, sampling, color association, basic health metrics.
- `Tools/Stage06_08/conceptghost_io.py` — unique run folder creation, JSON/report output, PLY/USDA serialization.
- `Tools/Stage06_08/conceptghost_maya_worker.py` — script executed by mayapy/Maya batch to build `.ma` and `.fbx` from the Stage 7 SceneBundle/USDA.
- `Tools/Stage06_08/run_maya_worker.bat` — Windows launcher that discovers Maya and runs the Maya Worker separately.
- `Tools/Stage06_08/BUILD_MASTER.bat` — deterministic builder/validator for `ConceptGhost_Master.json`.
- `Workflows/Project/ConceptGhost_Master.json` — single user-facing workflow.
- `Manifests/conceptghost_master_contract_v0.8.json` — machine-readable output/schema contract.
- `Reports/ConceptGhost_Stage06_08_build_report.json` — hashes, reference provenance, structural validation.

### Runtime output

`ConceptGhost_Output/<scene>/<run_id>/`
- `source/`
- `camera/`
- `diagnostics/reprojection_report.json`
- `diagnostics/reprojection_overlay.png`
- `geometry/native/<engine>/`
- `geometry/canonical/pointcloud.ply`
- `geometry/canonical/pointcloud.usda`
- `geometry/canonical/geometry.json`
- `maya/ConceptGhost_<scene>_Ghost.ma`
- `maya/ConceptGhost_<scene>_Ghost.usda`
- `maya/ConceptGhost_<scene>_Ghost.fbx`
- `maya/maya_manifest.json`
- `compare/`
- `logs/`
- `manifest.json`

---

### Task 1: Stage 6 Master Alpha Workflow Shell

**Files:**
- Create: `Tools/Stage06_08/build_conceptghost_master.py`
- Create: `Tools/Stage06_08/BUILD_MASTER.bat`
- Create: `Workflows/Project/ConceptGhost_Master.json`

**Interfaces:**
- Consumes: validated Atlas workflow JSON, DA3 `advanced_3d.json`, MoGe Stage5D4 workflow/reference nodes.
- Produces: one valid ComfyUI graph with a single `LoadImage`, master controls, Atlas branch, DA3 branch, MoGe branch, and downstream ConceptGhost integration placeholders/nodes.

- [ ] Parse the three source/reference workflows and assert required node types are present before building.
- [ ] Create one `LoadImage` source and fan its IMAGE output into Atlas, DA3, and MoGe branches.
- [ ] Add visible master controls with defaults: Max Reference / Auto / DA3 / Compare Both OFF.
- [ ] Preserve engine-native node settings at known stable/upstream values rather than inventing new tuning.
- [ ] Lay out the workflow left-to-right using the approved 01–08 canvas zones.
- [ ] Collapse/visually segregate Advanced engine controls where ComfyUI JSON supports it; keep critical warnings/status visible.
- [ ] Validate JSON structure, unique node IDs, valid link references, and required node-type inventory.
- [ ] Emit SHA-256 and build provenance into `ConceptGhost_Stage06_08_build_report.json`.

**Smoke acceptance:** `ConceptGhost_Master.json` loads as a graph with no malformed links; quality is not evaluated here.

---

### Task 2: Runtime Control and Status Contract

**Files:**
- Create: `Tools/Stage06_08/conceptghost_contracts.py`
- Create: `Manifests/conceptghost_master_contract_v0.8.json`

**Interfaces:**
- Produces exact schemas for `RunConfig`, `CameraBundle`, `GeometryEvidence`, `CanonicalGeometry`, `SceneBundle`, and final run status.

- [ ] Define `RunConfig` fields for source, preset, camera mode, geometry engine, compare flag, optional meshes, and extra diagnostics.
- [ ] Define provenance fields required by Runtime Behavior Policy for camera and geometry.
- [ ] Define `PASS | PARTIAL | FAIL`, `maya_ghost_ready`, `deliverable_package_complete`, and `authoritative` semantics.
- [ ] Encode canonical coordinate convention explicitly in every SceneBundle.
- [ ] Add schema validation utility that rejects missing required fields but preserves unknown engine-native metadata under namespaced `native` data.

**Smoke acceptance:** fixed sample payloads for DA3 and MoGe validate against the same downstream SceneBundle schema.

---

### Task 3: Atlas CameraBundle Adapter and Auto Policy

**Files:**
- Modify/Create: `Tools/Stage06_08/conceptghost_contracts.py`
- Create/Modify: ConceptGhost ComfyUI adapter node module used by Master workflow.

**Interfaces:**
- Consumes: Atlas Learned/VP solve outputs.
- Produces: `CameraBundle` containing image dimensions, intrinsics/FOV, camera transform/orientation, solver provenance, and quality status.

- [ ] Normalize Atlas Learned output into CameraBundle without changing Atlas camera math.
- [ ] Normalize Atlas VP output into the same CameraBundle schema.
- [ ] Implement Auto routing: Learned first; VP only after camera-quality failure.
- [ ] Keep explicit Learned/VP modes literal with no silent fallback.
- [ ] Record requested/final solver and fallback reason.

**Smoke acceptance:** both solver adapters produce the same CameraBundle keys and can be serialized.

---

### Task 4: DA3 GeometryEvidence Adapter

**Files:**
- Create/Modify: ConceptGhost geometry adapter node module.
- Modify: `Tools/Stage06_08/conceptghost_geometry.py`

**Interfaces:**
- Consumes: DA3 raw depth, confidence/sky data where supported, engine intrinsics/native point data, source image, CameraBundle.
- Produces: `GeometryEvidence(engine='da3')` plus canonicalization-ready source-pixel/depth relationships.

- [ ] Preserve DA3 native evidence in the run’s `geometry/native/da3` namespace.
- [ ] Ensure XYZ reconstruction uses raw depth rather than display-normalized depth.
- [ ] Record DA3 depth semantics/model/checkpoint/resolution/confidence metadata explicitly.
- [ ] Use Max Reference candidate settings from approved research as initial defaults, but mark them `candidate_unfrozen=true`.
- [ ] Provide a clean interface for future Atlas-conditioned DA3 without making that experiment a blocker for this vertical slice.

**Smoke acceptance:** one DA3 execution reaches GeometryEvidence and exports non-empty geometry evidence/native data.

---

### Task 5: MoGe GeometryEvidence Adapter with Atlas FOV Path

**Files:**
- Modify: ConceptGhost geometry adapter node module.
- Modify: `Tools/Stage06_08/conceptghost_geometry.py`

**Interfaces:**
- Consumes: MoGe point map/depth/mask/normals/intrinsics, source image, CameraBundle.
- Produces: `GeometryEvidence(engine='moge')` under the same downstream contract as DA3.

- [ ] Preserve the known-working Stage5D4 raw point path as native evidence.
- [ ] Convert MoGe OpenCV camera coordinates (X right, Y down, Z forward) explicitly into canonical coordinates.
- [ ] Keep `apply_mask/use_mask` on for the Max Reference candidate based on current evidence.
- [ ] Set MoGe high-detail candidate configuration (`resolution_level=9` where supported, `force_projection=true`).
- [ ] Add Atlas horizontal-FOV conditioning where the existing MoGe/Atlas implementation path safely supports `fov_x`; otherwise retain auto-FOV and record `atlas_fov_conditioned=false` rather than blocking the sprint.

**Smoke acceptance:** one MoGe execution reaches GeometryEvidence and exports a non-empty native PLY/evidence package.

---

### Task 6: Canonical Point Cloud Normalizer

**Files:**
- Create: `Tools/Stage06_08/conceptghost_geometry.py`
- Modify: ConceptGhost Normalizer custom node module.

**Interfaces:**
- Consumes: `CameraBundle + GeometryEvidence + source image`.
- Produces: `CanonicalGeometry` with `xyz[N,3]`, `rgb[N,3]`, optional confidence, source UV/pixel provenance, engine metadata, canonical coordinate metadata.

- [ ] Implement a single canonical coordinate conversion path for DA3 and MoGe.
- [ ] Use authoritative Atlas intrinsics/projection for final canonical interpretation where required by the approved engine path.
- [ ] Associate each retained point with source-image RGB.
- [ ] Keep native and canonical data separate; never overwrite the native files.
- [ ] Support dense Max Reference output while allowing downstream sampling for lower presets without changing engine identity.
- [ ] Serialize canonical geometry metadata independently of PLY/USD file formats.

**Smoke acceptance:** DA3 and MoGe both produce the same canonical field set with point count > 0.

---

### Task 7: Integration Consistency and Geometry Health Gates

**Files:**
- Modify: `Tools/Stage06_08/conceptghost_geometry.py`
- Create/Modify: ConceptGhost quality-gate custom node module.

**Interfaces:**
- Consumes: CameraBundle + CanonicalGeometry.
- Produces: `reprojection_report`, reprojection overlay, geometry-health metrics, and `SceneBundle` status.

- [ ] Reproject canonical points through Atlas camera to validate integration consistency.
- [ ] Save the reprojection report and overlay automatically.
- [ ] Compute basic health metrics sufficient to flag catastrophic geometry: finite-point ratio, point count, extreme-spread/outlier ratio, invalid coordinates, and basic depth distribution sanity.
- [ ] Do not pretend Geometry Health proves real-world depth accuracy.
- [ ] If Geometry Health is poor, mark geometry non-authoritative/PARTIAL or FAIL as required, but still serialize evaluation point-cloud files so the user can judge the result.

**Smoke acceptance:** catastrophic NaN/empty data is detected; non-empty imperfect geometry is preserved rather than hidden.

---

### Task 8: Run Bundle, PLY and USDA Export

**Files:**
- Create: `Tools/Stage06_08/conceptghost_io.py`
- Modify: integration/export custom node module.

**Interfaces:**
- Consumes: SceneBundle.
- Produces: self-contained unique run folder, canonical PLY, USDA `UsdGeomPoints`, geometry JSON, manifest.

- [ ] Generate a unique immutable run ID and never overwrite previous runs.
- [ ] Copy the source image into the run-local `source/` directory.
- [ ] Write binary or efficient PLY with canonical XYZ/RGB.
- [ ] Write ASCII USDA containing `UsdGeomPoints` with positions, widths suitable for viewing, displayColor, and canonical metadata.
- [ ] Save manifests with exact source/engine/preset/parameter/hashes/provenance/warnings/output paths.
- [ ] Use relative paths inside the run package wherever possible.

**Smoke acceptance:** PLY and USDA parse structurally and report the same point count.

---

### Task 9: Separate Maya Worker and Maya Ghost Assembly

**Files:**
- Create: `Tools/Stage06_08/conceptghost_maya_worker.py`
- Create: `Tools/Stage06_08/run_maya_worker.bat`

**Interfaces:**
- Consumes: SceneBundle manifest, run-local source image, pointcloud USDA, Atlas camera data.
- Produces: `.ma`, `.fbx`, `maya_manifest.json`.

- [ ] Discover supported Maya/mayapy path without modifying global PATH.
- [ ] Load MayaUSD in the Maya process.
- [ ] Create `matchedCamera_LOCKED` from authoritative Atlas projection/transform.
- [ ] Create `artistCamera`.
- [ ] Create source image plane/plate using the run-local image.
- [ ] Create MayaUSD proxy/stage referencing the run-local Ghost USDA rather than one Maya transform per point.
- [ ] Save the `.ma` artist entry file.
- [ ] Export FBX with matched camera and any validated exportable mesh context; do not claim the canonical point cloud is carried by FBX.
- [ ] Write `maya_manifest.json` with exporter status and paths.

**Smoke acceptance:** Maya batch can generate files without importing Maya Python packages into the ComfyUI interpreter.

---

### Task 10: Master End-to-End Wiring

**Files:**
- Modify: `Tools/Stage06_08/build_conceptghost_master.py`
- Regenerate: `Workflows/Project/ConceptGhost_Master.json`

**Interfaces:**
- Wires Tasks 2–9 into one graph.

- [ ] Route one source image through Atlas camera and selected geometry engine.
- [ ] Route Compare Both through independent secondary evidence/output without promotion/fusion.
- [ ] Normalize primary geometry into CanonicalGeometry.
- [ ] Always run required reprojection/health evidence and canonical export when their upstream inputs exist.
- [ ] Automatically request Maya Worker output for a valid authoritative SceneBundle.
- [ ] Show run result/status/output paths in the right-side workflow zone.
- [ ] Keep optional mesh groups present but disabled/not on the critical path.

**Smoke acceptance:** one Queue/Run initiates the complete graph; no manual second workflow is required.

---

### Task 11: Vertical Slice Operational Test

**Files:**
- Create: `Reports/ConceptGhost_Stage08_vertical_slice_report.json`

**Interfaces:**
- Consumes: one representative project image.
- Produces: first user-judgable end-to-end result.

- [ ] Load one concept image in the Master workflow.
- [ ] Execute default `Max Reference / Auto / DA3 / Compare Both OFF` once.
- [ ] Confirm only operational requirements: camera branch executed, primary geometry executed, canonical point count > 0, PLY/USDA written, diagnostics written, Maya Worker attempted.
- [ ] If DA3 is operationally blocked, record the blocker and run an explicit MoGe evaluation run rather than silently changing the primary result.
- [ ] Preserve all outputs even when geometry health is poor.
- [ ] Record paths/hashes/file sizes/status in the vertical-slice report.

**Acceptance:** the user can inspect a real canonical point cloud and, when Maya Worker succeeds, open the Maya Ghost. This is the project continuation decision point. No visual refinement is required before this checkpoint.

---

### Task 12: Freeze the First Evaluation Build

**Files:**
- Create: `Reports/ConceptGhost_v0.8_evaluation_build_report.json`
- Create: `ConceptGhost_v0.8_Evaluation_Build.zip`

- [ ] Hash all production workflow/tool files.
- [ ] Package the Master workflow, custom integration code, config, launcher, and evaluation report without duplicating heavyweight model weights.
- [ ] Upload versioned artifacts to the canonical ConceptGhost Drive layout without overwriting prior stages.
- [ ] Mark Stage 9 parameter tuning and Stages 10–12 meshes explicitly deferred until after user evaluation.

**Acceptance:** there is one reproducible v0.8 evaluation build representing the first meaningful go/no-go result.

---

## Self-Review

- Spec coverage: Stage 6 Master workflow, Stage 7 canonical contracts/gates, and Stage 8 Maya/PLY/USD/FBX handoff are all mapped to concrete tasks.
- No mesh-quality task is on the critical path.
- No silent DA3/MoGe fallback or fusion is introduced.
- Poor-but-readable geometry is preserved for the user's go/no-go evaluation.
- Mandatory defaults match the approved Runtime/UI policies.
- All required output formats and status semantics are included.
- No permanent PATH changes or Maya imports into ComfyUI Python are required.
- Operational tests are intentionally minimal and do not create another refinement loop before the Stage 8 evaluation build.
