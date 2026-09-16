# ConceptGhost — Stage 9 Benchmark, Calibration, and Preset Freeze Design

Date: 2026-09-16
Status: APPROVED architecture for Stage 9
Project: ConceptGhost

> MANDATORY DEVELOPMENT READ BEFORE STAGE 9 IMPLEMENTATION

This document defines how ConceptGhost benchmarks DA3/MoGe variants, evaluates camera-conditioned paths, freezes reproducible presets, and keeps the final quality decision under artist control.

Read together with:

```text
docs/superpowers/specs/2026-09-16-conceptghost-stage7-normalizer-design.md
docs/superpowers/specs/2026-09-16-conceptghost-stage8-maya-export-design.md
docs/superpowers/research/2026-09-16-conceptghost-consolidated-research-and-implementation-guidance.md
docs/superpowers/specs/2026-09-16-conceptghost-runtime-behavior-policy.md
```

---

# 1. Stage 9 goal

Stage 9 does not add a new production geometry engine.

Its purpose is to determine, with repeatable evidence, the best validated parameter sets for the existing V1 engines and to decide whether camera-conditioned variants should become the production behavior.

Primary outputs:

```text
DA3 / Fast Test v1
DA3 / Balanced v1
DA3 / Max Reference v1

MoGe / Fast Test v1
MoGe / Balanced v1
MoGe / Max Reference v1
```

Stage 9 also resolves:

```text
DA3 Atlas-conditioned path -> adopt | keep experimental | reject
MoGe Atlas-FOV path       -> adopt | keep experimental | reject
confidence policy
edge/discontinuity filtering policy
point-density policy
processing-resolution policy
```

---

# 2. Benchmark images are selected by the user

ConceptGhost does NOT define a permanent fixed benchmark set.

The user selects the images for each benchmark session.

Rules:

```text
- no automatic public-image selection
- no hidden benchmark corpus
- no requirement for exactly N images
- all candidate configurations inside one benchmark session use the exact same selected images
- source identity is recorded by filename, resolution, and hash
```

The same images may be reused later when useful, but no image set is permanently frozen by the system.

---

# 3. Benchmark session identity

Every benchmark session is auditable.

Suggested structure:

```text
Benchmark/
└── <benchmark_session_id>/
    ├── sources/
    ├── configs/
    ├── results/
    ├── metrics/
    ├── screenshots/
    ├── artist_review.json
    └── report.md
```

Record at minimum:

```text
benchmark_session_id
source files
source hashes
source resolutions
engine/model versions
all resolved parameters
software versions
GPU/runtime context where practical
run IDs
technical gate outcomes
artist review outcome
```

---

# 4. Candidate paths

The initial Stage 9 comparison matrix includes:

```text
A. DA3 baseline
   Atlas camera + current/public DA3 path + ConceptGhost Normalizer

B. DA3 Atlas-conditioned
   Atlas CameraBundle -> DA3 official API intrinsics/extrinsics -> Normalizer

C. MoGe baseline
   Atlas camera + MoGe Auto FOV + Normalizer

D. MoGe Atlas-conditioned
   Atlas horizontal FOV -> MoGe fov_x -> Normalizer
```

All candidates must pass through the same:

```text
Stage 7 canonical coordinate convention
Integration Consistency Gate
Geometry Health Gate
Stage 8 export path
Maya artist review
```

No candidate gets a special validation shortcut.

---

# 5. Technical validity comes before artistic comparison

A candidate is not ranked visually if it is structurally invalid.

Required preconditions:

```text
valid camera
+ valid GeometryEvidence
+ valid canonical conversion
+ Integration Consistency PASS
+ Geometry Health acceptable
+ valid USD Ghost
+ generated Maya Ghost
= READY FOR ARTIST REVIEW
```

If a candidate fails a mandatory technical gate:

```text
benchmark_status = TECHNICALLY_INVALID
```

It is not treated as merely a lower-scoring artistic result.

---

# 6. Automatic metrics

Automatic metrics are evidence, not an autonomous final quality verdict.

Track at minimum where applicable:

```text
reprojection mean / median / p95 / max
valid coverage
point count
non-finite count
confidence distribution
depth range / percentiles
sky/mask coverage
edge rejection ratio
outlier rejection ratio
large depth-jump statistics
runtime
peak VRAM where measurable
peak RAM where measurable
disk output size
USD/Maya load time
viewport responsiveness observations
```

Add streamer-specific metrics when a robust definition is available.

Do not invent a single opaque “quality score” that overrides the artist review.

---

# 7. Artist review in Maya is decisive

The final usefulness decision belongs to the user/artist.

For every technically valid candidate, Stage 9 should provide a Maya Ghost suitable for direct review.

Standard review dimensions:

```text
matched-camera agreement
foreground/background separation
ground/terrain continuity
architecture/large-plane coherence
thin-structure survival
streamer artifacts
noise / floating points
occlusion boundary quality
off-camera spatial usefulness
blockout usefulness with normal Maya primitives
```

Simple qualitative values are sufficient:

```text
good
acceptable
poor
```

A numeric artistic score is not required.

---

# 8. Matched-camera and off-camera evaluation are separate

A Ghost can look correct from the original image while being poor in 3D.

Therefore review both:

```text
VIEW A — matched-camera fidelity
VIEW B — off-camera spatial usefulness
```

Off-camera usefulness is especially important because ConceptGhost exists to support manual 3D blockout after leaving the solved camera view.

---

# 9. The user makes the final visual choice

Example record:

```text
source = Village_Concept_03

DA3 baseline             = valid / usable
DA3 Atlas-conditioned    = valid / stronger architecture
MoGe Auto FOV            = valid / background distortion
MoGe Atlas FOV           = valid / strongest spatial Ghost

artist_preference = MoGe Atlas FOV
```

The system records the user's decision.

It does not automatically declare a global engine winner.

---

# 10. No global engine winner is required

Stage 9 may reveal scene-dependent behavior.

Example:

```text
Scene A -> DA3 better
Scene B -> MoGe better
Scene C -> DA3 Atlas-conditioned better
Scene D -> MoGe Atlas-FOV better
```

That is acceptable.

V1 continues to expose:

```text
Geometry = DA3
Geometry = MoGe
```

The main purpose of Stage 9 is to define the best validated parameter sets per engine.

---

# 11. Presets resolve per engine

A user-facing preset name describes an objective, not identical numeric values across engines.

Example:

```text
Preset = Max Reference
Geometry = DA3
-> resolves to DA3_MAX_REFERENCE_v1

Preset = Max Reference
Geometry = MoGe
-> resolves to MOGE_MAX_REFERENCE_v1
```

The UI remains simple while engine-specific parameters remain reproducible.

---

# 12. Preset versioning

Every preset is versioned.

Manifest example:

```text
preset.name = "Max Reference"
preset.version = 1
geometry.engine = "DA3"
preset.resolved_parameters = {...}
```

If improved later:

```text
Max Reference v2
```

Old runs remain interpretable because they preserve resolved parameters and version.

---

# 13. Preset intent

## Fast Test

Purpose:

```text
quickly determine whether the camera and broad geometry are plausible
```

It should answer:

```text
Is the camera usable?
Is the basic depth structure plausible?
Is the selected engine functioning?
Is a Max Reference run worth the cost?
```

Fast Test is not simply “bad Max Reference”.

## Balanced

Purpose:

```text
retain most practical Ghost usefulness with materially lower cost
```

Balanced exists only if a meaningful cost/quality trade-off is demonstrated.

Do not force a Balanced preset that is clearly worse without useful savings.

## Max Reference

Purpose:

```text
highest validated stable reference quality
```

Quality is primary.

Higher resolution, more points, or greater resource cost are allowed when they materially improve the Ghost and remain stable.

“Max Reference” does NOT mean setting every numerical parameter to its theoretical maximum.

---

# 14. Parameter study policy

Parameter exploration is progressive, not brute-force combinatorial search.

Recommended order:

```text
1. processing resolution / model mode
2. camera conditioning
3. confidence policy
4. edge/discontinuity filtering
5. point sampling/density
6. secondary cleanup parameters only if evidence justifies them
```

Example:

```text
DA3 504 vs 1024
```

If no meaningful improvement exists, do not waste time exhaustively testing every intermediate value.

If a meaningful difference exists, test selected intermediate candidates.

---

# 15. Confidence study

Candidate policies may include:

```text
no/very low threshold
0.05
0.10
0.20
percentile-based filtering
```

Exact candidates depend on the active engine/API semantics.

Evaluate the trade-off:

```text
lower threshold -> more coverage, potentially more noise
higher threshold -> cleaner Ghost, potentially more holes
```

Do not assume the most aggressive confidence filtering is best.

---

# 16. Depth-edge / streamer filtering study

Edge filtering is a major benchmark dimension.

Test selected levels such as:

```text
OFF
mild
medium
strong
```

Goal:

```text
remove artificial foreground-to-background bridges
without destroying legitimate surfaces
```

DA3-Blender remains an implementation/reference source for practical depth-discontinuity and streamer cleanup ideas.

Native evidence must remain unchanged.

---

# 17. Point density study

Inference quality and exported point density are separate variables.

More points do not automatically mean a better Ghost.

Benchmark:

```text
coverage
noise
USD size
Maya load time
viewport usability
blockout usefulness
```

A smaller number of high-quality points may be preferable to a larger noisy cloud.

---

# 18. DA3 camera-conditioning decision

Compare:

```text
DA3 baseline
vs
DA3 + Atlas intrinsics/extrinsics
```

Possible final outcomes:

```text
CONSISTENT_IMPROVEMENT -> candidate for normal production DA3 path
NO_MEANINGFUL_GAIN     -> retain simpler baseline path
UNSTABLE/SCENE_DEPENDENT -> keep experimental/advanced
WORSE                  -> reject
```

No hidden adoption before evidence.

---

# 19. MoGe Atlas-FOV decision

Compare:

```text
MoGe Auto FOV
vs
MoGe Atlas FOV
```

If Atlas FOV produces consistent improvement:

```text
Geometry = MoGe
-> production path may automatically supply Atlas FOV
```

while the Auto-FOV path remains available for baseline/debug evidence.

If improvement is not consistent, do not force conditioning.

---

# 20. Optional external reference baseline

Depth Anything V2 Metric Outdoor may be used as a reference/control on selected exterior scenes.

It is not added to the V1 user-facing Geometry selector by Stage 9.

Purpose:

```text
diagnostic comparison
sanity check
external reference
```

This is especially useful because Atlas itself reverted to it as an exterior default after its own A/B testing.

---

# 21. Evidence package

Each benchmark session should preserve:

```text
selected image identities
all candidate configurations
technical metrics
Stage 7/8 gate outcomes
generated Maya Ghosts
selected screenshots where useful
artist review
final preset decision
```

Heavy evidence may live in Google Drive while lightweight definitions/results may live in GitHub.

---

# 22. Stage 15 reuses the benchmark framework

Future engines such as:

```text
MoGe-3
VGGT
UniDepth V2
Depth Pro
Metric3D V2
GeoWizard
```

should enter through the same architecture:

```text
New Engine
-> GeometryAdapter
-> Stage 7
-> Stage 8
-> Stage 9 Benchmark Framework
```

The user again chooses the images for that future benchmark session.

No permanent benchmark corpus is required.

---

# 23. Stage 9 PASS

Stage 9 is complete when:

```text
DA3 Fast Test v1 defined
DA3 Balanced v1 defined
DA3 Max Reference v1 defined

MoGe Fast Test v1 defined
MoGe Balanced v1 defined
MoGe Max Reference v1 defined
```

and evidence-based decisions exist for:

```text
DA3 Atlas conditioning
MoGe Atlas FOV conditioning
confidence policy
edge filtering
point density
processing resolution
```

Final equation:

```text
USER-SELECTED BENCHMARK IMAGES
+
CONTROLLED CANDIDATE RUNS
+
TECHNICAL GATES
+
MAYA ARTIST REVIEW
+
USER FINAL VISUAL DECISION
=
VERSIONED ENGINE PRESETS
```

---

# 24. One-line implementation instruction

> Stage 9 must benchmark only user-selected images, run all candidate configurations against the same session inputs, reject technically invalid candidates before artistic comparison, preserve automatic evidence without inventing an opaque overall quality score, let the user decide final Maya usefulness, and freeze versioned DA3/MoGe Fast Test, Balanced, and Max Reference parameter sets only after evidence.
