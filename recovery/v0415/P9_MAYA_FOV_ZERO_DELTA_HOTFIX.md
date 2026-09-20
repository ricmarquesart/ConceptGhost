# ConceptGhost v0.41.5 — Maya FOV zero-delta parity hotfix

Real Maya parity evidence:
- canonical_fov_x_deg = 71.500118
- maya_live_fov_x_deg = 71.500118
- fov_delta_deg = 0.0
- tolerance_deg = 0.02
- status = PASS

The contract still failed because it used Python truthiness fallback:
`float(record.get("fov_delta_deg") or 999.0)`.

A valid numeric zero is falsey, so 0.0 became 999.0.

v0.41.5 uses explicit None handling:
- missing delta => fail-closed
- numeric zero is preserved
- any delta <= tolerance passes
- any delta > tolerance fails

The fix is applied to both Maya-manifest parity validation and P9.14 export-identity parity validation.

All v0.41.1-v0.41.4 fixes are retained. New solvers: 0.
Packaged ZIP SHA-256:
`1c667cf56cdd5a771b7a57b0dfd36e41051ec4c57abc154185b9f213e752d94f`.
