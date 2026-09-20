# P9 v0.40.3 non-blocking focal ambiguity hotfix

Real v0.40.2 runtime evidence:
- Atlas: 36.8317519559 deg / 2174.412489 px
- MoGeIndependent: 67.5001183692 deg / 1083.540149 px
- DepthPro: 54.9986956697 deg / 1390.829712 px

The workflow must not abort solely because these valid focal witnesses disagree.

Policy:
- STRONG_AGREEMENT first.
- RECOVERED_AGREEMENT second.
- Otherwise AMBIGUOUS_CONTINUE using robust log-median focal with explicitly low confidence.
- A single valid focal may continue as SINGLE_WITNESS_CONTINUE at very low confidence.
- Zero valid focal witnesses remains fatal.
- No silent Atlas fallback.
- P9.5 manual focal/FOV authority remains available.
- New solvers: 0.
