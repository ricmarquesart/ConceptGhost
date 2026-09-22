# ConceptGhost P10-Lab — Refined Solver Fusion = P9 + P10

Experimental, isolated laboratory for multiview scene completion.

Current execution status is tracked in
[`docs/08_GATE_STATUS.md`](docs/08_GATE_STATUS.md).

## Current architecture

The official relationship is now:

- **Baseline branch = Baseline only**
- **P9 = a functionally identical copy of Baseline**
- **Refined Solver Fusion = P9 + P10**

P9 does not contain a separate solver-fusion refinement layer. Before P10 starts, P9 must reproduce Baseline behavior and expected output. P10 is the first stage that adds new behavior.

The lab therefore consumes one `ConceptGhost_P9_CompletionBundle.zip`. During isolated development, a direct Baseline-equivalent bundle may also be accepted because P9 and Baseline are contractually equivalent.

## Core path

P9 (= Baseline)
→ P9 Completion Bundle
→ temporary panoramic working context
→ automatic scene-relative camera paths
→ geometry control frames + disocclusion masks
→ masked WAN completion
→ source-preserving composite
→ SphereSfM
→ COLMAP dense reconstruction
→ P9/Baseline registration and fusion
→ local cleanup
→ texture recovery
→ original-view regression
→ Maya export

## Visible checkpoints

Every flight exposes four node-visible and resumable previews:

1. raw geometry control video;
2. disocclusion/hole-mask video;
3. WAN-filled video before source restoration;
4. source-preserving composite video.

Checkpoint manifests include SHA-256 digests. A changed or missing artifact is
not resumable.

## Preview Versions

Each gate that reaches a meaningful executable or visual milestone publishes an
isolated Preview Version with the relevant workflow/nodes, test instructions,
expected outputs, known limitations, validation evidence and SHA-256. Gate 1 is
contract-only and has no visual node preview; the first user-facing preview is
the Gate 2 Completion Bundle loader/validator.

## Flight scaling

The default plan is three initial flights plus an adaptive budget of one. The
planner is data-driven and accepts ten or more initial flights without copying
the ComfyUI subgraph. Additional flights stay inside the local completion
envelope; more flights do not imply a full 360 exploration.

The geometry control policy is `raw holes`: no P10 hole fill, discontinuity
bridging, unknown-region smoothing, or silhouette extrapolation before mask
generation. This policy creates a P10-only derivative and never mutates the
standalone Baseline mesh.

## Identity gate

P10 must never be used to justify changes inside P9. If P9 diverges from Baseline before the P10 boundary, the Refined branch fails the architecture contract.

## Not the final product

Gaussian Splatting / Brush are not required deliverables. 3DGS may later be used as an optional preview only.

## Hardware target

RTX 2080 Ti, 11 GB VRAM. Use quantized WAN, sequential workers, one path at a time, explicit unload and disk checkpoints.

## Repository rule

This directory is experimental. Promotion means connecting proven P10 modules **after P9** in the Refined Solver Fusion branch while leaving the normal Baseline branch unchanged.
