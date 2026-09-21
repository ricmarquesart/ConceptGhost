# ConceptGhost v0.41.8 — MoGe-3 Watchdog Status-Race Hotfix

Real runtime evidence showed a MoGe-3 worker reaching INFERENCE_DONE, SERIALIZE_START, DONE and result status PASS, then being killed by the parent monitor with "worker produced no heartbeat/status ... during startup".

Root cause:
- a transient unreadable/missing status-file poll during Windows atomic replacement was routed through the startup missing-status failure path even though valid statuses had already been observed;
- successful SystemExit(0) was caught by a BaseException handler and printed as FAILED.

v0.41.8:
- startup missing-status failure only applies while no valid status has ever been observed;
- a transient empty read after valid status is non-fatal;
- normal stale-heartbeat and hard-timeout gates remain active;
- SystemExit(0) is no longer logged as a failure;
- PIL->NumPy handoff uses a writable copy;
- runtime logs distinguish Atlas-conditioned MoGe geometry from the true independent focal probe.

v0.41.7 official run-pack restoration is retained. New solvers: 0.

Bundle SHA-256:
aed338a4099cb17b45436bccb8da0220a37d9af303815b75d294048054c51997
