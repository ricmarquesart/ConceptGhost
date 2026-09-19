# ConceptGhost v0.33 — P9 Frozen Tool Re-evaluation

No additional heavy AI/3D segmentation runtime is justified before the current v0.33 stack is benchmarked end-to-end.

Keep frozen:
- Metric3D v2
- Point-SAM
- EZ-SP / Superpoint Transformer full stack
- UniDepth V2
- Mask3D
- Mosaic3D
- SAM3D / OpenMask3D / Open3DIS-style 2D-first stacks for Single View

Keep skipped as a full dependency:
- SIHE full software stack; reuse metrology principles only

The current stack already covers MoGe metric evidence, Atlas metrology, MoGe×Atlas agreement, optional Depth Pro, robust consensus, geometric regions and artist-approved local cleanup. Re-open a frozen tool only if the fixed benchmark suite demonstrates a specific measurable gap.
