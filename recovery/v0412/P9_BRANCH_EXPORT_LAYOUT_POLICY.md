# ConceptGhost v0.41.2 — Branch / Export / Layout runtime hotfix

Observed runtime failures are distinct:

- **Baseline v0.36:** inactive Refined branch surfaced a red `ExecutionBlocked: Refined branch not selected`.
- **Refined Solver Fusion:** export reached PLY/USD/DCC mesh/Maya worker, then surfaced `long_triangle_policy: None != 'disabled'`.

v0.41.2 policy:

- inactive branch remains execution-gated but uses a silent blocker;
- PrimaryMesh→Maya handoff re-stamps immutable GeometryProfile topology-policy identity;
- Maya failure manifests preserve policy fields and root worker error is surfaced before a secondary contract mismatch;
- stale Maya manifest is removed before every worker invocation;
- workflow is repacked into separated lanes: 104 nodes / 215 links / 18 groups, zero overlap, >=60 px node safety envelope;
- no solver/FOV/P9.10/P9.13 algorithm change;
- new solvers: 0;
- packaged ZIP SHA-256: `2e047906e6f4b21b307e9be27a662ca3c138958e8f19183f575cd011b3b63a18`.

Windows/ComfyUI/Maya acceptance remains pending.
