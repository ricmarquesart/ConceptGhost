# ConceptGhost Geometry Assist — ComfyUI Visual Workflow r7

This replaces the earlier API-format draft with a real ComfyUI canvas workflow.

## User action after install
1. Restart ComfyUI.
2. Open ConceptGhost_Geometry_Assist_MoGe_VISUAL_r7.
3. Choose the source image in node 01 — CHOOSE IMAGE HERE.
4. Click Queue / Run.

All prompts and settings are intentionally visible inside the workflow.

## Visible groups
- INPUT — choose image, then RUN
- COMPONENT 1 — SDXL / IMG2IMG + PROMPTS
- COMPONENT 2 — CONTROLNET / STRUCTURE
- COMPONENT 3 — IP-ADAPTER / REFERENCE LOCK
- SAMPLING + OUTPUT

Each component contains a Note node explaining what each setting does and why the default was selected.

## Runtime reuse
The installer does not duplicate multi-GB models. It creates Windows directory junctions from the already validated isolated runtime at:
%LOCALAPPDATA%\ConceptGhost-GeometryAssistDiagnostic

ComfyUI sees:
- SDXL Base through native DiffusersLoader
- Canny ControlNet through native ControlNetLoader
- ViT-H IP-Adapter through IPAdapterModelLoader
- ViT-H CLIP Vision through CLIPVisionLoader

## Default geometry-assist intent
The proxy may change texture, material readability, local lighting and contact-shadow cues when useful, but should preserve camera, perspective, composition, silhouettes, positions, proportions, architecture, openings and object layout. It should make distant elements and depth separation easier for MoGe to interpret without adding new scene details.
