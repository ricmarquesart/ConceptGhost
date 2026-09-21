from __future__ import annotations

from pathlib import Path
from typing import Protocol, Sequence, Any
from .contracts import CompletionBundle
from .path_planner import CameraPath


class BaselineBundleAdapter(Protocol):
    def load(self, bundle: CompletionBundle) -> Any: ...


class PanoramaContextAdapter(Protocol):
    def build(self, scene: Any, output_dir: Path) -> Path: ...


class SplatKitControlAdapter(Protocol):
    def render_paths(
        self, scene: Any, panorama: Path, paths: Sequence[CameraPath], output_dir: Path
    ) -> Sequence[Path]: ...


class WanCompletionAdapter(Protocol):
    def complete(self, control_set: Sequence[Path], output_dir: Path) -> Sequence[Path]: ...


class SourceCompositeAdapter(Protocol):
    def composite(
        self, generated_views: Sequence[Path], scene: Any, output_dir: Path
    ) -> Sequence[Path]: ...


class SphereSfMAdapter(Protocol):
    def reconstruct(self, views: Sequence[Path], output_dir: Path) -> Path: ...


class ColmapDenseAdapter(Protocol):
    def reconstruct_dense(self, sparse_model: Path, output_dir: Path) -> Path: ...


class BaselineFusionAdapter(Protocol):
    def fuse(self, scene: Any, dense_result: Path, output_dir: Path) -> Path: ...


class MayaExportAdapter(Protocol):
    def export(self, scene: Any, completed_mesh: Path, output_file: Path) -> Path: ...
