# P9 v0.40.2 focal-consensus runtime hotfix

First real v0.40.1 Refined runtime reached P9.4 and stopped because the original 10% focal cluster threshold was treated as an absolute runtime stop.

v0.40.2 keeps the no-silent-Atlas-fallback rule and adds bounded recovery:

- STRONG_AGREEMENT: >=2 independent focal witnesses inside the configured 10% band.
- RECOVERED_AGREEMENT: only if strong agreement is absent, >=2 independent witnesses may form a recovery cluster up to 20% by default; confidence is reduced.
- HARD BLOCK: no coherent independent pair even inside the recovery bound remains fail-closed.
- Hard-block diagnostics include each focal/FOV observation plus pairwise relative differences.
- New solvers: **0**.
- Solver inference algorithms changed: **0**.
