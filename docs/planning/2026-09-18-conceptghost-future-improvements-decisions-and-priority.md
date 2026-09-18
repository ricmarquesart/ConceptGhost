# ConceptGhost — Future Improvements Decisions & Implementation Priority

**Date:** 2026-09-18  
**Status:** Consolidated decision document / future implementation candidate  
**Scope:** Future ConceptGhost improvements focused on metric scale, regional depth, architectural metrology, Maya diagnostics, object-aware geometry, and independent metric validation.

---

# 1. Purpose

This document records the current decisions about what should move forward, what should be deferred, what should be frozen, and what should be removed from future ConceptGhost planning.

The central implementation principle is:

```text
USE WHAT IS ALREADY INSTALLED FIRST
        ↓
ADD DETERMINISTIC GEOMETRY / METROLOGY
        ↓
ADD ONE INDEPENDENT METRIC WITNESS
        ↓
BUILD ROBUST CONSENSUS
        ↓
ONLY THEN CONSIDER MORE COMPLEX AI / 3D SEGMENTATION SYSTEMS
```

The goal is to maximize improvement per unit of implementation complexity. This plan is not tied to a specific ConceptGhost release number.

---

# 2. Core architectural decisions

## 2.1 MoGe-3 is the official geometry engine

The future main geometry path is:

```text
MoGe-3
```

DA3 is being retired from the future architecture.

Therefore DA3 is **not** part of:

```text
metric consensus
structural witness
future geometry arbitration
future diagnostics
future correction logic
```

Historical DA3 code may remain temporarily for cleanup/backward compatibility, but it is not part of the future design.

## 2.2 Atlas remains camera authority

Atlas continues to define:

```text
intrinsics
FOV
camera pose
world up
projection
source-image correspondence
```

Other models may provide their own camera/intrinsic estimates, but these are diagnostic witnesses, not automatic camera replacements.

## 2.3 MoGe native metric output becomes first-class evidence

MoGe already produces information that ConceptGhost does not yet exploit fully. Before installing additional models, ConceptGhost should preserve, expose, measure, and compare everything useful already returned by MoGe.

## 2.4 Metric evidence is report-only first

The first metric system must answer:

```text
What does each source estimate?
Do they agree?
Which source is an outlier?
How large is the disagreement?
```

It must not immediately move official geometry. Automatic metric correction is a later phase requiring multi-scene validation.

## 2.5 New external models must justify their maintenance cost

A new model is approved only if it adds a capability that the existing stack cannot deliver adequately.

---

# 3. ACTIVE / APPROVED ITEMS

# A1 — Fully exploit MoGe native metric and measurement capabilities

**Status:** APPROVED  
**Priority:** 1 / highest  
**Installation complexity:** Very low  
**New runtime required:** No

This is broader than only preserving metric scale. ConceptGhost should create a complete:

```text
MoGe Metric Evidence & Measurement Layer
```

using data MoGe already produces.

## A1.1 Native metric point map

Preserve immutable:

```text
points_metric_native
```

before ConceptGhost registration/canonical scaling.

Use for:

```text
camera-to-point distance
point-to-point distance
regional dimensions
building depth
cross-region comparison
metric diagnostics
```

## A1.2 Native metric depth

Preserve immutable:

```text
depth_metric_native
```

Use for:

```text
regional depth
foreground/background separation
distance statistics
comparison against Atlas metrology
future metric consensus
```

## A1.3 MoGe measurement utilities

Expose measurements derived directly from the metric point map:

```text
distance between two selected points
camera → selected point
distance between structures
approximate width
approximate vertical extent
regional depth median
regional depth spread
```

## A1.4 MoGe normals as evidence

Use native normals for:

```text
ground orientation
façade planar consistency
surface orientation
normal discontinuity detection
local geometry quality
vertical/horizontal surface diagnostics
```

Rule:

```text
MoGe native normals = evidence
final mesh normals = derived from final topology
```

## A1.5 MoGe intrinsics vs Atlas

Store and compare:

```text
Atlas focal/FOV
vs
MoGe focal/FOV
```

Possible states:

```text
CONSISTENT
MODERATE_DISAGREEMENT
STRONG_CONFLICT
```

Atlas remains camera authority.

## A1.6 MoGe mask / valid support

Use the valid mask to report:

```text
where geometry is supported
where support disappears
where High Fidelity recovers additional pixels
where silhouette support changes
```

## A1.7 MoGe refinement diagnostics

Where available, preserve optional per-step diagnostic evidence:

```text
refinement step 0
step 1
step 2
...
```

Use for benchmark/diagnostic questions such as:

```text
where did refinement improve depth edges?
which regions remain unstable?
how do normals change?
```

### A1 expected value

```text
metric scale          +++
regional depth        +++
measurement           +++
normal validation     ++
camera cross-check    ++
quality diagnostics   +++
integration risk      very low
```

---

# A2 — Atlas + Ground Plane + Ray Metrology

**Status:** APPROVED  
**Priority:** 2  
**Installation complexity:** Very low  
**New AI model:** No

Use the solved Atlas camera for deterministic geometric measurement.

```text
pixel
→ Atlas ray
→ ground-plane intersection
→ world XYZ
→ camera distance
→ ground distance
```

Mathematical model:

```text
X(t) = C + t d

t = -(n·C + b) / (n·d)
```

Primary purpose:

```text
determine where the base of an architectural structure intersects the ground
```

Example:

```text
Tower_01 base
camera distance = 72.4 m
ground-horizontal distance = 71.8 m
```

---

# A3 — Architectural Distance and Height

**Status:** APPROVED  
**Priority:** 3  
**Installation complexity:** Very low  
**Dependency:** A2

Once the base is located:

```text
base position B
+
world up U
+
Atlas ray through top pixel
```

solve the closest intersection/approach between:

```text
B + hU
```

and:

```text
C + t d_top
```

Output:

```text
estimated_distance_m
estimated_height_m
closest_approach_residual
confidence
```

Example:

```text
Tower_01
Distance: 72.4 m
Height: 18.7 m
Height residual: 0.18 m
Status: VALID
```

## A3.1 Physical Size Consistency

Add a plausibility diagnostic:

```text
Tower = 18.7 m
House = 8.2 m
Tower/House = 2.28×
```

This is plausibility evidence, not absolute authority.

---

# A4 — Ground-Plane Quality + Local Ground Fallback

**Status:** APPROVED  
**Priority:** 4  
**Installation complexity:** Low

Required hierarchy:

```text
GLOBAL GROUND PLANE
        ↓ if quality fails
LOCAL GROUND PLANE near target
        ↓ if quality fails
INSUFFICIENT_GROUND_MODEL
```

Track:

```text
support_count
support_ratio
inlier_count
inlier_ratio
planarity_residual
spatial_coverage
normal_consistency
confidence
```

Prefer no measurement over fabricated measurement.

---

# A5 — MoGe × Atlas Metric Agreement

**Status:** APPROVED  
**Priority:** 5  
**Installation complexity:** Very low  
**Dependency:** A1 + A2/A4

Compare:

```text
Atlas / geometric metrology
vs
MoGe native metric geometry
```

Examples:

```text
Atlas camera height = 1.65 m
MoGe camera-to-ground = 1.58 m
Difference = 4.2%
Status = CONSISTENT
```

or:

```text
Atlas = 1.65 m
MoGe = 0.91 m
Status = CONFLICT
```

Regional comparisons should include:

```text
Tower base
Near building
Far building
Foreground object
```

This becomes the first two-source metric-validation layer.

---

# A6 — Maya Metric Diagnostics & Region Layer

**Status:** APPROVED  
**Priority:** 6  
**Installation complexity:** Low  
**New runtime:** No

The previous Maya Object Layer item is merged into A6.

Provide:

```text
CG_METRIC_DIAGNOSTICS
```

with possible helpers:

```text
camera-height marker
ground-plane grid
target base locator
target top locator
distance line
height line
metric labels
agreement/conflict metadata
```

Example:

```text
Tower_01
MoGe native: 70.9 m
Atlas metrology: 72.4 m
Depth Pro: 73.1 m
Consensus: 72.2 m
Estimated height: 18.7 m
Agreement: HIGH
```

## A6.1 Maya Selection Sets / Region Layer

When geometric regions exist, export them as:

```text
CG_REGION_001
CG_REGION_002
CG_REGION_003
```

or artist-assigned names:

```text
CG_GROUND
CG_FACADE_01
CG_ROOF_01
CG_TOWER_01
```

Rule:

```text
region = metadata / selection
region ≠ geometry deletion
```

---

# A7 — Local Geometry Cleanup / Region Operations

**Status:** APPROVED CONCEPTUALLY, DEFERRED  
**Priority:** After metric foundation  
**Installation complexity:** Low/medium  
**New AI:** No

Purpose:

> Apply cleanup only where needed instead of modifying the entire mesh.

Example:

```text
good façade
good roof
good stairs
+
20 floating/spike points around one tower
```

Instead of global smoothing:

```text
target region
→ local diagnostic
→ local cleanup
→ rest of scene untouched
```

Candidate operations:

```text
isolated floating-component detection
spike / outlier detection
local plane fitting
local smoothing
small-hole diagnostics
local remeshing
adaptive local mesh density
boundary-protected triangulation
```

Possible evidence:

```text
XYZ position
depth
normals
mesh connectivity
depth edges
connected components
geometric regions
manual selection
```

Initial mode:

```text
DIAGNOSTIC / ARTIST-APPROVED
```

not automatic destructive editing.

---

# 4. REMOVED ITEM

# A8 — DA3 Structural Witness

**Status:** REMOVED FROM FUTURE PLAN

DA3 is being retired and will not participate in metric consensus, geometry arbitration, witnesses, diagnostics, or correction logic.

Future assumption:

```text
MoGe-3 = official geometry engine
```

---

# 5. ACTIVE EXTERNAL WITNESS

# B1 — Depth Pro

**Status:** APPROVED AS PRIMARY INDEPENDENT METRIC-WITNESS CANDIDATE  
**Priority:** First new external model  
**Installation complexity:** Medium  
**Purpose:** Independent metric validation, not a second official mesh

Depth Pro should not create a competing official geometry path.

Its job is:

```text
SOURCE IMAGE
+
Atlas known focal/camera information where applicable
        ↓
Depth Pro
        ↓
independent metric depth evidence
```

Architecture:

```text
             SOURCE IMAGE
                  │
      ┌───────────┼───────────┐
      │           │           │
      ▼           ▼           ▼
    MoGe-3      Atlas      Depth Pro
      │       Metrology        │
      ▼           ▼           ▼
   metric       metric      metric
   witness      witness     witness
      │           │           │
      └───────────┼───────────┘
                  ▼
           METRIC CONSENSUS
```

## B1.1 Why parallel evidence is useful

Case 1:

```text
MoGe = 70 m
Atlas = 72 m
Depth Pro = 71 m
```

Interpretation:

```text
strong agreement
```

Case 2:

```text
MoGe = 70 m
Atlas = 72 m
Depth Pro = 38 m
```

Interpretation:

```text
Depth Pro likely outlier
```

Case 3:

```text
MoGe = 43 m
Atlas = 71 m
Depth Pro = 69 m
```

Interpretation:

```text
MoGe regional metric may be wrong
```

Parallel evidence exists to answer:

```text
When two systems disagree, which interpretation has more independent support?
```

## B1.2 Initial operating mode

Depth Pro initially contributes only to:

```text
reports
comparison
conflict detection
metric consensus
```

It does not move the official mesh.

---

# 6. FROZEN EXTERNAL METRIC OPTION

# B2 — Metric3D v2

**Status:** FROZEN / FUTURE OPTION  
**Reason:** Insufficient incremental value at present

Metric3D provides metric depth and surface normals, but this currently overlaps with:

```text
MoGe metric depth
MoGe normals
Depth Pro independent depth
```

Reconsider only if a future requirement specifically needs an independent architecture-normal/planarity witness or demonstrates superior metric behavior.

---

# 7. ACTIVE CONSENSUS SYSTEM

# B3 — Metric Consensus Engine

**Status:** APPROVED  
**Priority:** After B1 is available  
**Installation complexity:** Low  
**New AI model:** No

Required evidence set:

```text
1. MoGe native metric
2. Atlas deterministic metrology
3. Depth Pro independent metric depth
```

## B3.1 Never use simple mean

Forbidden:

```text
(38 + 71 + 73) / 3
```

Preferred:

```text
weighted median
MAD / robust spread
agreement groups
outlier rejection
source quality gating
```

Each observation:

```text
VALID
WEAK
OUTLIER
UNAVAILABLE
```

## B3.2 Example

```text
Tower_01

MoGe: 38 m       OUTLIER
Atlas: 71 m      VALID
Depth Pro: 73 m  VALID
Consensus: ~72 m
Status: HIGH AGREEMENT among independent evidence
```

## B3.3 Initial operating mode

```text
REPORT ONLY
```

Potential future progression:

```text
report
→ recommendation
→ artist-approved correction
→ carefully gated automatic correction
```

---

# 8. DEFERRED GEOMETRIC REGION SYSTEM

# B4 — Simplified Geometric Regions / Graph Superpoints

**Status:** KEEP, BUT DEFER  
**Priority:** After metric foundation  
**Installation complexity:** Low/medium if implemented geometrically  
**New AI:** No for simplified version

This is not another solver and does not create a competing mesh.

Purpose: divide the existing official geometry into coherent surface regions.

Example:

```text
2.8 million triangles
        ↓
geometric analysis
        ↓
Region 001 = ground patch
Region 002 = planar façade
Region 003 = roof surface
Region 004 = side wall
Region 005 = separate depth layer
```

Analyze:

```text
normal similarity
depth discontinuity
mesh connectivity
planarity
curvature
spatial proximity
connected components
```

## B4.1 Contribution to official mesh

Use regions as boundaries for later operations:

```text
do not smooth façade and roof together
do not bridge unrelated depth layers
fit a plane only to planar façade
remove spikes only inside one region
increase density only where needed
```

Therefore B4 may later contribute directly to official Hero Mesh refinement after its boundaries are validated.

## B4.2 Relationship with A7

```text
B4 identifies coherent regions
        ↓
A7 performs local operations on those regions
```

Example:

```text
B4: Region_014 = façade patch
A7: plane-fit Region_014, remove local spikes, preserve boundary
```

---

# 9. B5 MERGED INTO A6

The former:

```text
B5 — Maya object layer based on manual/geometric regions
```

is now part of:

```text
A6 — Maya Metric Diagnostics & Region Layer
```

It is an export/usability concern, not a separate solver.

---

# 10. FROZEN FOR FUTURE POSSIBILITY

## C1 — Point-SAM

**Status:** FROZEN / future isolated spike

Potential future value:

```text
click tower
→ 3D segment
→ CG_TOWER_01
```

Useful for object isolation, object metrics, local cleanup, selection sets and boundary protection.

Do not integrate now.

## C2 — EZ-SP / Superpoint Transformer full stack

**Status:** FROZEN

Potential future role: learned 3D geometric partition + Point-SAM stabilization.

B4 gives us a simpler geometric-region experiment first.

## C3 — UniDepth V2

**Status:** FROZEN

Technically strong independent metric witness, but higher runtime complexity.

Reconsider if Depth Pro is insufficient or UniDepth shows a clearly superior measurable result.

## C4 — Mask3D

**Status:** FROZEN

Reconsider only if automatic 3D instance discovery becomes an explicit requirement.

## C5 — Mosaic3D

**Status:** FROZEN

Reconsider only if open-vocabulary 3D text labeling becomes a concrete requirement.

## C6 — Full SIHE software stack

**Status:** DO NOT INTEGRATE AS FULL DEPENDENCY

Reuse single-view metrology principles rather than the complete software stack.

## C7 — SAM3D / OpenMask3D / Open3DIS-style 2D-first systems

**Status:** FROZEN / not recommended for current Single View path

Reconsider only for a future true Multi View branch.

---

# 11. Active future architecture

```text
                         SOURCE IMAGE
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
                 MoGe-3               Atlas
                    │                   │
        native metric points/depth      │
        normals / mask / intrinsics     │
                    │                   │
                    │           Ground Plane Model
                    │                   │
                    │            Ray Metrology
                    │                   │
                    ▼                   ▼
             MOGE METRIC          ATLAS METRIC
                    │                   │
                    │     Depth Pro     │
                    │         │         │
                    └─────────┼─────────┘
                              ▼
                     METRIC CONSENSUS
                              │
                              ▼
                     REPORT / DIAGNOSTICS
                              │
                              ▼
                    MAYA METRIC LAYER
```

Initial rule:

```text
NO AUTOMATIC MESH MOVEMENT
```

---

# 12. Deferred geometry-refinement architecture

Later, after the metric foundation is stable:

```text
MoGe High-Fidelity Geometry
        ↓
Simplified Geometric Regions (B4)
        ↓
Local Geometry Cleanup / Region Operations (A7)
        ↓
Maya Selection Sets / Region Metadata (A6)
        ↓
Official export
```

---

# 13. Proposed implementation order

## Phase 1 — Extract everything from MoGe

Implement:

```text
native point map preservation
native metric depth preservation
native normal diagnostics
native intrinsics comparison
valid-mask diagnostics
measurement utilities
refinement diagnostics
```

No new external solver.

## Phase 2 — Deterministic Atlas Metrology

Implement:

```text
ground-plane model
ground quality scoring
local-ground fallback
ray generation
ray-ground intersection
building/tower base distance
architectural height
physical-size consistency
```

No new external AI.

## Phase 3 — MoGe × Atlas Agreement

Build:

```text
global scale agreement
regional depth agreement
camera-height agreement
conflict reports
```

At this point ConceptGhost already has a useful two-source metric system.

## Phase 4 — Maya Metric Diagnostics

Export:

```text
ground plane
measurement locators
height/distance lines
regional reports
conflict metadata
```

Also prepare generic selection/region infrastructure.

## Phase 5 — Depth Pro Installation Spike

Goal:

```text
one isolated independent metric witness
```

Validate:

```text
runtime
GPU compatibility
known focal input
metric output
same source image
reproducibility
```

Do not make it geometry authority.

## Phase 6 — Metric Consensus

Combine:

```text
MoGe
Atlas
Depth Pro
```

Add:

```text
weighted median
MAD
agreement groups
outlier rejection
quality classification
```

Mode:

```text
REPORT ONLY
```

## Phase 7 — Simplified Geometric Regions

Implement B4 using:

```text
normals
depth edges
connectivity
planarity
curvature
connected components
```

No heavy AI required.

## Phase 8 — Local Geometry Cleanup

Use B4 or manual regions for A7:

```text
local spike cleanup
floating-component cleanup
plane fitting
local smoothing
adaptive remesh
boundary protection
```

Initially diagnostic / artist-approved.

## Phase 9 — Re-evaluate frozen tools

Only now ask whether a remaining gap requires:

```text
Point-SAM
EZ-SP
UniDepth
Metric3D
Mask3D
Mosaic3D
```

Each must justify its runtime and maintenance cost.

---

# 14. Decision summary

| Item | Decision | Current role |
|---|---|---|
| A1 MoGe metric & measurements | APPROVED | first implementation priority |
| A2 Atlas ray-ground metrology | APPROVED | deterministic metric evidence |
| A3 architectural distance/height | APPROVED | physical structure measurement |
| A4 ground quality/local fallback | APPROVED | metrology reliability |
| A5 MoGe × Atlas agreement | APPROVED | two-source validation |
| A6 Maya diagnostics & region layer | APPROVED | artist-facing diagnostics/export |
| A7 local geometry cleanup | DEFERRED BUT APPROVED CONCEPTUALLY | later mesh refinement |
| A8 DA3 structural witness | REMOVED | DA3 retired |
| B1 Depth Pro | APPROVED CANDIDATE | third independent metric source |
| B2 Metric3D | FROZEN | optional future witness |
| B3 Metric Consensus | APPROVED | robust 3-source agreement |
| B4 simplified geometric regions | DEFERRED | future region/boundary layer |
| B5 Maya object layer | MERGED INTO A6 | no separate project |
| Point-SAM | FROZEN | future 3D segmentation experiment |
| EZ-SP | FROZEN | future learned superpoints |
| UniDepth V2 | FROZEN | future alternative metric witness |
| Mask3D | FROZEN | future automatic instances |
| Mosaic3D | FROZEN | future open-vocabulary 3D |
| Full SIHE | SKIP AS DEPENDENCY | reuse math only |
| 2D-first SAM3D/Open3DIS family | FROZEN | reconsider only for true multiview |

---

# 15. Final direction

The next major improvement program should focus on:

```text
MOGE
exploit everything already available
        +
ATLAS
turn solved camera into deterministic metrology
        +
DEPTH PRO
one independent learned metric witness
        +
METRIC CONSENSUS
robustly compare all three
        +
MAYA
make the result visible and auditable to the artist
```

Only after this foundation is proven should ConceptGhost invest in more complex 3D segmentation runtimes.

This keeps the project focused on:

```text
better geometry understanding
better physical scale
better depth validation
lower installation risk
lower runtime fragmentation
higher auditability
```

without accumulating models simply because they are available.
