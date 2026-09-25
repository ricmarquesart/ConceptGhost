# ConceptGhost Gate 7 R6F15 — COLMAP Auto-Discovery Fix

Date: 2026-09-25

## Target-PC failure

The R6F14 target-PC run reached node 2400 (ConceptGhostP10Gate7Runtime) and
failed in Gate 7.3 while launching the Delaunay visibility mesher. Windows
raised FileNotFoundError / WinError 2 from subprocess creation.

This is not a P9, MoGe, WAN, Gate 6 geometry, or COLMAP installation failure.
The same attempt had already completed the expensive upstream stages.

## Root cause

The Gate 7 UI normalized an empty COLMAP field to the literal token "colmap".
The Gate 7 dense-evidence repair path had a resolver that could reuse the exact
COLMAP executable stored by Gate 6, but the Delaunay call bypassed that resolver
and forwarded the bare token directly to prefusion_mesh.py.

On the target Windows machine COLMAP is installed under ConceptGhost's private
ThirdParty runtime and is not required to be globally available on PATH.
prefusion_mesh.py therefore reached subprocess.run("colmap", ...) and Windows
correctly returned WinError 2.

## R6F15 correction

- Gate 7 now imports and reuses reconstruction_runtime.resolve_colmap_executable.
- The resolver first prefers the exact executable recorded in the Gate 6 dense
  manifest.
- Blank, "colmap", and "colmap.exe" are treated as AUTO and resolve through the
  existing Gate 6 policy: environment override -> ConceptGhost private
  ThirdParty COLMAP 4.2.0 -> PATH.
- The Delaunay branch resolves the executable before native launch.
- The preview node preserves a blank AUTO input instead of coercing it to the
  bare "colmap" token.
- P9 authority, geometry settings, WAN output, Gate 6 output and MoGe runtime
  are unchanged.

## Regression evidence

New test:
Experimental/P10_Lab/tests/test_gate7_colmap_resolution.py

It verifies:
- exact Gate 6 recorded executable reuse;
- ConceptGhost private COLMAP auto-discovery for default "colmap";
- blank UI auto-discovery;
- Delaunay resolution before the native runner.

Cross-platform ConceptGhost Tests:
GitHub Actions run 36178840378 — SUCCESS.

R6F15 hotfix package build:
GitHub Actions run 36178840498 — SUCCESS.

## Target-PC recovery package

Google Drive Evaluation_Builds:
ConceptGhost_R6F15_COLMAP_AUTODISCOVERY_HOTFIX_r2.zip

Drive file ID:
1RZt1syL_0h1Zz84mHL_gnrDmT2f0drsy

Drive package SHA-256:
9cb015fb23c3be7097b5077dee88058331d7e7566fb1a860b6c0e13d4bd1d1a0

The package deliberately does not reinstall ConceptGhost or COLMAP. It applies
the bounded source patch and includes 03_RESUME_LAST_GATE7.bat, which finds the
latest Gate 7 failure manifest and resumes the existing P10 attempt directly.
This avoids creating a new Production attempt and avoids rerunning WAN/Gate 6.

## Target-PC recovery result

The R6F15 in-place recovery was executed successfully on the target PC.

Recovered P10 attempt:
`20260925T182415_329568Z_a99e3910_7d5df9fe`

Recovered P9 run:
`20260925T170319_730339Z_8806dd74`

The resume helper reported:
- Gate 7 runtime status: PASS;
- failed stage recovered: G7_3_DELAUNAY_COMPARISON;
- G7.1 registration manifest: produced;
- G7.2 provenance manifest: produced;
- G7.2c geometry-confidence manifest: produced;
- G7.3 free-space evidence/constraints: produced;
- Delaunay comparison: produced;
- confidence/free-space overlay: produced;
- G7.4 protected fusion candidate PLY + manifest: produced;
- G7.5 visual-review PNG + manifest: produced;
- automatic run-local audit: PASS;
- WAN/Gate 6 reused from the existing attempt;
- no new Production attempt created.

Run-local audit:
`<P9_RUN>/RUN_AUDIT_BUNDLE.zip`

Observed concrete path:
`G:\My Drive\ConceptGhost\Outputs\ConceptGhost\concept_scene_test36\20260925T170319_730339Z_8806dd74\RUN_AUDIT_BUNDLE.zip`

This closes the R6F15 runtime blocker itself.

## Gate state

Gate 7 target-PC **runtime acceptance: PASS**.

Gate 7 remains **OPEN only for artist visual acceptance** of the generated
G7.5 review image / protected-fusion result. No technical rerun of WAN/Gate 6
is required for this acceptance step.

Gate 8 remains blocked from runtime promotion until that visual acceptance is
recorded. Gate 8.1 source/CI work remains valid and unchanged.

Package r1 was renamed OBSOLETE after the resume helper was hardened to add the ComfyUI root to sys.path before importing the custom-node package. Use r2 only.
