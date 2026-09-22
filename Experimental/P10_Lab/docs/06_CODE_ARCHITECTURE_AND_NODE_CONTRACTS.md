# Code Architecture and Node Contracts

## Integration boundary

The Refined branch is a Baseline-equivalent P9 graph followed by P10. No P10
node is allowed on the standalone Baseline branch. P10 receives the versioned
completion bundle and treats its camera, scale and observed evidence as locked
authorities.

Gate 2 now implements this boundary against the real v1.53 official run pack.
It consumes the existing authoritative PrimaryMesh NPZ instead of inventing a
parallel P9 mesh format.

## Implemented Gate 2 boundary components

`p10_lab/p9_boundary.py` owns official-run validation, Completion Bundle
creation/loading, safe ZIP extraction and Baseline-vs-P9 identity comparison.

`p10_lab/contracts.py` owns Completion Bundle v0.3 validation, artifact hashes,
camera identity and normalized run metadata.

`p10_lab/preview_nodes.py` exposes two dependency-free ComfyUI preview nodes:

1. `P10 P9 Completion Bundle Builder`
2. `P10 P9 Bundle Loader / Validator`

These nodes are inspection/validation surfaces. They do not mutate P9 or start
any later P10 generation stage.

## Planned node sequence

1. P10 P9 Bundle Loader
2. P10 Scene Validator
3. P10 Temporary Panorama Context
4. P10 Completion Envelope
5. P10 Automatic Path Planner
6. P10 Path Collision Gate
7. P10 Raw-Hole Control Renderer
8. P10 Disocclusion Mask Builder
9. P10 WAN Masked Completion
10. P10 Source-Preserving Composite
11. P10 Generated View Collector
12. P10 SphereSfM Reconstruction
13. P10 Dense Reconstruction
14. P10 Geometry Quality Analyzer
15. P10 P9/Baseline Registration
16. P10 Known/Generated Fusion
17. P10 Local Remesh and Cleanup
18. P10 Texture Recovery
19. P10 Original View Regression Gate
20. P10 Maya Export

## Gate 2 identity behavior

The official source branch is inferred only from the production branch-mode
authority:

- `Baseline / P9` → laboratory `source_stage=baseline`;
- `Refined / P9 Clone` → integrated `source_stage=p9`.

Both require `source_equivalent_to=baseline`. The adapter also provides an
explicit identity comparator for a matched Baseline/P9 run pair. A mismatch in
source image, canonical camera, PrimaryMesh, scene identity, geometry profile,
coordinate convention or relevant scale authority fails the comparison.

## Reusable flight runner

Nodes 6–11 operate on one `CameraPath` data item. The workflow iterates that
runner sequentially; it does not duplicate a fixed WAN subgraph for every new
flight. `FlightPlanConfig` supplies the initial path count and adaptive budget.

## Per-flight outputs

| Node | Required visual output | Provenance |
|---|---|---|
| Raw-Hole Control Renderer | control video | `p9_raw_hole_control` |
| Disocclusion Mask Builder | binary mask video | `p10_disocclusion_mask` |
| WAN Masked Completion | generated video | `p10_wan_generated` |
| Source-Preserving Composite | composite video | `source_locked_composite` |

Each output is also a checkpoint artifact. The manifest contains a relative
path and SHA-256 digest. It also contains a context digest derived from the
source run and input digests, flight definition, control policy, and adapter
versions. A validated checkpoint can resume only while the context and every
artifact still match.

## Raw-hole contract

The control renderer consumes a P10-only derivative of `PrimaryMesh`. It may
remove unsupported faces using P9 confidence/boundary evidence, but it may not
write back to `PrimaryMesh`. Its default policy prohibits filling holes,
bridging depth discontinuities, smoothing unknown regions, and extrapolating
silhouettes.

## Authority and provenance

Authority order is:

1. observed source/P9 Baseline evidence;
2. lower-confidence P9 reconstruction;
3. P10 generated view evidence;
4. P10 multiview reconstruction;
5. narrow transition/repair geometry.

The original-camera regression gate rejects a fused result that changes a
strongly observed region beyond the approved tolerance.


## Authoritative Gate 6+ architecture refinement — 2026-09-22

The earlier conceptual node list above predates the real Gate 6 implementation. From Gate 6 onward, the authoritative architecture is:

12. **P10 Known-Camera COLMAP Reconstruction** — primary perspective reconstruction path using the exact P9-derived virtual cameras. SphereSfM remains optional ERP validation/fallback, not the primary pose authority.
13. **P10 Dense Reconstruction / Evidence Producer** — COLMAP undistortion, geometric PatchMatch and stereo fusion; retain geometric depth maps, normals and consistency graphs for later visibility/free-space evidence.
14. **P10 Pre-Fusion Geometry Quality** — current Poisson candidate plus the planned Delaunay visibility-aware candidate. The dual-mesh extension is activated with Gate 7 and does not reopen Gate 6 as a blocker.
15. **P10 P9/Baseline Registration** — register reconstructed P10 geometry into canonical P9 coordinates.
16. **P10 Geometry Confidence + Known/Generated Fusion** — authority-aware fusion with confidence diagnostics; confidence refinement remains OFF by default.
17. **P10 Free-Space-Aware Transition Handling** — consume OCCUPIED / CONFIRMED_FREE / UNKNOWN / CONFLICT evidence; CONFIRMED_FREE is a no-fill/no-bridge constraint.
18. **P10 Local Remesh / Defect Repair** — distinguish VALID_OPENING, MISSING_SURFACE_UNKNOWN, FALSE_SURFACE_IN_CONFIRMED_FREE and CONFLICT_REGION before bounded repair.
19. **P10 Texture Recovery + Original-View Regression**.
20. **P10 Maya Export**.

### Camera/image contract for Gate 6

The authoritative pose remains P9-derived, but intrinsics must be expressed in the actual saved reconstruction image viewport. Gate 5 applies ComfyUI center-crop + resize before saving the WAN/source-preserved composite. Gate 6 therefore stores a deterministic camera-image transform and uses those transformed intrinsics for COLMAP. Reusing pre-WAN intrinsics against a resized composite is invalid and must fail closed.

### Free-space modules

Planned native modules:
- `colmap_dense_io.py` — dense geometric evidence reader;
- `free_space_evidence.py` — sparse ray-carving accumulator;
- `free_space_constraints.py` — FREE/OCCUPIED/UNKNOWN/CONFLICT classification and no-fill constraints;
- `free_space_preview.py` — ComfyUI-only 3D diagnostics.

See `docs/12_FREE_SPACE_VISIBILITY_CARVING_POLICY.md` for the full contract.
