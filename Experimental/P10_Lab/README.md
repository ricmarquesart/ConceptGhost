# ConceptGhost P10-Lab — Baseline-First Multiview Completion

Experimental, isolated laboratory for completing occluded/unseen geometry after the stable Baseline branch.

## Current decision

P10 starts **after Baseline**, not after P9. P9 enrichment is optional and deferred until its quality is stable.

The laboratory must not modify the official Baseline workflow. It consumes one `ConceptGhost_Baseline_CompletionBundle.zip`, performs controlled multiview completion/reconstruction, validates against the original camera, and produces Maya-compatible geometry.

## Core path

Baseline Bundle
→ temporary panoramic working context
→ automatic scene-relative camera paths
→ geometry control frames + disocclusion masks
→ masked WAN completion
→ source-preserving composite
→ SphereSfM
→ COLMAP dense reconstruction
→ Baseline registration/fusion
→ local cleanup
→ texture recovery
→ original-view regression
→ Maya export

## Not the final product

Gaussian Splatting / Brush are not required deliverables. 3DGS may later be used as an optional preview only.

## Hardware target

RTX 2080 Ti, 11 GB VRAM. Use quantized WAN, sequential workers, one path at a time, explicit unload and disk checkpoints.

## Repository rule

This directory is experimental and must remain disconnected from the official workflow until promotion gates pass.
