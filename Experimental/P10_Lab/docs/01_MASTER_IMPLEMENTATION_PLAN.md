# P10-Lab Master Implementation Plan

## Decision

P10 begins from the stable Baseline output while P9 remains under refinement. The design must later accept richer P9 evidence without changing its core contract.

## Non-negotiables

- Baseline remains untouched and is always the fallback.
- Original source pixels and Baseline camera are highest authority where observed.
- Generated content is allowed only in unseen or demonstrably defective regions.
- No manual drone piloting.
- Initial scope is local completion, not full 360 world generation.
- Final product remains editable Maya geometry.
- First target is an RTX 2080 Ti with 11 GB VRAM.

## Ordered implementation

1. Completion Bundle contract and dry-run validator.
2. Baseline adapter.
3. Automatic scene-relative camera-path planner.
4. Control-frame/disocclusion-mask generation.
5. Quantized WAN masked completion.
6. Source-preserving high-resolution composite.
7. SphereSfM reconstruction.
8. COLMAP dense stereo/fusion and mesh.
9. Registration to Baseline coordinates.
10. Known/generated fusion.
11. Local remesh/geometry cleanup.
12. Texture recovery.
13. Original-camera regression.
14. Maya export.
15. Optional targeted extra path.
16. Later P9 enrichment.

## Promotion gates

- Baseline isolation.
- Original-view fidelity.
- Reduced disocclusion holes.
- Healthy completed mesh.
- Identifiable provenance.
- Maya usability.
- 11 GB hardware compliance.
