> **MANDATORY PRIVATE REFERENCE POLICY (2026-09-25)**  
> Before acting on this roadmap/policy document, consult `G:\\My Drive\\ConceptGhost\\Drones\\00_PRIVATE_AUTHOR_REFERENCE_SOURCE_OF_TRUTH_DO_NOT_GITHUB`. The purchased/original reference files remain Google Drive only and must **not** be copied to GitHub or release bundles. Concept Art + accepted P9 camera/source authority remain the product authority. Current gate progression follows the result-first reset in `61_RESULT_FIRST_ROADMAP_RESET_PRIVATE_REFERENCE_POLICY.md`.

# Gates, Test Matrix and Storage

## Software families

Required/planned:
- existing ConceptGhost/ComfyUI environment
- SplatKit components used for control/masks/composite
- quantized WAN path
- panorama/360 LoRA where required by the proven path
- SphereSfM
- COLMAP
- mesh processing/registration utilities
- Maya for final delivery

Not initially required:
- Hunyuan3D
- Gaussian Splat trainer
- Brush

## Storage

Reserve approximately 35–45 GB for the first laboratory, including model weights, environment overhead and working cache. Per-run temporary storage varies with resolution/frame count. Cache cleanup is a required feature.

## Tests

A. foreground occluder hides wall/ground
B. railing hides staircase
C. stretched triangle with no literal hole
D. shell-like object side/back
E. original-view preservation
F. path collision adaptation
G. restart from saved intermediates
H. P9 input containing only the same class of data available from Baseline
I. P9 identity regression: before P10 begins, P9 remains equivalent to Baseline
J. editable Maya delivery

Additional v1.54 contract tests:

K. raw-hole control defaults do not request any missing-region compensation
L. default plan is three initial flights plus one adaptive slot
M. ten-flight configuration uses the same bounded data-driven runner
N. control/mask/WAN/composite previews exist for every executed flight
O. changed or missing preview bytes invalidate checkpoint resume

## Architecture gate

The normal Baseline branch contains no P10.

The Refined Solver Fusion branch is exactly:

`P9 (= Baseline) → P10`

Any new behavior before the P10 boundary is an architecture regression.

The standalone Baseline mesh is never altered to expose holes. A P10-only
evidence derivative is created after the identity boundary.

## Definition of Done

One queue/run from the P9 handoff to validated Maya result, with no manual file handoff between internal P10 stages.
