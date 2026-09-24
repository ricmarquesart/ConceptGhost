# ConceptGhost Geometry Assist — ComfyUI Visual Workflow r8

r8 is a repair release for the exact setup failures visible in the r7 screenshots.

## What r8 fixes

### 1. Missing IPAdapter node pack
The red/UNKNOWN nodes were:
- IPAdapterModelLoader
- PrepImageForClipVision
- IPAdapterAdvanced

r8 installs or reuses ComfyUI_IPAdapter_plus. After installation ComfyUI must be restarted (or use the visible "Apply Changes" control in ComfyUI Desktop).

### 2. Missing CLIP Vision model
r7 exposed the isolated file through a subfolder path:
- ConceptGhost/model.safetensors

r8 exposes the same already-downloaded file using the canonical ComfyUI filename directly under models/clip_vision:
- CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors

### 3. Missing ControlNet model
r7 exposed:
- ConceptGhost/diffusion_pytorch_model.fp16.safetensors

r8 exposes the same already-downloaded weight directly under models/controlnet as:
- controlnet-canny-sdxl-1.0-small.safetensors

The r8 workflow also switches to native ComfyUI DiffControlNetLoader because the reused weight is stored in Diffusers format.

### 4. IPAdapter model
r8 exposes:
- ip-adapter_sdxl_vit-h.safetensors

directly under models/ipadapter.

## Disk use
The installer first tries NTFS hardlinks so the large model files are not duplicated. If hardlinks are unavailable it falls back to copying the file.

## Run
1. Close or restart ComfyUI after installing r8.
2. Load ConceptGhost_Geometry_Assist_MoGe_VISUAL_r8.
3. Choose the image in node 01.
4. Run.

Do not use r7 for the next test.
