# ConceptGhost v0.30 — GATE 4–6 High Fidelity Reference Proof

Reference run: `20260918T195826_428213Z_67686e0e`

The real v0.29.1 ViT-G RAW evidence was reused offline to exercise the corrected v0.30 canonicalization and mesher.

## BEFORE (actual v0.29.1 artifact)
- RAW profile: High Fidelity
- RAW model: Ruicheng/moge-3-vitg
- RAW resolution: 9
- PrimaryMesh profile: Standard
- mesher: standard_transport_stride
- stride: 3
- depth_edge_rtol: null
- vertices: 159,368
- faces: 316,244

## AFTER (v0.30 code, same RAW)
- Canonical profile: High Fidelity
- PrimaryMesh profile: High Fidelity
- model: Ruicheng/moge-3-vitg
- resolution: 9
- SSR: 7 (authoritative contract)
- mesher: moge_full_resolution_depth_edge_preserving
- stride: 1
- depth_edge_rtol: 0.04
- RAW valid points: 1,433,610
- retained mesh vertices: 1,426,735
- candidate faces: 3,139,990
- final faces: 2,823,599
- rejected invalid faces: 280,372
- rejected depth-edge faces: 36,019
- degenerate rejected faces: 0
- forbidden-depth-edge triangles accepted: 0
- normal gate: PASS
- camera-away faces: 0
- normal-opposed faces: 0

This proves the RAW → Canonical → PrimaryMesh correction on the exact failing real-world evidence.

MAYA_LIVE, MAYA_REOPEN and FBX_ROUNDTRIP are not claimed as v0.30 PASS yet because they require a Windows Maya execution of the new build.
