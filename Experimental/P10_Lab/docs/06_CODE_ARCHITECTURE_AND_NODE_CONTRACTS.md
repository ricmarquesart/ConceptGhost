# Code Architecture and Node Contracts

## Integration boundary

The Refined branch is a Baseline-equivalent P9 graph followed by P10. No P10
node is allowed on the standalone Baseline branch. P10 receives the versioned
completion bundle and treats its camera, scale and observed evidence as locked
authorities.

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
