# ConceptGhost v0.19.1 FINAL

Runtime hotfix of v0.19 FINAL based on a real Windows/Maya output bundle.

- Fixes Hero Mesh creation in Maya Python API 2.0 by passing `parent=parent_obj` explicitly to `MFnMesh.create`.
- Real run confirmed the selected MoGe point cloud and PrimaryMesh have 1,429,278 points/vertices; a 50,000-point comparison matches within <1e-6 float serialization tolerance.
- Both real-run FBX files contained `CG_MATCHED_CAMERA1` and `CG_ARTIST_CAMERA`, and mayapy round-trip camera validation passed.
- Fresh package extraction: 118 manifest files / 0 divergences, 134 tests passed, compileall PASS, Semantic worker self-test PASS.
- Full binary archive is stored in Google Drive and pinned here by SHA-256.
