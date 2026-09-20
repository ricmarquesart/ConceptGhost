# P9.13 v0.38.4 static gate

This branch is an independent CI anchor for the canonical Drive checkpoint **ConceptGhost v0.38.4 P9 Confidence-Gated Refinement WIP**.

Rules under test:

- new solver count = 0;
- reuse existing P7 geometric regions and P8 cleanup logic;
- regional evidence comes from existing dense-depth solver confidence, normal confidence and geometric boundary strength;
- HIGH regions may receive severe-face cleanup and conservative planar relaxation;
- MEDIUM regions may receive weaker planar relaxation only;
- LOW regions are conserved;
- sparse strong boundaries remain protected;
- no hole filling, adaptive remeshing, or new faces;
- worsening per-region plane RMS triggers regional rollback;
- reprojection/boundary/finite failures trigger global rollback;
- only a PASS result may become the Export/Maya PrimaryMesh override.

Windows / ComfyUI / Maya runtime proof remains a separate gate.
