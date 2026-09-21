# P10-Lab Master Implementation Plan — P9 (= Baseline) + P10

## Decision

The Refined Solver Fusion architecture is now defined as **P9 + P10**.

P9 is intentionally a functionally identical copy of Baseline. It has no separate refined-solver behavior of its own. P10 is appended immediately after P9 and is the first stage that adds multiview completion, geometry recovery and scene completion.

## Non-negotiables

- The standalone Baseline branch remains untouched.
- P9 must remain functionally equivalent to Baseline before the P10 handoff.
- Original source pixels and the P9/Baseline camera are highest authority where observed.
- Generated content is allowed only in unseen or demonstrably defective regions.
- No manual drone piloting.
- Initial scope is local completion, not full 360 world generation.
- Final product remains editable Maya geometry.
- First target is an RTX 2080 Ti with 11 GB VRAM.

## Ordered implementation

1. P9 Completion Bundle contract and dry-run validator.
2. P9/Baseline-equivalent adapter.
3. Automatic scene-relative camera-path planner.
4. Control-frame/disocclusion-mask generation.
5. Quantized WAN masked completion.
6. Source-preserving high-resolution composite.
7. SphereSfM reconstruction.
8. COLMAP dense stereo/fusion and mesh.
9. Registration to P9/Baseline coordinates.
10. Known/generated fusion.
11. Local remesh/geometry cleanup.
12. Texture recovery.
13. Original-camera regression.
14. Maya export.
15. Optional targeted extra path.
16. Refined-branch integration as P9 (= Baseline) + P10.

## Promotion gates

- Baseline protection.
- P9 identity with Baseline.
- Original-view fidelity.
- Reduced disocclusion holes.
- Healthy completed mesh.
- Identifiable provenance.
- Maya usability.
- 11 GB hardware compliance.

## Official topology

`Baseline` → Baseline output.

`Refined Solver Fusion` → P9 (same behavior/output contract as Baseline) → P10 completion → refined Maya result.

P10 must be developed so that it can be tested using Baseline-equivalent input, but its official integrated upstream stage is P9.
