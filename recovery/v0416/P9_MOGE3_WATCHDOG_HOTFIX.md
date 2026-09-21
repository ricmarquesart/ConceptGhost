# ConceptGhost v0.41.6 — MoGe-3 Independent Probe Watchdog

Observed real runtime behavior: the Refined workflow remained on the independent MoGe-3 focal probe for about 35 minutes with no observable stage progress before manual cancellation.

The old implementation used blocking `subprocess.run(..., timeout=3600)`, captured stdout only at process exit, and did not guarantee child-process termination when the ComfyUI prompt was cancelled.

v0.41.6 changes only worker supervision:

- atomic status/heartbeat file every 15 seconds;
- visible worker stages: CONFIGURE_RUNTIME, IMPORT_RUNTIME, MODEL_LOAD_START/DONE, IMAGE_PREPARED, INFERENCE_START/DONE, SERIALIZE_START, DONE;
- stale heartbeat after 180 seconds is an actionable failure;
- hard timeout: 25 minutes High Fidelity / High Fidelity Split Clean, 15 minutes Low Resolution;
- ComfyUI cancellation terminates the isolated worker process tree;
- failed jobs remain on disk for diagnosis;
- existing private MoGe runtime can receive the worker-only refresh without reinstalling model weights.

MoGe model selection, refine steps, resolution, FOV math, solver output and P9 scoring are unchanged. New solvers: **0**.

Packaged ZIP SHA-256: `4dd1676fe566b459efd972db92c9e6292023cc0826773d05c5d9d26ef84fda7b`.
