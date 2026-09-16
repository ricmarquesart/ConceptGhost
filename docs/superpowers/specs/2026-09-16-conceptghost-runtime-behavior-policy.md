# ConceptGhost — Runtime Behavior Policy

Date: 2026-09-16
Status: Active design policy — camera Auto and geometry selection behavior approved
Project: ConceptGhost

## Purpose

Define deterministic runtime behavior for the user-facing `ConceptGhost_Master.json`.
This document complements the architecture, roadmap, and UI-layout specifications.

## 1. Camera control

User-facing camera choices:

- `Auto`
- `Atlas Learned`
- `Atlas VP`

### 1.1 `Camera = Auto` — approved behavior

`Auto` is deterministic and uses an ordered fallback:

```text
1. Run Atlas Learned
2. Evaluate the camera-quality acceptance criteria
3. If Atlas Learned PASSES:
      use Atlas Learned
      do not run Atlas VP as a replacement
4. If Atlas Learned FAILS the camera-quality criteria:
      run Atlas VP as fallback
5. Evaluate Atlas VP
6. If Atlas VP PASSES:
      use Atlas VP
      record that fallback occurred
7. If both fail:
      camera stage FAIL
      preserve diagnostics
      do not publish a valid Maya Ghost
```

`Auto` must never silently choose an unvalidated camera.

### 1.2 Explicit camera modes

If the user selects `Atlas Learned`, ConceptGhost runs that requested solver and does not silently replace it with Atlas VP.

If the user selects `Atlas VP`, ConceptGhost runs Atlas VP directly.

A future explicit option may allow fallback from a manually selected solver, but V1 should keep manual selections literal and predictable.

## 2. Camera-quality decision

The exact numerical/visual acceptance thresholds will be defined from Stage 3 evidence and benchmark scenes before the production Master Workflow is frozen.

The policy is fixed even if the thresholds evolve:

- a solver must pass the current documented quality gate before becoming the authoritative camera;
- fallback occurs because the primary solver failed the gate, not merely because another solver also exists;
- quality-gate evidence is preserved in diagnostics.

## 3. Camera provenance

Every run must record at minimum:

```text
camera.requested_mode
camera.primary_solver
camera.primary_status
camera.fallback_attempted
camera.fallback_reason
camera.final_solver
camera.final_status
```

Example:

```text
requested_mode: auto
primary_solver: atlas_learned
primary_status: fail
fallback_attempted: true
fallback_reason: camera_quality_gate_failed
final_solver: atlas_vp
final_status: pass
```

The user-facing result must clearly show the solver actually used.

## 4. Geometry control — approved V1 behavior

V1 deliberately has no `Geometry = Auto`.

User-facing geometry choices are:

- `DA3` — default
- `MoGe`

The separate `Compare Both` switch controls whether the alternate engine is also executed for comparison.

### 4.1 Default geometry

The default production-facing geometry engine in V1 is:

```text
Geometry = DA3
Compare Both = OFF
```

This default may be revisited only after Stage 9 A/B evidence, but the V1 architecture does not require an automatic engine chooser.

### 4.2 No silent geometry fallback

If the user explicitly selects DA3, ConceptGhost does not silently replace DA3 with MoGe because DA3 failed.

If the user explicitly selects MoGe, ConceptGhost does not silently replace MoGe with DA3 because MoGe failed.

The selected engine is part of the run's reproducible configuration.

The alternate engine can be run only when `Compare Both = ON` or when the user explicitly selects it in a new run.

### 4.3 Compare Both remains comparison, not Auto

`Compare Both = ON` means:

```text
selected Geometry engine = primary comparison branch
alternate engine = secondary comparison branch
both execute independently
both keep native outputs
both normalize independently
no automatic fusion
no hidden engine substitution
```

The run manifest must preserve which engine was selected as primary and which was executed only because `Compare Both` was enabled.

### 4.4 Geometry provenance

Every run must record at minimum:

```text
geometry.requested_engine
geometry.compare_both
geometry.primary_engine
geometry.primary_status
geometry.secondary_engine
geometry.secondary_status
geometry.final_authoritative_engine
```

For a normal DA3-only run:

```text
requested_engine: da3
compare_both: false
primary_engine: da3
secondary_engine: none
```

For a DA3-primary comparison run:

```text
requested_engine: da3
compare_both: true
primary_engine: da3
secondary_engine: moge
```

The exact behavior when the selected primary geometry fails but the comparison engine succeeds is a separate policy decision and must not be implemented implicitly.

## 5. No hidden success substitution

A successful Atlas Learned execution is not automatically a valid camera if it fails ConceptGhost quality criteria.

Likewise, a successfully executed Atlas VP node is not sufficient by itself.

The final camera authority is the solver that passes the documented ConceptGhost camera-quality gate.

For geometry, successful execution of a node or export is not sufficient to redefine which engine the user selected. V1 prioritizes reproducibility over hidden automatic substitution.

## Related documents

- `docs/superpowers/specs/2026-09-16-conceptghost-master-workflow-design.md`
- `docs/superpowers/specs/2026-09-16-conceptghost-master-workflow-ui-layout.md`
- `docs/superpowers/plans/2026-09-16-conceptghost-master-workflow-addendum.md`
