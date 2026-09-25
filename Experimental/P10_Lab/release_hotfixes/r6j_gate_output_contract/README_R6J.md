# ConceptGhost R6J — Gate Output Contract + Gate 6 Functional Proof

R6J makes each Gate prove its deliverable instead of treating a green node as a
successful Gate.

## Run now

1. Run 01_APPLY_GATE_OUTPUT_CONTRACT.bat
2. Run 02_VERIFY_GATE_OUTPUT_CONTRACT.bat
3. Run 03_BACKFILL_LAST_RUN_GATE_OUTPUTS.bat

Step 3 does NOT regenerate WAN, COLMAP, MoGe or geometry. It publishes the
existing latest attempt into an artist-readable output tree beside the P9 run.

## Output location

<P9_RUN>/
  RUN_AUDIT_BUNDLE.zip
  GATE_OUTPUT_INDEX.json
  LATEST_GATE_OUTPUTS.txt
  GATE_OUTPUTS/
    <P10_ATTEMPT_ID>/
      GATE_01_FOUNDATION_RUN/
      GATE_02_P9_TO_P10_HANDOFF/
      GATE_03_KNOWN_UNKNOWN/
      GATE_04_DRONES_CAMERAS/
      GATE_05_NEW_VIEWS/
      GATE_06_RECONSTRUCTION_3D/
      GATE_07_P9_P10_FUSION/

Each Gate folder has:
INPUTS / OUTPUTS / PREVIEWS / LOGS /
GATE_STATUS.json / INPUT_MANIFEST.json / OUTPUT_MANIFEST.json / SHA256SUMS.txt.

Gate 4 publishes every control frame PNG, every hidden-area mask, route/camera
manifests, GIF and quick previews.

Gate 5 publishes every raw WAN PNG and every final source-preserved composite
PNG, plus GIF previews and view_manifest.json.

Gate 6 publishes sparse points, dense points, reconstructed raw P10 mesh
(PLY+OBJ), reconstruction cameras, quality/runtime manifests, logs/previews, and
Gate06_Reconstruction_Diagnostic.ma. Gate 6 is functionally PASS only when the
new reconstruction is non-empty. Poor visual quality may be WARN without hiding
the actual 3D product.

Gate 7 publishes raw P10, fused candidate, provenance/reason evidence,
confidence/free-space evidence, summary preview and Gate07_Fusion_Diagnostic.ma.
That Maya diagnostic references P9 and separates raw P10 / accepted / rejected
P10 layers. Runtime PASS is not functional PASS; zero accepted P10 remains FAIL.

Gate 3 is deliberately strict. If explicit Gate-3 free/conflict outputs do not
exist, its GATE_STATUS.json remains FAIL so the project knows exactly where
evidence is missing instead of silently borrowing later Gate-7 evidence.

No Gate overwrites the preceding Gate product. R6J does not mutate P9 authority,
the existing WAN images, the MoGe runtime, or shared ComfyUI Python packages.
