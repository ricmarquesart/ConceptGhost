# SplatKit / Matrix-Style Adaptation

## Refined-branch position

This adaptation begins **after P9**, where P9 is a copy of Baseline. It does not replace or modify P9.

## Reuse

- virtual camera geometry rendering
- control videos
- disocclusion masks
- masked WAN novel-view completion
- source-preserving composite
- SphereSfM camera recovery
- COLMAP-compatible dataset

## Do not adopt as final destination

- manual drone operation
- mandatory 360 exploration
- Brush
- Gaussian Splat as final output

## Panorama policy

The public pipeline is panorama-centered, so the first lab preserves a temporary panoramic working representation internally. The user still supplies a normal ConceptGhost image. P9/Baseline camera data positions and locks the original image region; generated surroundings are temporary context.

## Automatic flight

Initial paths:
- shallow left arc
- shallow right arc
- short forward/side translation
- configurable adaptive paths only if important defects remain

Paths scale to scene size and pass a collision gate.

The initial count is data, not graph topology. The reviewed default is three
initial paths with one adaptive slot; a quality experiment may request ten or
more paths while reusing the same flight runner. The completion envelope stays
local unless explicitly changed, so flight count does not silently become a
full 360 reconstruction.

## Raw-hole and preview adaptation

`SplatKit_CameraPlotRenderControlGeo` is adapted to consume a P10 evidence-mesh
derivative with hole fill, discontinuity bridging, unknown-region smoothing and
silhouette extrapolation disabled. Unknown pixels render black and an explicit
binary mask is preserved.

Each flight publishes four visual outputs in the workflow: control geometry,
hole mask, raw WAN fill and high-resolution source-preserving composite. This
extends the reference workflow's saved control/generated videos into an
explicit ConceptGhost checkpoint contract.

## 11 GB policy

- WAN GGUF/quantized path
- one path at a time
- conservative initial resolution
- explicit GPU unload
- disk checkpoints
- no 8K proof-of-concept requirement

## Fusion policy

Observed reliable P9/Baseline region → P9/Baseline wins.
Unseen region → multiview reconstruction allowed.
Transition region → narrow blend/remesh.
Generated conflict in strongly observed region → reject generated geometry.

Hunyuan remains deferred as a possible future object-only fallback.
