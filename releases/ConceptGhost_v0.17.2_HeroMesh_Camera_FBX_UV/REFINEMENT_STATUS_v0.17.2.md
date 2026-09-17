# ConceptGhost v0.17.2 — Hero Mesh + Camera / FBX / UV Corrections

Updated: 2026-09-17

## C10 — Matched camera / reference framing
- Film-back aspect is forced to `image_width / image_height` even if a supplied physical sensor-height disagrees.
- Maya render resolution is set to source width/height, pixel aspect 1.0.
- Matched camera explicitly uses Maya Horizontal film fit, resolution-gate display and gate mask.
- Source image plane is attached to `CG_MATCHED_CAMERA`, maintains source aspect and is camera-specific.
- Atlas remains the camera authority.

## C10B — E2 Maya/DCC coordinate space
- Native MoGe E2 Preview remains unchanged in OpenCV camera space.
- `ConceptGhostMeshForDCC` creates an independent copy for DCC export.
- Vertex conversion: native `(X,+Y down,+Z forward)` → `(X,-Y,-Z)`, metric registration when trusted, then Atlas `camera_world_matrix`.
- Preview mesh is never mutated.

## C11 — FBX camera contract
- FBX export explicitly enables cameras.
- Camera signatures are captured before export and checked after FBX import round-trip.
- Focal length, film aperture, film offsets and world matrix must survive.
- An existing `.fbx` file is not considered PASS unless round-trip verification passes.

## C12 — Preview vs Maya UV
- `E2 · MoGe Preview GLB`: raw MoGe mesh goes directly to SaveGLB; no V flip.
- `E2-DCC · Maya-ready GLB`: independent DCC copy receives V flip plus Atlas-world conversion.
- The ComfyUI preview and Maya/DCC export therefore use separate UV conventions without mutating each other.

## C13 — Hero Mesh inside `.ma` and official FBX
- `ConceptGhostExportBundle` now accepts the exact E2-DCC `MESH` as `hero_mesh`.
- The mesh is serialized run-locally with vertices, faces, UVs, normals and base-color texture when present.
- mayapy reconstructs the polygon mesh directly under `CG_GEOMETRY/CG_HERO_MESH` instead of leaving that group empty.
- `CG_HERO_MESH` is hidden by default but exists in the Outliner and can be enabled by the artist.
- The same Hero Mesh is selected together with `CG_MATCHED_CAMERA` and `CG_ARTIST_CAMERA` for the official FBX export.
- FBX round-trip now verifies the Hero Mesh as well as both cameras.
- If a requested Hero Mesh fails to author, `.ma`/FBX are no longer reported as successful.

## Automated verification
- `pytest`: 94 passed.
- `compileall`: passed.
- Stage 11: 28 nodes / 65 links / 2 SaveGLB branches.
- Stage 14 / Master: 32 nodes / 82 links / 2 SaveGLB branches.
- E2-DCC feeds both the Maya-ready GLB output and the official `.ma`/FBX exporter.

## Pending real runtime validation
- ComfyUI E2 Preview texture orientation on Windows.
- Maya Hero Mesh reconstruction/texture display using the artist's installed Maya version.
- Matched-camera overlay against the source image.
- FBX import in the artist's Maya showing both cameras + `CG_HERO_MESH` and preserving the camera signature.
