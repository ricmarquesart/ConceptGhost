#!/usr/bin/env python3
"""ConceptGhost Stage 4 DA3 baseline loader.

The implementation is split into readable ``.pyinc`` source parts so the
Stage 4 source can be published and reviewed atomically through the project
connector without changing runtime behavior.
"""
from pathlib import Path as _CGPath

_CG_DIR = _CGPath(__file__).resolve().parent
for _CG_PART in (
    "cg_da3_baseline_part1.pyinc",
    "cg_da3_baseline_part2.pyinc",
    "cg_da3_baseline_part3.pyinc",
    "cg_da3_baseline_part4.pyinc",
):
    _CG_PATH = _CG_DIR / _CG_PART
    _CG_SOURCE = _CG_PATH.read_text(encoding="utf-8")
    exec(compile(_CG_SOURCE, str(_CG_PATH), "exec"), globals(), globals())

del _CG_DIR, _CG_PART, _CG_PATH, _CG_SOURCE, _CGPath
