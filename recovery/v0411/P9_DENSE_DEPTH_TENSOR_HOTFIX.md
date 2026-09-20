# P9.9 Dense Depth Tensor Runtime Hotfix — v0.41.1

The first real v0.41.0 AUTO execution passed the new P9.4 FOV Authority and reached P9.9 Dense Depth Fusion.

Runtime failure:
`Boolean value of Tensor with more than one value is ambiguous`

Root cause:
`nodes.py` used Python boolean coalescing on multi-element PyTorch tensors:

`mg.get("depth_metric_native") or mg.get("depth")`
`mg.get("mask_native") or mg.get("mask")`

Fix:
select primary/fallback values only through explicit `is None` checks. No tensor/ndarray truth-value evaluation is allowed.

Scope:
- P9.4 FOV Authority unchanged.
- Solver outputs unchanged.
- Dense fusion math unchanged.
- Semantic/P9.10 unchanged.
- P9.13–P9.15 unchanged.
- New solvers: 0.
- Bundle SHA-256: `ba49b7b51fe44ba7b050344835285a0faac8976dc78c3904ba09a7c0b4f66138`.

Runtime acceptance remains pending the next Windows/ComfyUI/Maya run.
