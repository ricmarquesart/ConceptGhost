# ConceptGhost v1.54 P10 — Phase 1 Implementation Plan

> Execute with strict test-first development. Keep the standalone Baseline
> unchanged and develop only in the isolated v1.54 branch.

**Goal:** establish the executable P10 boundary, scalable flight plan, and
visible/resumable checkpoint contracts before integrating GPU-heavy adapters.

**Architecture:** the v1.53 Refined/P9 clone reaches a Baseline-equivalent
completion bundle. A P10-only raw-hole control policy derives render evidence.
A data-driven flight plan feeds a reusable stage runner. Every major visual
stage emits a validated artifact manifest. WAN, SphereSfM, COLMAP, and Maya are
adapters behind stable contracts so they can use isolated runtimes.

**Tech:** Python standard library for contracts/tests; ComfyUI nodes later;
WAN/Matrix-style generation, SplatKit renderer/compositor, SphereSfM/COLMAP,
and Maya adapters in later gates.

## Task 1: Lock the clarified P10 contracts

**Files:**
- Modify: `Experimental/P10_Lab/p10_lab/pipeline.py`
- Create: `Experimental/P10_Lab/p10_lab/control_policy.py`
- Create: `Experimental/P10_Lab/tests/test_control_policy.py`

1. Write failing tests proving raw-hole defaults never request fill, smoothing,
   silhouette extrapolation, or unknown-region compensation.
2. Run the tests and observe the missing contract failure.
3. Implement the smallest immutable control policy.
4. Run tests and refactor names only while green.

## Task 2: Add scalable initial and adaptive flight configuration

**Files:**
- Modify: `Experimental/P10_Lab/p10_lab/path_planner.py`
- Create: `Experimental/P10_Lab/tests/test_path_planner.py`

1. Write failing tests for default 3 + 1 budget, ten initial paths, stable path
   identifiers, positive scene-relative scale, and invalid negative counts.
2. Implement `FlightPlanConfig` and `FlightPlan` without a hard-coded upper
   path limit.
3. Preserve compatibility of `default_paths()` for the original three routes.
4. Run the focused tests.

## Task 3: Add visible checkpoint manifests

**Files:**
- Modify: `Experimental/P10_Lab/p10_lab/pipeline.py`
- Create: `Experimental/P10_Lab/p10_lab/checkpoints.py`
- Create: `Experimental/P10_Lab/tests/test_checkpoints.py`

1. Write failing tests for the four required preview roles and safe relative
   artifact paths.
2. Implement manifest serialization, SHA-256 validation, and stage/flight
   identity.
3. Prove that changed or missing artifacts invalidate resume.
4. Run focused tests.

## Task 4: Make CI execute the P10 laboratory

**Files:**
- Modify: `.github/workflows/tests.yml`

1. Add compile and unit-test commands for `Experimental/P10_Lab` on Linux and
   Windows without adding external dependencies.
2. Keep existing repository tests intact.
3. Run the same commands locally.

## Task 5: Synchronize documentation and checkpoint the branch

**Files:**
- Modify: `Experimental/P10_Lab/README.md`
- Modify: `Experimental/P10_Lab/docs/01_MASTER_IMPLEMENTATION_PLAN.md`
- Modify: `Experimental/P10_Lab/docs/03_SPLATKIT_MATRIX_ADAPTATION.md`
- Modify: `Experimental/P10_Lab/docs/05_GATES_TESTS_STORAGE.md`

1. Record raw-hole policy, required previews, and scalable flight settings.
2. Run the full local unit suite and compile checks.
3. Review the diff for accidental Baseline changes.
4. Push the isolated branch and use GitHub Actions as the cross-platform gate.

## Deferred gates

- v1.53 CompletionBundle emission from the real Refined/P9 clone
- P10 raw evidence-mesh derivation from confidence/boundary data
- temporary panorama implementation
- SplatKit render and WAN isolated-runtime adapters
- SphereSfM/COLMAP dense reconstruction
- P9 registration, fusion, remesh, texture recovery
- original-camera regression and Maya `.ma` export
- complete v1.54 installer packaging and Drive mirror
