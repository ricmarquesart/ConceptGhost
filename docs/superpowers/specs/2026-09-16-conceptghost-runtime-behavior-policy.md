# ConceptGhost — Runtime Behavior Policy

Date: 2026-09-16
Status: Active design policy — camera Auto behavior approved
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

## 3. Required provenance

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

## 4. No hidden success substitution

A successful Atlas Learned execution is not automatically a valid camera if it fails ConceptGhost quality criteria.

Likewise, a successfully executed Atlas VP node is not sufficient by itself.

The final camera authority is the solver that passes the documented ConceptGhost camera-quality gate.

## Related documents

- `docs/superpowers/specs/2026-09-16-conceptghost-master-workflow-design.md`
- `docs/superpowers/specs/2026-09-16-conceptghost-master-workflow-ui-layout.md`
- `docs/superpowers/plans/2026-09-16-conceptghost-master-workflow-addendum.md`
