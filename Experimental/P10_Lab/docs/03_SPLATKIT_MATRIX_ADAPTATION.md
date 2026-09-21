# SplatKit / Matrix-Style Adaptation

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

The public pipeline is panorama-centered, so the first lab preserves a temporary panoramic working representation internally. The user still supplies a normal ConceptGhost image. Baseline camera data positions/locks the original image region; generated surroundings are temporary context.

## Automatic flight

Initial paths:
- shallow left arc
- shallow right arc
- short forward/side translation
- optional targeted path only if important defects remain

Paths scale to scene size and pass a collision gate.

## 11 GB policy

- WAN GGUF/quantized path
- one path at a time
- conservative initial resolution
- explicit GPU unload
- disk checkpoints
- no 8K proof-of-concept requirement

## Fusion policy

Observed reliable Baseline region → Baseline wins.
Unseen region → multiview reconstruction allowed.
Transition region → narrow blend/remesh.
Generated conflict in strongly observed region → reject generated geometry.

Hunyuan is deferred as a possible future object-only fallback.
