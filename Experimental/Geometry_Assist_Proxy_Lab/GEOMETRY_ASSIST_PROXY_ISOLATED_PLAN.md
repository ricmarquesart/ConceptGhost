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


---

## r1 implementation / delivery status — 2026-09-23

The isolated test package is now implemented as **r1**.

Canonical evaluation bundle:

`ConceptGhost_Geometry_Assist_Proxy_Diagnostic_Isolated_FULL_r1.zip`

SHA-256:

`f0c9c887008b71d0e9c5c207354f8ae281187eb6d22b236ea4b8c39f0c511ad6`

Google Drive Evaluation_Builds file ID:

`1JqgESxbEU-s2-U2atbfNAKfYPX7WKzTd`

Google Drive parent:

`ConceptGhost/Storage/Evaluation_Builds`

### r1 user entry points

1. `01_INSTALL_GEOMETRY_ASSIST_DIAGNOSTIC.bat`
2. `02_VERIFY_GEOMETRY_ASSIST_DIAGNOSTIC.bat`
3. restart ComfyUI and open `Geometry_Assist_Proxy_Diagnostic.json`
4. optional standalone path: `04_RUN_STANDALONE_GEOMETRY_ASSIST.bat <image> [STRICT|CONSERVATIVE|MODERATE]`
5. uninstall: `03_UNINSTALL_GEOMETRY_ASSIST_DIAGNOSTIC.bat`

### r1 private runtime

`%LOCALAPPDATA%\ConceptGhost-GeometryAssistDiagnostic`

The runtime contains its own:
- Python 3.10.11 embeddable runtime;
- Torch 2.3.1 / CUDA 12.1 wheels;
- Diffusers/Transformers/Accelerate;
- ControlNet Aux;
- SDXL base files;
- small SDXL Canny ControlNet;
- IP-Adapter Plus + private CLIP Vision encoder;
- FP16-safe SDXL VAE;
- worker, cache, TEMP, outputs and manifests.

No models are written into shared ComfyUI folders.

### r1 host-side writes

Only the uniquely owned bridge and standalone workflow:
- `ComfyUI/custom_nodes/ConceptGhost_Geometry_Assist_Diagnostic`
- `ComfyUI/user/default/workflows/Geometry_Assist_Proxy_Diagnostic.json`

No host pip install is used.

### r1 output set

Each run persists:
- original PNG;
- Canny structural hint;
- native proxy PNG;
- original-resolution proxy PNG;
- convenience JPG;
- amplified source/proxy difference;
- source/proxy edge overlap image;
- comparison mosaic;
- diagnostics JSON;
- manifest JSON;
- run log.

### r1 low-VRAM policy

Target remains RTX 2080 Ti 11 GB:
- FP16;
- model CPU offload;
- attention slicing;
- VAE slicing/tiling;
- one image per run;
- 1024 max long edge;
- one automatic retry at 768 after CUDA OOM.

### r1 conservative profiles

- STRICT: strength 0.18 / ControlNet 1.00 / IP-Adapter 0.90.
- CONSERVATIVE default: strength 0.28 / ControlNet 0.90 / IP-Adapter 0.80.
- MODERATE: strength 0.38 / ControlNet 0.80 / IP-Adapter 0.70.

### Verification status

Static package tests: **5/5 PASS**.

Python worker / bridge compile checks: **PASS**.

Full SDXL model download and RTX 2080 Ti generation remain a **runtime acceptance test on the target PC**. This package does not claim GPU acceptance before that user-side run.

### Official pipeline status

Still **NONE / DIAGNOSTIC ONLY**.

r1 does not update P9/P10, does not replace MoGe, and does not automatically route the proxy into geometry generation. The intended A/B remains:

`Original -> MoGe/P9`

versus

`Geometry Assist Proxy -> MoGe/P9`

Only repeated evidence of improvement without structural drift can justify a later optional official branch.


## r1 implementation status — 2026-09-23

The isolated r1 diagnostic package is now implemented and packaged for hardware testing.

Package:
- `ConceptGhost_Geometry_Assist_Diagnostic_Isolated_r1.zip`
- SHA-256: `a30232d6a9dc29f4c4714d3a04c26d8f9e52cb4cad0d2a72b224540ba94f7165`
- Google Drive Evaluation_Builds ID: `1v920EioJzLi-EvAkGWBV976GH3gr2Dxn`
- GitHub Actions packaging run: `35927043338` — SUCCESS.

Implemented stack:
- isolated CPython 3.10.11;
- private Torch 2.3.1 / CUDA 12.1;
- Diffusers SDXL img2img;
- `diffusers/controlnet-canny-sdxl-1.0-small`;
- `controlnet-aux` Canny preprocessing;
- `h94/IP-Adapter` SDXL image conditioning;
- CPU offload + VAE tiling/slicing for the 11 GB target.

No ComfyUI custom node or shared model installation is used in r1. This is deliberate: the first A/B test is a standalone diagnostic with PNG/JPG outputs only.

Static contract + Python compile checks passed in GitHub Actions.
Hardware inference acceptance on the RTX 2080 Ti remains pending and is the next checkpoint.


## r2 runtime hotfix status — 2026-09-23

First RTX 2080 Ti hardware execution result:
- isolated installation PASS;
- private Python/Torch/CUDA PASS;
- SDXL load PASS;
- ControlNet load PASS;
- IP-Adapter load PASS;
- failure occurred only when ControlNet entered the first denoising step.

Root cause:
- img2img canvas was 1024x768;
- ControlNet Aux default Canny preprocessing resized the hint to 704x512;
- Diffusers then produced incompatible latent/control feature widths (128 vs 88).

r2 fixes:
- 64-pixel-aligned working canvas;
- exact ControlNet Aux detect/image resolution contract;
- final exact control-image alignment guard;
- explicit pipeline height/width;
- CLIP-safe concise prompts;
- explicit 77-token prompt contract;
- removal of Python cache files from distribution.

Final r2 package:
- `ConceptGhost_Geometry_Assist_Diagnostic_Isolated_r2.zip`
- SHA-256: `c8136e052b6197fa8cd19254c05949079acbd8c5f8394d97b6597af44d82c2a8`
- Drive Evaluation_Builds ID: `1FqL2LxID2cPhDqLy8shBY48fhYhygjYz`
- GitHub Actions final run: `35930843468` — SUCCESS
- artifact ID: `10780358333`

Upgrade is in-place inside the owned isolated runtime; r1 does not need to be uninstalled.

## r3 runtime hotfix status — 2026-09-23

Second RTX 2080 Ti hardware execution result:
- isolated installer/verification PASS;
- private Torch/CUDA/model self-test PASS;
- Canny structural hint aligned exactly to 1024x768;
- ControlNet load PASS;
- SDXL ControlNet img2img load PASS;
- IP-Adapter load PASS;
- execution stopped before denoising at the explicit CLIP context guard.

Observed token evidence:
- positive prompt: 96 tokens;
- negative prompt: 74 tokens;
- SDXL CLIP maximum: 77 tokens.

Root cause:
- r2 correctly added a fail-closed 77-token runtime guard, but its replacement positive prompt was still too long under the actual SDXL CLIP tokenizer;
- the r2 static regression checked whitespace word count rather than model-token count;
- the installer self-test did not validate the packaged prompts with the real local SDXL tokenizers, so verification could report PASS before this defect was exercised.

r3 fixes:
- much shorter conservative positive and negative default prompts;
- explicit contract marker BOTH_SDXL_CLIP_TOKENIZERS;
- shared prompt-contract validator used by both verification and runtime;
- verification loads the private SDXL tokenizer and tokenizer_2 and fails before PASS if either prompt exceeds the configured context;
- runtime repeats the same validation against pipe.tokenizer and pipe.tokenizer_2 before diffusion;
- static regression now requires the v3 config, both-tokenizer contract, validator markers and a large lexical safety margin.

Validation:
- Geometry Assist Isolated Package run 35931725035: SUCCESS;
- ConceptGhost Tests run 35931725054: SUCCESS;
- P10 DR9 Source Snapshot run 35931725178: SUCCESS;
- implementation/package head: 3722956cbf96f3ef2aa9330f77917806f7759c39;
- GitHub Actions artifact ID: 10781605703.

Canonical r3 evaluation bundle:
- `ConceptGhost_Geometry_Assist_Diagnostic_Isolated_r3.zip`
- SHA-256: `69d15f106600e068f1520004b8d7e61f35ace01da1bf982e910810f7e9c9f149`
- Google Drive Evaluation_Builds file ID: `1rhhLRtSiURFqTrrozqDgc0cO-h7J4_YF`

Upgrade from r2:
- do NOT uninstall the private runtime;
- extract r3 and run `01_INSTALL_GEOMETRY_ASSIST_DIAGNOSTIC.bat`;
- run `02_VERIFY_GEOMETRY_ASSIST_DIAGNOSTIC.bat`;
- verification must now print the prompt-tokenizer contract as PASS;
- then re-run the same input image.

Hardware generation acceptance remains pending until the r3 run reaches and completes diffusion on the target RTX 2080 Ti.
