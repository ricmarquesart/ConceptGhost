# ConceptGhost v0.29 — MoGe-3 High Fidelity

Current complete user bundle with a single installer.

## User-facing defaults

- geometry_engine = MoGe
- moge_version = MoGe-3
- geometry_profile = Standard
- profiles: Standard / High Fidelity only

## High Fidelity

- official MoGe-3 ViT-G checkpoint: Ruicheng/moge-3-vitg
- resolution_level = 9
- refine_steps = 7
- mixed precision enabled
- full-resolution depth-edge-preserving surface mesher
- depth-edge rtol = 0.04
- no silent ViT-L fallback on CUDA OOM
- final topology remains authoritative through Maya/FBX

## Standard

- Ruicheng/moge-3-vitl
- v0.28-compatible transport behavior
- Max Reference uses resolution_level 9 / refine_steps 3

## Complete installer

The COMPLETE bundle exposes only:
- INSTALL_CONCEPTGHOST.bat
- VERIFY_CONCEPTGHOST.bat
- VERIFY_HIGH_FIDELITY_VITG.bat

INSTALL_CONCEPTGHOST.bat installs the current ComfyUI payload and repairs/creates the isolated runtime at %LOCALAPPDATA%\ConceptGhost-MoGeRuntime-v1. It uses private Python 3.11.9 and downloads/caches both ViT-L and ViT-G. It does not modify the shared ComfyUI Python/Torch/CUDA environment.

## Validation

Before packaging:
- 25/25 tests PASS
- compileall PASS
- workflow 34 nodes / 90 links / no dangling links
- Standard reference regression: 158,724 vertices / 313,524 faces / stride 3
- High Fidelity dry-run on the same user MoGe-3 evidence: 1,416,071 retained vertices / 2,806,047 faces / 12,220 depth-edge vertices cut / stride 1
- normal gate PASS / 0 camera-away / 0 opposed

## Complete bundle

Google Drive folder:
https://drive.google.com/drive/folders/1edRBgxDKoZD0VMr1KLwXHXirOZS_XZDp

Complete ZIP:
https://drive.google.com/file/d/1pcN23UkiljOt2sT6PmKHSOYYuS153zhK/view?usp=drivesdk

Source snapshot:
https://drive.google.com/file/d/14sB3KXdCVth3KxqeaffFAkzrfNtmY5Xc/view?usp=drivesdk

SHA256 COMPLETE:
aec98e15c1915397925d431d23b4e1eddac4fff69432fd9ce2873313225a03ed

SHA256 SOURCE:
f68e6b658818c9d843152e94678bd83db3d579b0590a8a8fe17609cea32970a1
