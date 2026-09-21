# ConceptGhost v0.43.1 — Maya Metric Unit Hotfix

Runtime finding:
- Manual Metric Authority correctly computed the canonical scene in meters.
- Maya was authored in its standard centimeter unit without a meters-to-centimeters boundary conversion.
- Therefore a requested 3.0 m reference became a 3.0 Maya-unit span, i.e. 3 cm.
- The previous Maya validation repeated the same unit mistake and could falsely PASS because it compared raw Maya centimeters numerically against expected meters.

Hotfix contract:
- Canonical ConceptGhost geometry, camera translation, depth and Manual Metric Scale remain in meters.
- Maya scene unit is explicitly centimeters.
- Every spatial value crossing the Maya authoring boundary is converted with 1 m = 100 cm.
- Conversion applies uniformly to PrimaryMesh vertices, matched/artist camera translation, Manual Metric diagnostic locators/lines/distance helpers and metric ground helpers.
- FOV, rotation, normals, UVs, topology, image coordinates and canonical files remain unchanged.
- Maya validation converts measured Maya centimeters back to meters before comparing with known_distance_m.
- 3.0 m must measure as 300 cm in Maya.
- A 3 cm span must no longer be accepted as 3.0 m.
- Maya metadata records mayaLinearUnit=cm, canonicalLinearUnit=meters and mayaUnitsPerMeter=100.0.

Regression acceptance:
- 3.0 m -> 300.0 Maya cm PASS.
- 300.0 Maya cm -> 3.0 canonical m PASS.
- 3.0 Maya cm -> 0.03 m and must FAIL a 3.0 m authority check.
- Camera and geometry receive the same x100 authoring conversion, preserving reprojection/framing.
- Manual Metric global scale math itself is unchanged.
