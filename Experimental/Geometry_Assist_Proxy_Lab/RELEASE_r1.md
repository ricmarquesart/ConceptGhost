# Geometry Assist Diagnostic Isolated r1

Status: packaged; static CI PASS; RTX 2080 Ti hardware inference acceptance pending.

## Package

`ConceptGhost_Geometry_Assist_Diagnostic_Isolated_r1.zip`

SHA-256:
`a30232d6a9dc29f4c4714d3a04c26d8f9e52cb4cad0d2a72b224540ba94f7165`

Google Drive Evaluation_Builds:
- file ID: `1v920EioJzLi-EvAkGWBV976GH3gr2Dxn`

GitHub Actions:
- workflow: `Geometry Assist Isolated Package`
- run: `35927043338`
- conclusion: SUCCESS
- artifact ID: `10779203959`

## Isolation

Writes only to:
`%LOCALAPPDATA%\ConceptGhost-GeometryAssistDiagnostic`

Does not pip-install into ComfyUI, does not use shared ComfyUI model folders, does not alter MoGe, Lotus, P9 or P10.

## User test

1. Extract ZIP.
2. Run `01_INSTALL_GEOMETRY_ASSIST_DIAGNOSTIC.bat`.
3. Run `02_VERIFY_GEOMETRY_ASSIST_DIAGNOSTIC.bat`.
4. Drag a concept PNG/JPG onto `03_RUN_GEOMETRY_ASSIST_DIAGNOSTIC.bat`.
5. Inspect `02_geometry_assist_proxy.png` and the side-by-side/difference diagnostics.
6. Run MoGe/P9 once on the original and once on the proxy for manual A/B.

The installer downloads the private runtime/model data during installation; large model weights are intentionally not embedded in the small distribution ZIP.
