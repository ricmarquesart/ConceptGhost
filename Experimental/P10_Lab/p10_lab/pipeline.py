from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Stage(str, Enum):
    LOAD_BASELINE = "load_baseline"
    VALIDATE_SCENE = "validate_scene"
    PANORAMA_CONTEXT = "panorama_context"
    PLAN_PATHS = "plan_paths"
    COLLISION_GATE = "collision_gate"
    CONTROL_RENDER = "control_render"
    WAN_COMPLETION = "wan_completion"
    SOURCE_COMPOSITE = "source_composite"
    SPHERESFM = "spheresfm"
    COLMAP_DENSE = "colmap_dense"
    REGISTER_BASELINE = "register_baseline"
    FUSE_GEOMETRY = "fuse_geometry"
    CLEANUP = "cleanup"
    TEXTURE = "texture"
    REGRESSION = "regression"
    MAYA_EXPORT = "maya_export"


ORDERED_STAGES = tuple(Stage)


@dataclass(frozen=True)
class StageCheckpoint:
    stage: Stage
    artifact_dir: str
    validated: bool
    digest: str | None = None


def next_stage(current: Stage | None) -> Stage:
    if current is None:
        return ORDERED_STAGES[0]
    idx = ORDERED_STAGES.index(current)
    if idx + 1 >= len(ORDERED_STAGES):
        raise StopIteration("Pipeline already complete")
    return ORDERED_STAGES[idx + 1]
