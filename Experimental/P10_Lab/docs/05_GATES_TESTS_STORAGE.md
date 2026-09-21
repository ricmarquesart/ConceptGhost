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
H. Baseline-only bundle with no P9 fields  
I. later P9-enriched bundle  
J. editable Maya delivery

## Definition of Done

One queue/run from Baseline bundle to validated Maya result, with no manual file handoff between internal stages.
