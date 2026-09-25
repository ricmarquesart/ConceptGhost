# ConceptGhost P10 — R6G Route Editor Visual Quality & Layout

Date: 2026-09-25
Status: SOURCE/CI COMPLETE — TARGET-PC VISUAL ACCEPTANCE PENDING

## Scope

This gate is intentionally independent from the P9 PrimaryMesh regression.
The v0.36-compatible one-root MoGe runtime restored the accepted P9 geometry
quality. R6G changes only display-only Route Editor geometry, layout and artist
controls. It must not mutate P9 geometry, camera authority, route handoff or P10
reconstruction contracts.

## R6G-A — Preview fidelity

### Root cause found

The previous Mesh Surface preview was not a coherent decimated mesh. It selected
approximately every Nth source triangle until the 24k face budget was reached:

`faces[::face_stride]`

That produces disconnected islands/triangles and explains why Mesh Surface could
look less legible than Points even when the authoritative PrimaryMesh was good.

Point LODs also used flattened vertex stride sampling. A thin/distant feature
could be under-represented simply because its vertices did not land on the
stride.

### Correction

- point LODs use deterministic source-image-space stratification when
  `grid_xy/source_uv` exists;
- thin/distant source-image regions therefore retain coverage;
- Mesh Surface uses image-grid clustering and remaps all authoritative source
  faces through the grid cells;
- degenerate/duplicate coarse triangles are removed;
- the result is a coherent connected display LOD rather than disconnected
  every-Nth triangles;
- mesh display budget raised from 24k to 60k faces;
- all preview geometry remains
  `DISPLAY_ONLY_NEVER_GEOMETRY_AUTHORITY`.

## R6G-B — Workspace layout

The live Selected Camera View moves from above the four-view editor to the left.

Desktop layout:

```
+-------------------------+-------------------------+
|                         | Perspective | Top       |
|  Selected Camera View   |-------------+-----------|
|  live selected waypoint | Side        | Front     |
|                         |             |           |
+-------------------------+-------------------------+
```

The two columns have equal footprint. The selected-camera raster increases from
640 px to 960 px internal width.

## R6G-C — Local view controls

Each Perspective/Top/Side/Front viewport receives prominent overlay controls:

- zoom - / +;
- selected-waypoint nudge left/right/up/down;
- selected-waypoint yaw - / +;
- selected-waypoint pitch - / +;
- DEL selected point.

Orthographic nudges map exactly to that view's two locked axes. Perspective
nudges move the already-selected waypoint in the current orbit view plane while
preserving depth, avoiding ambiguous click-to-create behavior.

Pivot controls are removed from the global toolbar and exist only in the
Perspective viewport:

- Reset Pivot
- Pivot Scene
- Pivot Cam

## R6G-D — Selected camera preview

The dedicated Selected Drone Camera Preview also consumes the corrected coherent
mesh LOD and its default width is raised to 960 px. It remains a display-only
validation view and never changes P9.

## Roll

The current route authority stores a forward/look direction (yaw/pitch derived)
but has no roll field. A cosmetic Roll button would be misleading because the
downstream camera basis would ignore it. True roll therefore requires an
end-to-end schema change (route authority, interpolation, camera basis, exports,
WAN/control sequence). R6G does not fake roll. It is reserved as a separate
follow-on gate if required.

## Acceptance

R6G source acceptance requires:
1. Python tests for image-space point sampling and coherent mesh LOD.
2. Frontend contract tests for left-side selected camera layout and per-view
   controls.
3. Node/JS parse validation in CI.
4. Target-PC visual validation using the now-restored good P9 PrimaryMesh.
5. No P9 authority/hash/geometry mutation.
