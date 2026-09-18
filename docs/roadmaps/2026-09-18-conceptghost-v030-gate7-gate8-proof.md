# ConceptGhost v0.30 — Gate 7 / Gate 8 Proof

Boundary: stop after Gate 8, as requested.

Reference RAW: `20260918T195826_428213Z_67686e0e`

## Gate 7 — topology / normals
The real v0.30 High Fidelity PrimaryMesh reconstructed from the user's ViT-G RAW was validated with the final Gate-8 worker code:

- faces: 2,823,599
- PRE_MAYA: PASS
- camera-away faces: 0
- opposed normals: 0
- zero normals: 0
- median camera dot: 0.404280
- median normal dot: 0.999500

The worker treats `MAYA_LIVE`, `MAYA_REOPEN`, and `FBX_ROUNDTRIP` as mandatory fail-closed gates. Missing/NOT_REQUESTED gate metadata, profile mismatch, model mismatch, wrong stride, missing edge policy, MA failure, or FBX failure cannot be accepted as High Fidelity PASS.

## Gate 8 — profile provenance contract
The Gate-8 contract validates:
- `geometry_profile == selected_profile == effective_profile`;
- embedded `ConceptGhost.GeometryProfile.v1`;
- ViT-G identity, resolution 9 and SSR7;
- `moge_full_resolution_depth_edge_preserving`;
- stride 1;
- `depth_edge_rtol=0.04`;
- `silent_fallback=false`;
- hero mesh profile/policy/stride;
- MA PASS;
- FBX PASS;
- camera-only FBX PASS;
- PRE_MAYA / MAYA_LIVE / MAYA_REOPEN / FBX_ROUNDTRIP all PASS;
- final manifest repeats the same PrimaryMesh + Maya proof and requires run status PASS.

The exact old regression shape — High Fidelity / ViT-G RAW followed by Standard / stride 3 PrimaryMesh — is now explicitly rejected by regression tests.

## Local validation
- compileall: PASS
- v0.30 tests: 20 PASS
- workflow: 26 nodes / 66 links
- dangling links: 0
- active DA3 tokens: 0
- active DepthAnythingV3 tokens: 0
- retired Semantic controls: 0

## Runtime boundary
Autodesk Maya is not available in the Linux build container. Therefore real `MAYA_LIVE`, `MAYA_REOPEN`, and `FBX_ROUNDTRIP` observations are not fabricated. The RC2 bundle contains the required fail-closed worker and verifier for the user's Windows/Maya machine.
