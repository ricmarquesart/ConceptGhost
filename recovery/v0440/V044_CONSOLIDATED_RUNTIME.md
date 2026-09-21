# ConceptGhost v0.44.0 — Consolidated Runtime

Purpose: consolidate the active v0.43 production path and the two runtime fixes validated from real Windows/ComfyUI/Maya runs.

Included:
- P9 Baseline / Refined clone architecture.
- Manual Metric Authority.
- v0.43.1 Maya metric-unit boundary fix: canonical meters -> Maya centimeters at 100 cm per meter.
- v0.43.2 Low Resolution Projection Support fix: helper uses discontinuity_threshold instead of the undefined low_resolution_projection_threshold.
- Existing MoGe-3 quality settings are preserved.

Packaging policy:
- No Legacy workflow directory.
- No retired P9 runtime installers.
- No historical compatibility-only scripts in the release bundle.
- Runtime modules still imported by nodes.py remain packaged even if their filenames originate from earlier P9 development.

Release bundle:
- ConceptGhost_v0.44.0_CONSOLIDATED_RUNTIME.zip
- Workflow: ConceptGhost_Master_v0.44.0_CONSOLIDATED_RUNTIME.json
- 77 nodes / 146 links / 17 groups.
- Bundle manifest + SHA256SUMS + streamlined installer/verifier.
