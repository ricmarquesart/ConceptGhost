# ConceptGhost P10 — Required Software by Result-First Gate

**Status:** AUTHORITATIVE DEPENDENCY MAP  
**Effective:** 2026-09-25

The final target is a refined/polished **Maya blockout/reference world**, not production-ready final geometry/materials. Dependencies that only improve glass/reflections or other final-look behavior are intentionally excluded.

## Excluded by design

- **SAM3 / ComfyUI-RMBG** — not required for the blockout objective. Its useful ADV role is semantic handling of windows/glass/reflections.
- **ComfyUI-GGUF** — not required. The GGUF loader node in the private author's SMPL workflow is disconnected.
- **RAFT weights** — not required in the default ConceptGhost path. SplatKit HiRes Composite is standardized to `base_mode=geometry`; RAFT is loaded only when the base mode is not geometry.
- **ADV workflow** — reference-only. The required default implementation uses the 360 panorama workflow plus the SMPL dataset workflow.

## R0 — Reference parity + frozen acceptance scene

Required:
- current ConceptGhost COMPLETE bundle;
- current ComfyUI Desktop;
- Maya.

No new author-pipeline model is required specifically by R0.

## R1 — Persistent official output tree

Required:
- current ConceptGhost runtime.

Official gate outputs must be created in their final attempt/gate folders during execution. A post-run backfill BAT is recovery-only.

## R2 — Camera rails / coverage

Required:
- ComfyUI-SplatKit;
- SplatKit MoGe ViT-L checkpoint;
- ComfyUI-Mickmumpitz-Nodes.

## R2-PANO / mandatory 360 source expansion

Required:
- ComfyUI-Krea2-Ostris-Edit;
- ComfyUI-Mickmumpitz-Nodes panorama tools;
- ComfyUI-SplatKit;
- ComfyUI_essentials for the sharpening node used by the author graph;
- ComfyUI_UltimateSDUpscale;
- ComfyUI_preview360panorama;
- Krea 2 Turbo FP8;
- Qwen3-VL 4B FP8;
- Krea2 text→ERP LoRA;
- Krea2 image→ERP outpaint LoRA;
- RealESRGAN x2;
- existing WAN 2.1 VAE.

The generated ERP remains lower authority than the exact concept/P9 source patch.

## R3 — Source-authority generated views / HiRes composite

Required:
- ComfyUI-SplatKit;
- existing WAN 2.1 I2V 14B FP8;
- existing UMT5 XXL FP8;
- existing WAN VAE;
- existing LightX2V rank64;
- WAN CLIP Vision H;
- WAN Panorama LoRA;
- 4x UltraSharp;
- SplatKit MoGe ViT-L.

Default `HiResComposite.base_mode` is `geometry`.

## R4 — Standard extendable multiview dataset

Required:
- SphereSfM / `colmap_sphere.exe` installed by SplatKit;
- the R2/R3 stack above.

## R5 — Explorable-world proof

Required:
- Brush 0.3.0;
- R4 COLMAP-compatible dataset.

Brush trains/views the Gaussian-splat world proof. It does **not** replace Maya.

## R6 — Useful polygonal reconstruction

Required:
- current ConceptGhost reconstruction/COLMAP tools from the COMPLETE bundle;
- validated R4/R5 evidence;
- Maya for direct alignment/coverage inspection.

## R7 — Protected P9 + P10 comparison/fusion

Required:
- current ConceptGhost Gate 7 runtime;
- Maya.

## R8 — Cleanup / regularization

Required:
- current ConceptGhost geometry cleanup tools;
- Maya.

Do not add third-party software merely to hide a failed reconstruction.

## R9 — Texture/provenance/original-view regression

Required:
- current ConceptGhost source/provenance pipeline;
- Maya.

Arnold/final-look rendering is outside the reconstruction dependency requirement.

## R10 — Final Maya blockout + COMPLETE release

Required:
- Maya;
- current ConceptGhost COMPLETE bundle;
- all upstream required dependencies already installed.

## R11 — Adaptive expansion / optimization

Required:
- reuse the same stack as the gate being repeated.

No new dependency is automatically authorized merely for optimization.

## Canonical dependency installer

`ConceptGhost_REQUIRED_PIPELINE_INSTALLER_r2.zip`

Normal operator order:

1. `00_AUDIT_REQUIRED_STACK.bat` — no changes; PC-specific missing/install-space report.
2. `01_INSTALL_REQUIRED_STACK.bat` — installs all and only the required default stack.
3. restart ComfyUI once.
4. `02_VERIFY_REQUIRED_STACK.bat`.

The installer intentionally excludes SAM3/RMBG, GGUF, RAFT and the ADV workflow.
