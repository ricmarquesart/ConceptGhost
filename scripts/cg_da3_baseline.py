#!/usr/bin/env python3
"""ConceptGhost Stage 4 DA3 baseline loader."""
from pathlib import Path as _CGPath

_CG_DIR = _CGPath(__file__).resolve().parent
_CG_ORIGINAL_NAME = __name__
# Prevent the legacy part4 direct-execution block from firing before Stage 4S
# overrides in part5 have been loaded.
globals()["__name__"] = "scripts.cg_da3_baseline"
for _CG_PART in (
    "cg_da3_baseline_part1.pyinc",
    "cg_da3_baseline_part2.pyinc",
    "cg_da3_baseline_part3.pyinc",
    "cg_da3_baseline_part4.pyinc",
    "cg_da3_baseline_part5.pyinc",
):
    _CG_PATH = _CG_DIR / _CG_PART
    _CG_SOURCE = _CG_PATH.read_text(encoding="utf-8")
    exec(compile(_CG_SOURCE, str(_CG_PATH), "exec"), globals(), globals())
globals()["__name__"] = _CG_ORIGINAL_NAME

if _CG_ORIGINAL_NAME == "__main__":
    raise SystemExit(main())

del _CG_DIR, _CG_PART, _CG_PATH, _CG_SOURCE, _CGPath, _CG_ORIGINAL_NAME
