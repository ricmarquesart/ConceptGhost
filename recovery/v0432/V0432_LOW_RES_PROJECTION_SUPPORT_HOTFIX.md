# ConceptGhost v0.43.2 — Low Resolution Projection Support Hotfix

Runtime error:
- Node: ConceptGhostMoGeProjectionSupport
- Low Resolution profile failed with NameError:
  low_resolution_projection_threshold is not defined.

Root cause:
- _refine_moge_projection_support(...) receives its threshold as the local parameter
  discontinuity_threshold.
- One line inside the helper incorrectly referenced the outer node input name
  low_resolution_projection_threshold, which is not in helper scope.
- High Fidelity avoided the crash because it passes threshold=0.0 and therefore skips
  the discontinuity-filter block.
- Low Resolution passes the active threshold (normally 0.20), enters the block, and
  hit the undefined symbol.

Fix:
- Replace only:
  float(low_resolution_projection_threshold)
  with:
  float(discontinuity_threshold)

No solver/model/refine-step/resolution/FOV/manual-metric/geometry-profile policy change.

Cumulative status:
- v0.43.1 Maya metric-unit conversion remains required/preserved.
- v0.43.2 adds the Low Resolution Projection Support fix.
