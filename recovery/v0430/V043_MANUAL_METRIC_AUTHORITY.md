# ConceptGhost v0.43.0 — Manual Metric Authority

Architecture:
- P9 = Baseline.
- Refined = P9 + future P10.
- In v0.43 P10 is not implemented, so Baseline and Refined remain identical P9 paths.
- Manual Metric Scale is shared P9 authority and therefore identical in both modes.
- No new solver.

Artist workflow:
- Manual Metric Scale default OFF.
- ON: draw one line over the reference image, choose Vertical Height or Free 3D Distance, enter known physical distance/unit.
- Endpoint positions are robustly estimated from 7x7 patches over canonical geometry.
- Valid manual authority = ARTIST_MANUAL_KNOWN_DISTANCE.
- Global scale factor is uniform and immutable for P10.

Scale semantics:
- scales canonical XYZ, canonical camera depth and camera translation/position together;
- preserves FOV, camera rotation, normals, UVs, topology and image-space coordinates;
- Vertical Height uses WORLD_UP projection;
- Free 3D Distance uses Euclidean 3D distance;
- invalid active manual measurement fails closed.

Audit/output:
- diagnostics/manual_metric_scale.json
- diagnostics/manual_metric_scale_overlay.png
- RUN_PARAMETERS.txt includes line, known value, measured before, factor, measured after, authority, warnings and P10 immutability.

Maya contract:
- creates CG_MANUAL_SCALE_REFERENCE, CG_SCALE_POINT_A, CG_SCALE_POINT_B and CG_MANUAL_SCALE_DISTANCE in diagnostics;
- validates live Maya scene and saved/reopened .ma;
- active manual metric must match requested meters within tolerance or export fails closed.

Static/synthetic evidence:
- 4 reconstructed units -> requested 2.0 m => scale 0.5 PASS.
- FOV invariant PASS.
- camera rotation invariant PASS.
- reprojection invariant PASS.
- geometry ratio invariant PASS.
- invalid endpoint fail-closed PASS.
- Maya helper/roundtrip contract PASS with fake cmds.
- workflow: 77 nodes / 146 links / 17 groups; Baseline/Refined identical before future P10.

Real Windows + ComfyUI + Maya runtime acceptance remains pending.
