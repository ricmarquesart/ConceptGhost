# ConceptGhost v0.41.3 — Maya camera-signature runtime hotfix

The v0.41.2 Refined run reached PLY, USD, DCC transport mesh and the Maya worker, then correctly surfaced the worker root error:

`name 'math' is not defined`

The Maya worker computes the live horizontal FOV from Maya focal length and horizontal film aperture during Canonical FOV ↔ Maya FOV parity validation. The worker module used `math.degrees` / `math.atan` without importing Python `math`.

v0.41.3 adds the explicit `import math` and a dedicated camera-signature regression.

Unchanged:
- FOV Authority
- solver outputs
- P9.9 fusion math
- Semantic/P9.10
- P9.13
- branch behavior/layout from v0.41.2
- new solvers: 0

Packaged ZIP SHA-256:
`6a28b3089081f0a107ea1b55dd6dadf132b6ac0f0d03e5efb8672facbcd1166a`

Windows/ComfyUI/Maya acceptance remains pending.
