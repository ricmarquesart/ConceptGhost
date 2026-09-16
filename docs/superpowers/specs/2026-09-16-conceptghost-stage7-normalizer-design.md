# ConceptGhost — Stage 7 Canonical Integration / Normalizer Design

Date: 2026-09-16
Status: Approved architecture basis; parameter values remain evidence-driven candidates until Stage 9 benchmarking
Project: ConceptGhost

> MANDATORY DEVELOPMENT READ BEFORE STAGE 7 IMPLEMENTATION

This document defines how Atlas, DA3, and MoGe are converted into one stable ConceptGhost scene representation.

## 1. Canonical coordinate system — APPROVED

ConceptGhost canonical scene space is:

```text
Right-handed
Y-Up
+X = right
+Y = up
-Z = camera forward
```

Image space remains:

```text
U = right
V = down
origin = image top-left
```

All adapters must explicitly convert into this canonical convention. No downstream exporter may infer axis conventions heuristically.

## 2. Authority model

```text
CAMERA / PROJECTION
Atlas = authoritative

DEPTH / SHAPE EVIDENCE
DA3 or MoGe = authoritative source of geometry evidence

COLOR
Original source image = authoritative

FINAL 3D SPACE
ConceptGhost Canonical Scene = authoritative
```

Native DA3/MoGe camera/point outputs remain diagnostic evidence.

## 3. CameraBundle

Stage 7 normalizes Atlas results into a stable contract:

```text
CameraBundle
├── source_width
├── source_height
├── fx
├── fy
├── cx
├── cy
├── K[3x3]
├── projection_type
├── camera_to_world / world_to_camera
├── solver_requested
├── solver_used
├── solver_confidence
├── quality_status
└── coordinate_convention
```

Downstream code consumes CameraBundle, not Atlas-private node internals.

## 4. GeometryEvidence contract

Each engine adapter emits a common evidence contract:

```text
GeometryEvidence
├── engine
├── raw_depth / point_map
├── depth_semantics
├── confidence
├── valid_mask / sky_mask
├── normals
├── native_intrinsics
├── native_camera
├── source_pixel_mapping
├── model/checkpoint
├── inference_parameters
└── native_coordinate_convention
```

`depth_semantics` is mandatory and must distinguish at least:
- camera-Z depth;
- ray distance;
- inverse/relative depth;
- metric depth;
- engine-specific point-map semantics.

No adapter may assume that a value named `depth` has the same geometric meaning across engines.

## 5. DA3 integration

### 5.1 Baseline path

Preserve the unchanged public/native DA3 result first.

For 3D reconstruction, use raw depth rather than display-normalized depth. The ComfyUI-DepthAnythingV3 project explicitly recommends Raw normalization for point-cloud reconstruction and recommends Mono/Metric variants when sky filtering is desirable.

Conceptual baseline:

```text
source pixel UV
+ DA3 depth/confidence
+ Atlas CameraBundle
-> Atlas ray
-> canonical XYZ
-> canonical RGB from source image
```

### 5.2 Candidate DA3 parameter study

These are benchmark candidates, NOT final hard-coded values:

```text
Normalization:
Raw for 3D reconstruction

Sky filtering:
enabled when model provides sky mask

Point downsample:
1 for Max Reference candidate
>1 only for Balanced/Fast after benchmark

Confidence:
native ComfyUI reference starts at 0.10 normalized threshold
official DA3 exporter uses percentile-based filtering (default 40%)
official DA3 example also shows 30% percentile at higher-resolution export

Processing resolution:
official API default: 504
official example: 1024
Stage 9 must measure 504 / ~756 / 1024 or the closest safe values supported by the chosen workflow
```

Candidate model comparison for single concept images:
- DA3MONO-LARGE: monocular depth + sky;
- DA3METRIC-LARGE: metric depth + sky;
- DA3-LARGE / refreshed -1.1 family where the active workflow supports it;
- current public workflow model as baseline, unchanged.

No model becomes `Max Reference` purely because it is larger or metric. Concept art may not obey photographic metric priors.

### 5.3 Atlas-conditioned DA3 experiment

The official DA3 API accepts optional camera extrinsics and intrinsics for pose-conditioned depth estimation.

Stage 7 research must therefore compare:

```text
A. DA3 unconditioned
   -> post-normalize with Atlas

B. DA3 conditioned with Atlas camera inputs where the official API path supports it
   -> then normalize/validate
```

This is an A/B refinement, not an automatic replacement of the current DA3 ComfyUI baseline.

If camera-conditioned DA3 materially improves geometry consistency, an adapter may be added after compatibility and environment-safety validation.

## 6. MoGe integration

### 6.1 Baseline path

Native ComfyUI MoGe currently exposes:
- `resolution_level` 0–9, default 9;
- `fov_x_degrees`, where 0 means auto-estimate;
- `force_projection`, default true;
- `apply_mask`, default true.

Baseline evidence is preserved unchanged.

### 6.2 Atlas-conditioned MoGe experiment

This is a high-priority refinement.

The MoGe project explicitly supports optional known FOV, and documents that supplying true FOV can improve accuracy.

Therefore Stage 7 must A/B test:

```text
A. MoGe FOV = auto

B. MoGe FOV = Atlas horizontal FOV
```

The Atlas-conditioned result still passes through the same Canonical Normalizer and health gates.

This does not make MoGe the camera authority; it uses Atlas as a camera constraint to improve MoGe geometry generation.

### 6.3 Candidate MoGe parameters

Candidate Max Reference baseline:

```text
resolution_level = 9
force_projection = true
apply_mask = true
FOV = Atlas FOV candidate path
```

For mesh-only evaluation:
```text
decimation = 1
discontinuity_threshold = 0.04 reference default
texture = true
```

The official ComfyUI workflow also applies an auto-resize strategy for very large inputs, reducing images wider than 2048 to a 2048 longer-edge working size. Stage 9 should test whether this remains optimal for ConceptGhost environments.

Model candidate:
- MoGe-2 ViT-L / normal-capable variant where the active ComfyUI integration supports it safely.
- MoGe-3 is future research, not current V1 dependency.

## 7. Canonical point construction

For each valid source pixel:

```text
UV
+ Atlas CameraBundle
+ engine depth/geometry evidence
-> canonical ray / 3D position
```

Color always comes from the original concept image:

```text
CanonicalPoint
├── X Y Z
├── R G B
├── confidence
├── valid
├── source_u source_v
├── source_engine
└── provenance
```

## 8. Filtering pipeline

Native evidence is never destroyed.

```text
geometry/native/<engine>/
```

Canonical output applies validated filtering:

```text
raw evidence
-> finite/positive validity
-> sky/invalid mask
-> confidence filtering
-> depth-discontinuity filtering
-> outlier/streamer filtering
-> canonical point cloud
```

The DA3-Blender workflow is a reference source for confidence filtering, depth-discontinuity handling, streamer reduction, and point presentation.

## 9. Two separate validation gates

### Gate A — Integration Consistency

Reprojection validates math and coordinate integration.

```text
source UV
-> canonical XYZ
-> Atlas projection
-> UV'
```

Metrics:
- mean pixel error;
- median;
- p95;
- max;
- tested count;
- invalid count.

Important:
Reprojection DOES NOT prove that predicted depth is correct. Points at different depths on the same camera ray can project to the same pixel.

### Gate B — Geometry Health

Stage 7 also records:
- valid coverage;
- confidence distribution;
- non-finite count;
- depth range/percentiles;
- edge rejection ratio;
- outlier rejection ratio;
- point count;
- large depth-jump statistics;
- sky/invalid coverage.

This detects clearly broken geometry even when reprojection passes.

Stage 9 performs the later qualitative/reference-quality benchmark.

## 10. Scale

V1 default:

```text
scale_mode = relative
```

Do not claim physical metres from arbitrary concept art.

Metric predictions from DA3Metric/MoGe-2 may be retained as evidence, but ConceptGhost must label scale provenance honestly.

Future:

```text
scale_mode = anchored
```

may use a known real-world measurement.

## 11. Compare Both

DA3 and MoGe produce separate canonical results under the same Atlas camera.

No fusion in V1.

```text
DA3 -> CanonicalGeometry A
MoGe -> CanonicalGeometry B
```

If primary fails and secondary passes, preserve the secondary but keep the run PARTIAL; do not silently promote it.

## 12. SceneBundle

Stage 7 output contract:

```text
SceneBundle
├── CameraBundle
├── CanonicalGeometry
├── SourceImage
├── GeometryHealth
├── ReprojectionReport
├── EngineMetadata
├── CoordinateConvention
├── ScaleConvention
└── Manifest
```

Stage 8 exporters consume SceneBundle and must not depend directly on DA3/MoGe internal node outputs.

## 13. Stage 7 files

Expected:

```text
camera/camera.json

geometry/
├── native/<engine>/...
└── canonical/
    ├── pointcloud.ply
    └── geometry.json

diagnostics/
├── reprojection_report.json
├── reprojection_overlay.png
└── geometry_health.json

manifest.json
```

## 14. Stage 7 acceptance

```text
valid Atlas Camera
+ valid GeometryEvidence
+ canonical conversion valid
+ Integration Consistency PASS
+ Geometry Health acceptable
= SceneBundle READY FOR STAGE 8
```

## 15. Parameter policy

No parameter is declared “best” from documentation alone.

The project uses:
1. upstream defaults as reproducible baseline;
2. community/proven alternatives as candidate configurations;
3. controlled A/B tests on ConceptGhost scenes;
4. Stage 9 evidence to freeze Max Reference / Balanced / Fast Test.

This prevents overfitting the pipeline to one demo or one creator’s settings.
