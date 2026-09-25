# Gate 7 R6F11 — Atlas Depth-Anything Cache Fix

Date: 2026-09-25 UTC  
Status: SOURCE IMPLEMENTED — PACKAGE CI / TARGET-PC ACCEPTANCE PENDING

## Evidence from R6F10

R6F10 fully passed the previously failing MoGe-3 compatibility chain on the RTX 2080 Ti:

- Low Resolution ViT-L CUDA/refiner smoke: PASS;
- High Fidelity ViT-G/Turing compatibility gate: PASS;
- private runtime: Torch 2.6.0 + cu124 + Triton Windows 3.2.0.post21;
- production High Fidelity remains resolution_level=9 / refine_steps=7.

The next installation failure is no longer in MoGe/Triton/FlexGEMM.

The installer reached the legacy/base runtime verification and failed while checking the cached Atlas Depth-Anything model with:

`AutoImageProcessor.from_pretrained(model_id, local_files_only=True)`

for:

`depth-anything/Depth-Anything-V2-Metric-Outdoor-Large-hf`

The earlier online precache step had reported PASS, but the later repository-ID local-only resolver could not reconstruct the image-processor files from cache.

## R6F11 correction

R6F11 makes the Atlas Depth cache contract deterministic.

`precache_atlas_models.py` now uses `huggingface_hub.snapshot_download` with an explicit file set:

- `config.json`;
- `preprocessor_config.json`;
- `model.safetensors`.

The returned resolved snapshot directory is then used directly for both:

- `AutoImageProcessor.from_pretrained(snapshot, local_files_only=True)`;
- `AutoModelForDepthEstimation.from_pretrained(snapshot, local_files_only=True)`.

The snapshot path is recorded in `ATLAS_MODELS_READY.json`.

`verify_runtime.py` no longer asks Transformers to rediscover the model by repo ID in offline mode. It reads the exact cached snapshot path from `ATLAS_MODELS_READY.json`, verifies the three required files, and loads the processor/model from that local directory.

## Why this is bounded

- no shared ComfyUI Python packages are changed;
- no model choice is changed;
- no Atlas or Depth-Anything weights are changed;
- no MoGe runtime change is introduced beyond the already-passing R6F10 compatibility bridge;
- P9 remains immutable;
- Gate 8 remains absent from the validation package.

## Inherited runtime state

R6F11 retains and re-tests the R6F10 MoGe bridge, including the deterministic private compatibility self-test.

Target-PC acceptance remains pending until the full installer reaches PASS.
