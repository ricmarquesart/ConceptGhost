# ConceptGhost v0.31.2 RC5 installer regression → RC6 fix

## Observed target-machine failure
RC5 installed the ComfyUI payload but then failed in `Scripts/install_moge3_runtime.ps1` because:

`Tools\\MoGeRuntime\\vendor\\MoGe-main.zip`

was not present in the runtime-ready source package.

The failure occurred before Gate 10 runtime acceptance. No Maya/FBX/remesh result was accepted.

## Important side effect
RC5 removed `%LOCALAPPDATA%\\ConceptGhost-MoGeRuntime-v1\\READY.json` before checking for the missing vendor archive. The private runtime contents themselves were not removed.

## RC6 correction
When the vendor archive is absent, RC6 now attempts a fail-closed reuse path:
1. Require the existing ConceptGhost-owned private Python, MoGe repo and worker.
2. Refresh only ConceptGhost-owned worker scripts.
3. Preserve global/ComfyUI Python, Torch, CUDA, NumPy and unrelated runtimes.
4. Require cached-model evidence for both `Ruicheng/moge-3-vitl` and `Ruicheng/moge-3-vitg`.
5. Run the private runtime CUDA/inference verification.
6. Recreate and require `READY.json` status PASS.
7. Only fail for a missing vendor archive when no reusable private runtime exists.

## Local proof
- pytest: **65 PASS**
- RC6 SHA-256: `946d520fd4ca804494d707372e1ef5e0fa2a7a4bdbbf5f76cc87c6425468d511`
