# ConceptGhost P10-Lab — Refined Solver Fusion = P9 + P10

Experimental, isolated laboratory for multiview scene completion.

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

## Identity gate

P10 must never be used to justify changes inside P9. If P9 diverges from Baseline before the P10 boundary, the Refined branch fails the architecture contract.

## Not the final product

Gaussian Splatting / Brush are not required deliverables. 3DGS may later be used as an optional preview only.

## Hardware target

RTX 2080 Ti, 11 GB VRAM. Use quantized WAN, sequential workers, one path at a time, explicit unload and disk checkpoints.

## Repository rule

This directory is experimental. Promotion means connecting proven P10 modules **after P9** in the Refined Solver Fusion branch while leaving the normal Baseline branch unchanged.
