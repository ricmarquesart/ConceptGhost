# Supplied Mickmumpitz Workflow Audit

## Files reviewed

- `260825_MICKMUMPITZ_3DGS-Dataset-Creator_1-0_SMPL(1).json`
- `260825_MICKMUMPITZ_Krea2-360Pano-Creator_1-0.json`

## Dataset Creator

The supplied graph contains 77 nodes, 160 links and 17 groups. It implements
four primary camera blocks and one add-to-dataset block. Each flight repeats
the same technical sequence:

1. `SplatKit_CameraPlotRenderControlGeo` emits geometry frames and masks;
2. `CreateVideo`/`SaveVideo` expose the control video;
3. `SplatKit_WanI2VMaskedConditioning` conditions WAN on frames and masks;
4. `KSampler` and `VAEDecode` produce the generated video;
5. `SplatKit_HiResComposite` restores high-resolution source evidence;
6. composite images and camera data feed SphereSfM/COLMAP dataset nodes.

The reviewed graph uses 81 frames at 1440×720 and four sampling steps. Those
values are reference facts, not ConceptGhost release defaults; v1.54 must tune
them against quality, storage and the 11 GB VRAM gate.

## Panorama Creator

The supplied graph contains 76 nodes, 121 links and 10 groups. Its image mode
warps the source photo onto an ERP canvas, masks the missing surroundings,
outpaints with Krea/Ostris/ERP conditioning, restores the original region,
rolls the panorama so the seam is processed centrally, fixes the seam, then
publishes both a 2K intermediate and an upscaled panorama preview.

ConceptGhost adopts the source-locking and seam-handling ideas while keeping
the panorama temporary and internal.

## ConceptGhost departures

- final output is Maya mesh/camera/texture, not Gaussian Splat;
- flight paths are automatic and scene-relative;
- the default is three initial flights plus one adaptive slot;
- flight count is scalable data rather than duplicated graph structure;
- P10 explicitly shows control, mask, generated and composite checkpoints;
- the raw-hole renderer disables compensating geometry before mask creation;
- original-view fidelity has higher authority than plausible generated content.
