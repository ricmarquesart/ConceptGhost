# CG-02 / CG-03 Panorama v0.9 — Source Lock + Top-Down Presets

## Release
- Bundle: `ConceptGhost_P9_PLUS_CG02_CG03_TEST_v0.9.zip`
- Drive file id: `1iZvMPXVme1vThIGB5ovVZjp2fXe-mLUg`
- SHA-256: `269dd799a8e159f1d831add0627663d85e09a7db747dfc777ad8a32165a6f764`

## PRESET 04 — SOURCE LOCK / MAX PRESERVE
Use when the ERP reprojected to the accepted P9 camera loses source sharpness, detail, perspective, composition, or art style.

Editable nodes: **41, 42, 44, 45, 74, 77**.

Key policy:
- invent only unseen regions;
- observed P9 region is treated as locked visual authority;
- explicitly suppress blur, repainting, relighting, perspective drift and photorealistic drift;
- default final tiled-refine denoise: **0.08**.

## PRESET 05 — TOP-DOWN / BIRD'S-EYE
Use when the accepted P9 camera points predominantly downward and the source has little or no visible horizon.

Editable nodes: **41, 42, 44, 45, 74, 77**.

Key policy:
- preserve the accepted downward-facing / bird's-eye orientation;
- continue the environment outward from the observed region;
- do **not** require or invent a conventional eye-level horizon;
- do not convert the source to a street-level/front-facing composition;
- default final tiled-refine denoise: **0.10**.

## Authority rule
P9 remains authoritative for the source image, accepted camera/FOV and known geometry.
CG-02 extends the unknown 360 world and does not replace the known P9 observation.
CG-03 remains fail-closed when source-camera reprojection or ERP seam continuity fails.
