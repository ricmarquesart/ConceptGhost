# R6L — Known-Camera Depth-Anchored Hole Fusion Plan

Date: 2026-09-25 UTC
Status: PLANNED / NEXT RECONSTRUCTION QUALITY LANE

## Why R6L exists

The current Gate 6 path asks COLMAP to recover geometry from source-preserved
WAN views. On the rejected target-PC run, sparse connectivity remained weak,
dense fusion stopped gaining useful points early, and the final mesh did not
correspond to the holes the artist expected to fill.

Increasing frame count and concentrating all five drones on a short scene region
is a useful A/B test of whether the limiting factor is insufficient overlap.
However, generated WAN pixels are not guaranteed to be photometrically
multiview-consistent. More frames alone may therefore remain insufficient.

## Proposed alternate reconstruction lane

ConceptGhost already knows every Gate 4 camera pose and already preserves
original/P9-supported pixels outside the generated hole mask. R6L will exploit
that structure instead of requiring generated pixels to behave like a normal
photogrammetry capture.

For selected Gate 5 composite frames:

1. infer a dense depth map for the whole composite;
2. render/project P9 into the same known camera;
3. on pixels that are still P9-known, robustly register the inferred depth to
   authoritative P9 depth;
4. keep only generated/hidden-region depth after registration;
5. unproject those pixels with the exact Gate 4 intrinsics and camera-to-world
   matrix into P9 canonical world meters;
6. fuse observations across frames and independent drone missions;
7. retain provenance, mission support and confidence for every fused region;
8. mesh only the supported new-hole geometry;
9. send that P10-only candidate into the existing Gate 7
   provenance/confidence/free-space/protected-fusion chain.

## Why this addresses the observed failure

The scale is anchored per view against visible P9 geometry rather than inferred
from generated imagery alone.

The output is generated specifically from pixels inside the known missing-area
mask, so the candidate is naturally targeted at holes instead of arbitrary
scene surfaces.

The known camera matrices remove a second camera-estimation problem.

Independent-mission support can still reject one-view hallucinations before
Gate 7 fusion.

## Model/runtime candidates

The existing project already carries metric depth infrastructure for
Depth-Anything and MoGe. R6L should begin with the lighter metric-depth route
for per-frame depth and keep MoGe as a quality/reference alternative. Model
choice must remain isolated from P9 authority.

## A/B acceptance test

Use the user's new short-scene, high-frame-count five-drone run.

Compare:

A. current known-camera COLMAP Gate 6;
B. R6L depth-anchored known-camera fusion.

Both outputs must be exported in P9 canonical meters and through the R6K
Maya-centimeter diagnostic bridge.

The useful winner is decided by measurable hole-region coverage, independent
mission support, P9 registration residuals and direct Maya comparison. No Gate 8
promotion occurs during this experiment.
