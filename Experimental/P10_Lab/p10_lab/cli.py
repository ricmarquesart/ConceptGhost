from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contracts import CompletionBundle, SceneScale
from .path_planner import default_paths
from .pipeline import ORDERED_STAGES


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ConceptGhost P10-Lab dry-run validator for P9 (= Baseline)"
    )
    parser.add_argument("bundle_dir", type=Path)
    parser.add_argument("--scene-radius", type=float, default=1.0)
    args = parser.parse_args()

    bundle = CompletionBundle.from_directory(args.bundle_dir)
    paths = default_paths(SceneScale(args.scene_radius))

    report = {
        "source_stage": bundle.source_stage,
        "source_equivalent_to": "baseline",
        "source_run_id": bundle.source_run_id,
        "optional_inputs": sorted(bundle.optional),
        "paths": [
            {"name": p.name, "waypoints": [w.__dict__ for w in p.waypoints]}
            for p in paths
        ],
        "pipeline": [stage.value for stage in ORDERED_STAGES],
        "status": "DRY_RUN_OK",
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
