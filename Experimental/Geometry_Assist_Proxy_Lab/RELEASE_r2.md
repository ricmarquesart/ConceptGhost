# Geometry Assist Diagnostic Isolated r2

Status: runtime hotfix packaged; static CI PASS; RTX 2080 Ti re-test pending.

## Root cause fixed

The first hardware run successfully installed and loaded the private Python/Torch/CUDA stack, SDXL, ControlNet and IP-Adapter, then failed at the first ControlNet denoising step.

Root cause:
- img2img working canvas = 1024x768;
- ControlNet Aux Canny default preprocessing resized the control hint to 704x512;
- Diffusers therefore produced latent/control feature maps with incompatible widths (128 vs 88).

r2 fixes this by:
- 64-pixel-aligned working canvas;
- ControlNet Aux called with the exact working-resolution contract;
- final hard size-alignment guard before inference;
- explicit SDXL pipeline height/width;
- short positive/negative prompts kept within CLIP 77-token context;
- explicit prompt-token contract to prevent future silent truncation;
- Python cache files excluded from the package.

The MediaPipe/timm/Flash-Attention warnings observed in r1 are non-fatal for the Canny-only diagnostic path.

## Package

`ConceptGhost_Geometry_Assist_Diagnostic_Isolated_r2.zip`

SHA-256:
`c8136e052b6197fa8cd19254c05949079acbd8c5f8394d97b6597af44d82c2a8`

Google Drive Evaluation_Builds:
- file ID: `1FqL2LxID2cPhDqLy8shBY48fhYhygjYz`

GitHub Actions:
- final packaging run: `35930843468`
- conclusion: SUCCESS
- artifact ID: `10780358333`

## Upgrade from r1

Do **not** uninstall the r1 runtime.

1. Extract r2.
2. Run `01_INSTALL_GEOMETRY_ASSIST_DIAGNOSTIC.bat`.
3. The installer reuses the isolated runtime/models and refreshes the owned config/worker.
4. Run `02_VERIFY_GEOMETRY_ASSIST_DIAGNOSTIC.bat`.
5. Re-run the same source through `03_RUN_GEOMETRY_ASSIST_DIAGNOSTIC.bat`.

Official ConceptGhost/MoGe/Lotus/ComfyUI environments remain untouched.
