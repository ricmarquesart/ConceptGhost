# ConceptGhost Geometry Assist Proxy — Isolated Diagnostic Lab

Standalone experimental lab for producing a conservative **Geometry Assist Proxy** from painted / hand-painted concept art.

## Safety / isolation

This package is intentionally **outside the official P9/P10 pipeline**.

It writes only to:

`%LOCALAPPDATA%\ConceptGhost-GeometryAssistDiagnostic`

It does **not**:
- pip-install into ComfyUI;
- write models into ComfyUI model folders;
- modify the MoGe runtime;
- modify the Lotus Diagnostic runtime;
- modify official ConceptGhost workflows;
- replace P9/P10 geometry.

The first test is standalone: drag an image onto `03_RUN_GEOMETRY_ASSIST_DIAGNOSTIC.bat` and inspect PNG/JPG outputs.

## Stack

- SDXL Base 1.0 — conservative img2img engine.
- ControlNet SDXL Canny Small — structural constraint.
- ControlNet Aux — Canny preprocessor (OpenCV fallback only if the package cannot expose its CannyDetector).
- IP-Adapter SDXL — reference-image conditioning to reduce composition drift.

The worker uses Hugging Face Diffusers directly inside a private Python runtime. No ComfyUI custom nodes are required for this isolated test.

## Hardware target

- RTX 2080 Ti 11 GB.
- FP16.
- single image only.
- model CPU offload.
- VAE slicing/tiling.
- default working max dimension: 1024.

## Entry points

1. `01_INSTALL_GEOMETRY_ASSIST_DIAGNOSTIC.bat`
2. `02_VERIFY_GEOMETRY_ASSIST_DIAGNOSTIC.bat`
3. Drag a PNG/JPG onto `03_RUN_GEOMETRY_ASSIST_DIAGNOSTIC.bat`
4. `04_OPEN_GEOMETRY_ASSIST_OUTPUTS.bat`
5. `05_UNINSTALL_GEOMETRY_ASSIST_DIAGNOSTIC.bat`

## Output bundle

Each run writes below:
`%LOCALAPPDATA%\ConceptGhost-GeometryAssistDiagnostic\Outputs\<run_id>\`

Files:
- `00_original.png`
- `01_control_hint_canny.png`
- `02_geometry_assist_proxy.png`
- `02_geometry_assist_proxy.jpg`
- `03_side_by_side.png`
- `04_difference_overlay.png`
- `05_edge_comparison.png`
- `manifest.json`
- `run.log`

The PNG proxy is the authoritative test image. JPG is convenience only.

## A/B test

A — run MoGe/P9 on the original concept.

B — generate the isolated Geometry Assist Proxy, then run MoGe/P9 on that proxy.

Compare the existing MoGe depth diagnostics and PrimaryMesh. The lab itself never connects the proxy to P9 automatically.

## Default prompt

The default prompt is stored in `Config/geometry_assist_config.json` and is intentionally conservative. It requests a physically legible version of the same scene while preserving camera, perspective, silhouettes, layout, proportions, openings and architectural relationships.

## Status

Experimental diagnostic only. No official pipeline impact.


## r2 hotfix — ControlNet canvas alignment + CLIP prompt guard

The first hardware run proved that the isolated install, CUDA stack, SDXL, ControlNet and IP-Adapter all load correctly, but the ControlNet Aux Canny preprocessor returned a 704x512 control image while img2img used a 1024x768 source canvas. Diffusers then failed with a latent/control feature mismatch (128 vs 88).

r2 fixes the root cause by:
- making the working canvas 64-pixel aligned;
- requesting the ControlNet Aux preprocessor at the exact working resolution;
- applying a final exact-size guard before inference;
- passing explicit `height` / `width` to the SDXL ControlNet img2img pipeline;
- shortening the default positive/negative prompts to remain inside CLIP's 77-token context;
- adding an explicit prompt-token contract so future prompt growth fails early instead of being silently truncated.

The other warnings seen in the r1 run (missing optional MediaPipe, timm deprecations, no Flash Attention) are non-fatal for the Canny-only diagnostic path.

Existing r1 installations do **not** need to be uninstalled. Running the r2 installer reuses the isolated Python/models and replaces only the owned worker/config as needed.

Distribution revision: **r2** — first runtime hotfix after RTX 2080 Ti hardware attempt.
