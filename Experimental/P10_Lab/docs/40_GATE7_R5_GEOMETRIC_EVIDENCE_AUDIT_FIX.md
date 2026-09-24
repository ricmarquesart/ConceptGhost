# Gate 7 Preview r5 — COLMAP geometric evidence + audit closeout fix

Date: 2026-09-24
Status: SOURCE FIX IMPLEMENTED — PACKAGE/CI PENDING

## Runtime evidence from r4

The real target-PC run reached Gate 7 and failed with two independent findings:

1. Gate 7 reported zero usable geometric views because it requires both
   `*.geometric.bin` depth and `consistency_graphs/*.geometric.bin`.
2. Automatic RUN_AUDIT_BUNDLE then failed because the r4 package could exhaust
   its optional evidence budget before reserving
   `reconstruction_runtime_manifest.json`.

The r4 bundle source commit predates the later audit-core reservation and
run-local audit-storage commits, so the second failure is already corrected in
the active branch but not in the installed r4 package.

## r5 correction contract

### A. Gate 6 PatchMatch evidence

- Pass COLMAP boolean options as numeric `1/0`, avoiding version-sensitive
  `true/false` parsing.
- Explicitly enable `PatchMatchStereo.write_consistency_graph=1`.
- Dense reconstruction now records geometric depth, geometric normal and
  geometric consistency-graph counts.
- A zero geometric-depth or zero consistency-graph result fails at Gate 6 with
  a direct diagnostic instead of surfacing later as a misleading Gate 7
  coverage failure.
- Old dense manifests are not resume-compatible with this contract and are
  rebuilt as derived P10 data.

### B. Gate 7 coverage denominator

Gate 7 still uses only the intersection of registered views that have geometric
depth + consistency evidence. Missing authored views remain UNKNOWN and never
vote FREE.

The 70% evidence threshold now applies to **COLMAP-registered views**, which are
the views actually eligible to provide PatchMatch evidence. Authored-to-
registered coverage remains recorded as a reconstruction-quality diagnostic
rather than being silently reinterpreted as free-space evidence.

Per-mission coverage uses the same registered-view denominator. At least two
independent registered missions must still qualify.

This removes an accidental duplication of Gate 6 frame-drop quality policy
without weakening the free-space authority rule.

### C. RUN_AUDIT_BUNDLE

r5 incorporates the post-r4 source fixes:

- required audit manifests are reserved before optional visual-evidence budget;
- `reconstruction_runtime_manifest.json` cannot be displaced by optional files;
- default storage is run-local:
  `<P9_RUN>/P10_AUDIT/<P10_ATTEMPT>/RUN_AUDIT_BUNDLE.zip`;
- latest pointers live under `<P9_RUN>/P10_AUDIT/`.

## Gate boundary

Gate 8 remains blocked until r5 receives one real target-PC runtime acceptance.
P9 remains immutable and no P9 critical file is changed by this correction.
