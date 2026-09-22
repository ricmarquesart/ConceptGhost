# ConceptGhost v1.54 — P10 Checkpoints and Scalable Flights

**Status:** approved implementation direction
**Baseline:** `ConceptGhost_v1.53.0_COMPLETE_INSTALLER.zip`
**Scope:** Refined/P9 clone after its Baseline-equivalent boundary only

## Product invariant

The Baseline branch remains unchanged. The second branch executes the same P9
work first, then enters P10. P10 may invent content only where the reference has
no observation. It must not replace source-observed pixels, the canonical
camera, global scale, or supported P9 geometry.

The final product remains an editable Maya `.ma` scene containing camera,
geometry, and textures. Gaussian Splat and Brush are not release outputs.

## P10 boundary: raw holes

P10 must render an evidence/control mesh that exposes unsupported regions.
This is a P10-only derivative of the P9 result; it is not a change to the
standalone Baseline mesh.

The default control policy is:

- do not fill mesh holes;
- do not bridge unsupported depth discontinuities;
- do not smooth unknown regions into known regions;
- do not extrapolate silhouettes;
- render unknown pixels as black and emit an explicit binary mask;
- keep source-supported pixels locked for later compositing.

## Visible checkpoints

Every flight must publish resumable artifacts and a node-visible preview for
these four stages:

| Stage | Required preview | Meaning |
|---|---|---|
| Control render | control video | Virtual camera view of the raw P9-derived geometry |
| Disocclusion mask | mask video | White/active pixels are missing evidence to be generated |
| WAN completion | generated video | WAN/Matrix-style proposal before source restoration |
| Source composite | composite video | Source/P9 pixels restored over generated unknown regions |

Each checkpoint manifest records stage, flight id, media type, relative path,
digest, validation state, and provenance. A later run may resume only from a
validated checkpoint whose artifacts still match their digests.

## Scalable flight plan

The initial configuration is three automatic flights plus an adaptive budget
of one. The initial three cover a left arc, right arc, and forward/elevated
probe. The adaptive flight is spent only when the remaining-hole analysis says
it can reveal useful missing evidence.

`initial_path_count` and `adaptive_path_budget` are explicit configuration.
The architecture must accept ten or more paths without adding ten hard-coded
copies of a ComfyUI subgraph. Paths are data items consumed by a reusable flight
runner.

Increasing path count is not itself a quality guarantee. Per-path metrics must
include newly exposed mask area, overlap with previous paths, collision result,
reconstruction contribution, and original-view regression. Paths with little
new evidence may be skipped.

## Exploration envelope

P10 is local multiview completion, not unrestricted world generation. Paths
remain inside a scene-relative completion envelope around the canonical camera
and P9 geometry. The envelope can be enlarged deliberately, but adding flights
does not silently expand it to 360 degrees or enter interiors.

## Mickmumpitz/SplatKit mapping

The supplied Dataset Creator workflow contributes the reusable sequence:

1. `SplatKit_CameraPlotRenderControlGeo`
2. control and mask previews
3. `SplatKit_WanI2VMaskedConditioning`
4. WAN video preview
5. `SplatKit_HiResComposite`
6. composite preview
7. SphereSfM/COLMAP dataset assembly

The supplied Krea2 panorama workflow contributes perspective-to-ERP placement,
masked outpaint, source re-composition, seam correction, and panorama preview.
In ConceptGhost the panorama is temporary internal context, not a required user
input or final output.

## Hardware and storage

On the RTX 2080 Ti 11 GB target, flights execute sequentially. WAN is unloaded
before reconstruction. Validated artifacts are written to the stable
ConceptGhost-owned cache so a failure does not require repeating earlier
flights. No P10 dependency may mutate the protected shared ComfyUI Python stack.
