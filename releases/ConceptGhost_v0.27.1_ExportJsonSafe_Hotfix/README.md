# ConceptGhost v0.27.1 — Export json_safe hotfix

Fixes the runtime failure in `ConceptGhostExportBundle` while writing canonical USDA metadata:

```
NameError: name 'json_safe' is not defined
```

Root cause: `conceptghost_io.write_usda_points()` called the shared `json_safe()` serializer but did not import it from `conceptghost_contracts.py`.

The hotfix:
- imports `json_safe` with package and direct-module compatibility;
- adds a regression test that writes USDA metadata containing NumPy scalar/array values;
- leaves the already-PASS MoGe-3 private runtime untouched;
- leaves MoGe-2, Single View, Multi View/Trellis, ComfyUI Python, Torch and CUDA untouched.

Local validation: 14/14 pytest PASS plus Python compile gate PASS.

For an existing v0.27 install, run only `INSTALL_V0271_EXPORT_HOTFIX.bat`, then `VERIFY_V0271_EXPORT_HOTFIX.bat`, then fully restart ComfyUI Desktop.
