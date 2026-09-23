# Geometry Assist Proxy Diagnostic Lab — Isolated Test Plan

## Purpose
Create a completely isolated experiment that converts a painted / hand-painted concept into a conservative **Geometry Assist Proxy** image for downstream MoGe A/B testing.

The proxy is NOT authoritative artwork and is NOT part of the official ConceptGhost pipeline. Its only purpose is to make scene structure, occlusion boundaries, planes, materials and lighting more physically legible while preserving the original camera/composition as closely as possible.

## Isolation contract
Runtime root:
`%LOCALAPPDATA%\ConceptGhost-GeometryAssistDiagnostic`

The lab must NOT:
- pip-install into the active ComfyUI Python;
- modify the official ConceptGhost workflow;
- modify `%LOCALAPPDATA%\ConceptGhost-MoGeRuntime-v1`;
- modify Lotus Diagnostic;
- write models into shared ComfyUI model folders;
- alter P9/P10 outputs.

First implementation is standalone. No host ComfyUI custom node is required for r1. This is intentionally stricter isolation than the normal workflow.

## Core stack

### 1. ControlNet Aux
Use the Hugging Face `controlnet-aux` package only inside the private runtime.

Initial preprocessor:
- Canny, because it is deterministic, lightweight, does not require an additional learned annotator checkpoint, and preserves hard scene boundaries.

Future A/B preprocessors:
- HED / SoftEdge
- Realistic Lineart
- MLSD for architecture-heavy concepts

### 2. ControlNet
Initial checkpoint:
`diffusers/controlnet-canny-sdxl-1.0-small`

Reason:
- SDXL-compatible;
- much smaller than the full SDXL Canny ControlNet;
- appropriate for RTX 2080 Ti 11 GB testing;
- structural control remains the main guard against composition drift.

### 3. IP-Adapter
Initial official baseline:
`h94/IP-Adapter`
SDXL weight:
`ip-adapter_sdxl.bin`

Purpose:
- keep the generated proxy visually/compositionally tied to the source image.

Optional second A/B adapter after baseline works:
`ostris/ip-composition-adapter`
`ip_plus_composition_sdxl.safetensors`

This adapter is specifically intended to preserve general composition while reducing dependence on source style/content, which may be valuable for turning painterly concepts into geometry-readable proxies.

### Base diffusion model
`stabilityai/stable-diffusion-xl-base-1.0`

Use FP16, model CPU offload, VAE tiling/slicing where supported, and one image at a time.

## Hardware target
Primary target:
- NVIDIA RTX 2080 Ti
- 11 GB VRAM

Execution policy:
- float16;
- model CPU offload;
- sequential/single-image execution;
- initial max working dimension 1024;
- preserve source aspect ratio;
- no batch > 1;
- deterministic seed by default.

## Default conservative profile
Name:
`GEOMETRY_ASSIST_CONSERVATIVE`

Suggested first defaults:
- strength / denoise: 0.20–0.28, initial 0.24;
- ControlNet scale: 0.90–1.00, initial 0.95;
- IP-Adapter scale: 0.70–0.90, initial 0.80;
- CFG: 3.5–5.0, initial 4.0;
- steps: 20–30, initial 24;
- seed: fixed and recorded.

These are test defaults, not final production values.

## Default prompt
```text
Create a geometry-assist proxy of the exact same scene.
Preserve the exact camera, perspective, composition, silhouettes, object layout,
architectural proportions, positions, scale relationships, openings, doors,
windows, stairs, roofs, street elements and major surface boundaries.
Do not redesign the scene.
Do not add, remove, move or duplicate objects.
Reduce painterly ambiguity.
Make materials, lighting, cast shadows, occlusion boundaries, planar surfaces
and foreground/midground/background separation physically legible and realistic.
Use neutral plausible lighting and realistic material response only where it
helps clarify the existing structure.
Preserve every major edge and structural relationship from the input.
Avoid inventing unseen details.
```

Default negative prompt:
```text
changed camera, changed perspective, changed framing, crop, fisheye,
altered architecture, extra windows, extra doors, added objects, removed objects,
moved objects, duplicated objects, changed proportions, warped geometry,
dramatic lighting, fantasy lighting, heavy stylization, painterly effect,
blurred edges, melted structure, simplified scene, invented structures,
hallucinated background, text, watermark
```

## Execution flow
```text
SOURCE CONCEPT
   |
   +--> ControlNet Aux / Canny
   |        |
   |        +--> structural hint
   |
   +--> IP-Adapter reference
   |
   +--> SDXL img2img initial image
            |
            +--> ControlNet structural constraint
            +--> IP-Adapter image reference
            +--> conservative prompt
                     |
                     v
             GEOMETRY ASSIST PROXY
```

## Outputs
Every run writes to:
`%LOCALAPPDATA%\ConceptGhost-GeometryAssistDiagnostic\Outputs\<run_id>\`

Required outputs:
- `00_original.png`
- `01_control_hint_canny.png`
- `02_geometry_assist_proxy.png`
- `03_side_by_side.png`
- `04_difference_overlay.png`
- `manifest.json`
- `run.log`

Optional:
- JPEG copy of proxy for quick viewing;
- multiple conservative seeds only when explicitly requested;
- edge-alignment diagnostic.

The PNG is the authoritative diagnostic image. JPG is convenience only.

## A/B purpose
The proxy is never automatically sent into P9.

Manual test procedure:
1. Run MoGe/P9 on ORIGINAL.
2. Run isolated Geometry Assist Lab on the same original image.
3. Run MoGe/P9 separately on the PROXY.
4. Compare MoGe depth diagnostics and PrimaryMesh visually.
5. Only if proxy repeatedly improves geometry without source drift should any official integration be discussed.

## Visual acceptance criteria
A proxy is useful only when:
- camera/framing is effectively unchanged;
- silhouettes remain aligned;
- architectural objects remain in the same locations;
- no new window/door/object appears;
- no object disappears;
- foreground/midground/background become easier to read;
- planes and occlusion boundaries become clearer;
- lighting is more physically legible but does not reinterpret geometry.

Reject the proxy when:
- major edges move;
- structure is redesigned;
- objects are invented;
- scene scale relationships change;
- perspective changes;
- source-specific architectural details are replaced.

## Diagnostic metrics
The first decision is visual, but the isolated lab should also calculate simple safety metrics:
- source/proxy SSIM where available;
- edge overlap / edge displacement;
- mean absolute pixel difference;
- output dimensions;
- runtime;
- peak CUDA allocation if available;
- exact seed/prompt/scales.

Metrics are drift warnings, not proof of geometric correctness.

## Installation design
Installer:
`01_INSTALL_GEOMETRY_ASSIST_DIAGNOSTIC.bat`

Private runtime contents:
```text
%LOCALAPPDATA%\ConceptGhost-GeometryAssistDiagnostic\
  Python\
  Models\
    sdxl_base\
    controlnet_canny_sdxl_small\
    ip_adapter\
  Cache\
  Temp\
  Worker\
  Outputs\
  Logs\
  Manifests\
```

Private Python:
- CPython 3.11 x64;
- private pip;
- CUDA PyTorch wheel compatible with the test stack;
- diffusers;
- transformers;
- accelerate;
- safetensors;
- huggingface_hub;
- controlnet-aux;
- opencv-python-headless;
- Pillow;
- NumPy.

All environment/cache variables are process-local and redirected into the runtime root.

## Model download policy
The installer or preparation step downloads only into the private `Models` / `Cache` roots.

No shared model directory is used.

Before production-quality packaging:
- freeze exact model revisions;
- record file hashes where practical;
- use resumable downloads;
- avoid Windows symlink requirements, following lessons from the Lotus Diagnostic installer.

## Disk budget
Use a conservative preflight requirement of 25 GB free for r1.

Reason:
- SDXL base;
- SDXL ControlNet;
- IP-Adapter + CLIP image encoder;
- Torch/Python packages;
- temporary download/cache overhead.

Exact steady-state size is recorded after the first verified installation.

## Commands
Planned entry points:
1. `01_INSTALL_GEOMETRY_ASSIST_DIAGNOSTIC.bat`
2. `02_VERIFY_GEOMETRY_ASSIST_DIAGNOSTIC.bat`
3. `03_RUN_GEOMETRY_ASSIST_DIAGNOSTIC.bat <image>`
4. `04_UNINSTALL_GEOMETRY_ASSIST_DIAGNOSTIC.bat`

Run command may also prompt for the input path when no drag-and-drop argument is supplied.

## Verification
Verification must prove:
- private Python exists;
- Torch imports only from private runtime;
- CUDA is visible;
- diffusers imports;
- ControlNet Aux imports;
- IP-Adapter loader support exists;
- no host ComfyUI Python mutation;
- no shared-model mutation;
- no MoGe/Lotus runtime mutation.

A tiny offline smoke test should validate preprocessing without downloading/generating a full SDXL result.

## Failure policy
A failure:
- stops only the isolated experiment;
- preserves run log and partial manifest;
- never mutates official ConceptGhost geometry;
- never falls back to installing packages into host ComfyUI.

## Phase plan

### GAP-1 — Isolation scaffold
Runtime root, private Python, cache/temp/log/output contracts.

### GAP-2 — Dependency lock
Pin tested Torch/Diffusers/Transformers/ControlNet-Aux stack for Windows + RTX 2080 Ti.

### GAP-3 — Model materialization
SDXL base + small Canny ControlNet + IP-Adapter in private storage.

### GAP-4 — Preprocessor proof
Generate deterministic Canny structural hint PNG from source.

### GAP-5 — Conservative proxy worker
SDXL img2img + ControlNet + IP-Adapter.

### GAP-6 — Low-VRAM hardening
CPU offload, slicing/tiling, sequential loading, memory diagnostics.

### GAP-7 — Output bundle
Original, hint, proxy, side-by-side, difference, manifest, log.

### GAP-8 — Safety metrics
SSIM/edge alignment/drift warnings.

### GAP-9 — Prompt/profile tuning
Tune conservative defaults on painted architecture / environment concepts.

### GAP-10 — Optional Composition IP-Adapter A/B
Compare standard IP-Adapter with composition-focused adapter.

### GAP-11 — User A/B with MoGe
Original→MoGe versus Proxy→MoGe on the same source image.

### GAP-12 — Decision
Only after user evidence decide whether a future optional official Geometry Assist branch is worth designing.

## Official pipeline impact
NONE.

This lab does not update P9/P10 gates and does not become an official dependency.
Any future integration requires a separate explicit roadmap decision after A/B validation.
