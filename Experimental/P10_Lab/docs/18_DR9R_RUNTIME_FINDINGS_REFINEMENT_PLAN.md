# ConceptGhost P10 DR9R — Runtime Acceptance Findings and Refinement Plan

Date: 2026-09-23

## Runtime acceptance state

DR9 is **NOT accepted yet**. The real ComfyUI test exposed workflow/UX issues that are important enough to correct before Gate 7.

## Findings from the first real artist-route session

1. **The TOP/SIDE/FRONT route editor distorted scene proportions.**
   The backend rendered orthographic projections but normalized the horizontal and vertical axes independently to the full panel. One metre on X therefore did not necessarily occupy the same screen distance as one metre on Y. This made the point cloud and routes visually misleading.

2. **The second three-panel image inside node 07R was not a second route authority.**
   It was the normal ComfyUI image-output preview from the previous server execution. The custom interactive DOM editor was already showing the current client-side route, while the lower image remained a frozen snapshot until the next Queue Prompt. This created the false impression that P10 was using a separate hidden drone path.

3. **Edited routes only become downstream authority on the next prompt execution.**
   The frontend writes the edited JSON into the hidden route_plan_json widget immediately, but nodes 08/09/10 cannot consume a human edit that happens after the same prompt has already executed. This is an unavoidable human-in-the-loop boundary in a normal ComfyUI prompt.

4. **The second prompt did use the artist-authored drones.**
   The runtime log shows a new prompt after the first completion and then three WAN sampling passes, matching the three artist missions.

5. **P9 was cached on the second prompt.**
   The expensive MoGe/P9 solve appears only in the first prompt. The second prompt begins directly in the P10/WAN work. Therefore the current system already avoids a second full P9 solve, but the first prompt still wastes a default P10 pass before the artist can author the route.

6. **P10 attempt outputs are not yet immutable per execution.**
   P9 run_dir is scene-run identity and is correctly reused by ComfyUI cache. However several P10 directories are keyed only by the parent P9 run_id, so a later P10 attempt for the same P9 scene can replace previous route/evidence/WAN preview files.

7. **The observed pre-fusion mesh is not accepted as a quality result.**
   It is visibly fragmented into disconnected islands in the current preview. Because the camera routes were authored against a misleading map, this result must be treated as diagnostic only and retested after route-authoring corrections.

## Architecture decision

Do **not** solve this by generating a different low-fidelity geometry and then switching to High Fidelity for production. Route clearance and camera placement must be authored against the same authoritative P9 scene that production P10 will consume.

The preferred flow is a two-stage handoff around the immutable P9 run_dir:

### Stage A — P9 Scene Solve + Route Setup

- Run P9 once using the intended authoritative geometry profile.
- Produce the PrimaryMesh / camera / source / raw P9 evidence and immutable run_dir.
- Open the route editor from that completed P9 run.
- Do not execute WAN or Gate 6 reconstruction in this stage.
- Artist edits and commits the P10 route.

### Stage B — P10 Production from Existing P9 Run

- Load the existing P9 run_dir without re-solving P9.
- Load the scene-bound committed route.
- Generate P10 evidence, WAN completion, known-camera reconstruction and later Gate 7 fusion.
- Preserve raw P9 evidence because the P10 boundary already consumes run_dir artifacts rather than requiring live in-memory P9 tensors.

This removes the wasted default P10 pass while preserving exact P9 authority.

## DR9R corrective gates

### DR9R-A — Orthographic Accuracy + Duplicate Preview Cleanup
Status: **IMPLEMENTED / CI PENDING**

- Preserve one metric scale in each TOP/SIDE/FRONT orthographic panel.
- Add source-image colors to sampled PrimaryMesh points when source coordinates are available.
- Remove the stale second image preview from the route-authoring node UI.
- Explicitly tell the artist that edited routes apply on the next Queue Prompt.
- Keep route/collision math unchanged.

### DR9R-B — 4-View Route Workspace
Status: **NEXT**

- Add one interactive perspective/orbit viewport.
- Keep TOP, SIDE and FRONT as locked orthographic views.
- All four views display the same scene/route state.
- Route placement/editing remains authoritative in orthographic views; perspective is initially navigation/inspection to avoid ambiguous depth picking.
- Add camera/frustum and route direction visualization.

### DR9R-C — Explicit Two-Stage P9→P10 Handoff
Status: **PLANNED**

- Create Route Setup execution path that stops before WAN/Gate 6.
- Persist/commit route against scene_contract_id + P9 run_id.
- Create P10 Production entry that loads an existing P9 run_dir and committed route.
- No second P9 solve required.

### DR9R-D — Immutable P10 Attempt Directories
Status: **PLANNED**

- Introduce p10_attempt_id separate from parent p9_run_id.
- Every P10 Queue Prompt receives a unique attempt folder.
- Store parent_p9_run_id, scene_contract_id and route_plan_sha256 in the attempt manifest.
- Never overwrite a prior P10 attempt.
- Maintain LATEST_P10_RUN pointer for convenience only.

### DR9R-E — Runtime Regression + New Test Bundle
Status: **PLANNED**

- Re-run route setup with a curved/descending PATH plus SPIN_360.
- Confirm one GIF per authored drone.
- Confirm WAN/reconstruction consume the committed route.
- Inspect pre-fusion mesh after corrected route placement.
- Only then close DR9 runtime acceptance and continue Gate 7.
