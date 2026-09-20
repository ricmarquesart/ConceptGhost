# P9.10 v0.39.0 static policy

This branch is an independent static regression anchor for the v0.39.0 checkpoint.

- New solvers added: **0**
- Inputs reused: P9.9 fused depth, multi-solver confidence, depth boundaries, Final MoGe normals.
- Boundary/normal discontinuities are protected.
- Low-confidence regions are conserved.
- High-confidence, normal-consistent regions may receive only small local edge-aware refinement.
- Semantic/SAM is not reintroduced in this checkpoint; it remains proof-gated.
- Package SHA-256: `c925bb7a3f7bd4d4cbe14f3c1f16131cd79842aa1f9a15dea00873237afab524`
