from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess
from typing import Iterable

from .contracts import ContractError


@dataclass(frozen=True)
class ColmapStep:
    command: str
    args: tuple[str, ...]

    def argv(self, executable: str) -> tuple[str, ...]:
        return (executable, self.command, *self.args)


@dataclass(frozen=True)
class SparseTriangulationPlan:
    dataset_root: Path
    database_path: Path
    known_model_path: Path
    output_model_path: Path
    output_text_path: Path
    frame_count: int
    camera_count: int
    matcher: str
    sequential_overlap: int
    refine_intrinsics: bool
    steps: tuple[ColmapStep, ...]

    def manifest(self) -> dict[str, object]:
        return {
            "schema": "ConceptGhost.P10SparseTriangulationPlan.v0.1",
            "dataset_root": str(self.dataset_root),
            "database_path": str(self.database_path),
            "known_model_path": str(self.known_model_path),
            "output_model_path": str(self.output_model_path),
            "output_text_path": str(self.output_text_path),
            "frame_count": self.frame_count,
            "camera_count": self.camera_count,
            "matcher": self.matcher,
            "sequential_overlap": self.sequential_overlap,
            "refine_intrinsics": self.refine_intrinsics,
            "camera_pose_policy": "FIX_EXISTING_FRAMES",
            "image_id_policy": "COLMAP_POINT_TRIANGULATOR_TRANSCRIBE_BY_FILENAME",
            "steps": [
                {"command": step.command, "args": list(step.args)}
                for step in self.steps
            ],
        }


def _read_json(path: Path, label: str) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read {label} {path}: {error}") from error
    if not isinstance(payload, dict):
        raise ContractError(f"{label} must contain a JSON object")
    return payload


def _parse_cameras_txt(path: Path) -> dict[int, tuple[int, int, float, float, float, float]]:
    if not path.is_file():
        raise ContractError(f"Missing known-camera COLMAP file: {path}")
    cameras: dict[int, tuple[int, int, float, float, float, float]] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 9:
            raise ContractError(f"Unsupported cameras.txt row: {line}")
        camera_id = int(parts[0])
        if parts[1] != "PINHOLE":
            raise ContractError("Gate 6.3 currently requires PINHOLE cameras")
        values = (
            int(parts[2]),
            int(parts[3]),
            float(parts[4]),
            float(parts[5]),
            float(parts[6]),
            float(parts[7]),
        )
        if camera_id in cameras:
            raise ContractError(f"Duplicate camera id {camera_id} in cameras.txt")
        cameras[camera_id] = values
    if not cameras:
        raise ContractError("Known-camera model contains no cameras")
    return cameras


def _write_camera_group_lists(
    dataset_root: Path,
    frames: list[dict],
    cameras: dict[int, tuple[int, int, float, float, float, float]],
) -> dict[int, Path]:
    group_root = dataset_root / "feature_lists"
    group_root.mkdir(parents=True, exist_ok=True)
    names_by_camera: dict[int, list[str]] = {camera_id: [] for camera_id in cameras}
    for frame in frames:
        camera_id = frame.get("camera_id")
        name = str(frame.get("image_name") or "").strip()
        if type(camera_id) is not int or camera_id not in cameras:
            raise ContractError(f"Frame references unknown camera id: {camera_id!r}")
        if not name:
            raise ContractError("Frame image_name cannot be empty")
        names_by_camera[camera_id].append(name)

    result: dict[int, Path] = {}
    for camera_id, names in sorted(names_by_camera.items()):
        if not names:
            continue
        path = group_root / f"camera_{camera_id:04d}.txt"
        path.write_text("\n".join(names) + "\n", encoding="utf-8")
        result[camera_id] = path
    return result


def _as_arg(value: Path | str | int | float) -> str:
    return str(value)


def build_sparse_plan(
    dataset_root: str | Path,
    *,
    colmap_executable: str = "colmap",
    exhaustive_frame_limit: int = 120,
    sequential_overlap: int = 12,
) -> SparseTriangulationPlan:
    dataset_root = Path(dataset_root).resolve()
    manifest_path = dataset_root / "dataset_manifest.json"
    manifest = _read_json(manifest_path, "dataset manifest")

    if manifest.get("reconstruction_strategy") != "KNOWN_CAMERA_COLMAP_PRIMARY":
        raise ContractError("Gate 6.3 requires the known-camera COLMAP dataset strategy")
    frame_count = manifest.get("frame_count")
    camera_count = manifest.get("camera_count")
    if type(frame_count) is not int or frame_count < 2:
        raise ContractError("Sparse triangulation requires at least two frames")
    if type(camera_count) is not int or camera_count < 1:
        raise ContractError("Sparse triangulation requires at least one camera")
    if type(exhaustive_frame_limit) is not int or exhaustive_frame_limit < 2:
        raise ContractError("exhaustive_frame_limit must be >= 2")
    if type(sequential_overlap) is not int or sequential_overlap < 1:
        raise ContractError("sequential_overlap must be >= 1")

    images_dir = dataset_root / "images"
    known_model = dataset_root / "sparse" / "known"
    if not images_dir.is_dir():
        raise ContractError(f"Missing images directory: {images_dir}")
    if not known_model.is_dir():
        raise ContractError(f"Missing known sparse model: {known_model}")

    frames = manifest.get("frames")
    if not isinstance(frames, list) or len(frames) != frame_count:
        raise ContractError("dataset_manifest frames do not match frame_count")
    cameras = _parse_cameras_txt(known_model / "cameras.txt")
    if len(cameras) != camera_count:
        raise ContractError("dataset_manifest camera_count does not match cameras.txt")
    group_lists = _write_camera_group_lists(dataset_root, frames, cameras)

    database_path = dataset_root / "database.db"
    output_model = dataset_root / "sparse" / "triangulated"
    output_text = dataset_root / "sparse" / "triangulated_txt"

    steps: list[ColmapStep] = []
    for camera_id, list_path in sorted(group_lists.items()):
        width, height, fx, fy, cx, cy = cameras[camera_id]
        del width, height
        steps.append(
            ColmapStep(
                "feature_extractor",
                (
                    "--database_path", _as_arg(database_path),
                    "--image_path", _as_arg(images_dir),
                    "--image_list_path", _as_arg(list_path),
                    "--ImageReader.camera_model", "PINHOLE",
                    "--ImageReader.single_camera", "1",
                    "--ImageReader.camera_params", f"{fx:.17g},{fy:.17g},{cx:.17g},{cy:.17g}",
                    "--FeatureExtraction.use_gpu", "1",
                ),
            )
        )

    if frame_count <= exhaustive_frame_limit:
        matcher = "exhaustive_matcher"
        steps.append(
            ColmapStep(
                matcher,
                (
                    "--database_path", _as_arg(database_path),
                    "--FeatureMatching.use_gpu", "1",
                ),
            )
        )
    else:
        matcher = "sequential_matcher"
        steps.append(
            ColmapStep(
                matcher,
                (
                    "--database_path", _as_arg(database_path),
                    "--SequentialMatching.overlap", str(sequential_overlap),
                    "--SequentialMatching.loop_detection", "0",
                    "--FeatureMatching.use_gpu", "1",
                ),
            )
        )

    steps.append(
        ColmapStep(
            "point_triangulator",
            (
                "--database_path", _as_arg(database_path),
                "--image_path", _as_arg(images_dir),
                "--input_path", _as_arg(known_model),
                "--output_path", _as_arg(output_model),
                "--clear_points", "1",
                "--refine_intrinsics", "0",
            ),
        )
    )
    steps.append(
        ColmapStep(
            "model_converter",
            (
                "--input_path", _as_arg(output_model),
                "--output_path", _as_arg(output_text),
                "--output_type", "TXT",
            ),
        )
    )

    return SparseTriangulationPlan(
        dataset_root=dataset_root,
        database_path=database_path,
        known_model_path=known_model,
        output_model_path=output_model,
        output_text_path=output_text,
        frame_count=frame_count,
        camera_count=camera_count,
        matcher=matcher,
        sequential_overlap=sequential_overlap,
        refine_intrinsics=False,
        steps=tuple(steps),
    )


def _count_text_model_points(path: Path) -> int:
    points_path = path / "points3D.txt"
    if not points_path.is_file():
        return 0
    return sum(
        1
        for line in points_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def _resolve_executable(value: str) -> str:
    value = str(value or "").strip()
    if not value:
        raise ContractError("COLMAP executable cannot be empty")
    path = Path(value)
    if path.parent != Path("."):
        if not path.is_file():
            raise ContractError(f"COLMAP executable does not exist: {path}")
        return str(path)
    return shutil.which(value) or value


def run_sparse_triangulation(
    dataset_root: str | Path,
    *,
    colmap_executable: str = "colmap",
    exhaustive_frame_limit: int = 120,
    sequential_overlap: int = 12,
    overwrite_output: bool = False,
) -> dict[str, object]:
    plan = build_sparse_plan(
        dataset_root,
        colmap_executable=colmap_executable,
        exhaustive_frame_limit=exhaustive_frame_limit,
        sequential_overlap=sequential_overlap,
    )
    executable = _resolve_executable(colmap_executable)

    if plan.output_model_path.exists() and any(plan.output_model_path.iterdir()):
        if not overwrite_output:
            raise ContractError(
                f"Refusing to overwrite completed sparse output: {plan.output_model_path}"
            )
        shutil.rmtree(plan.output_model_path)
    if plan.output_text_path.exists() and any(plan.output_text_path.iterdir()):
        if not overwrite_output:
            raise ContractError(
                f"Refusing to overwrite text sparse output: {plan.output_text_path}"
            )
        shutil.rmtree(plan.output_text_path)

    plan.output_model_path.mkdir(parents=True, exist_ok=True)
    plan.output_text_path.mkdir(parents=True, exist_ok=True)
    log_root = plan.dataset_root / "logs" / "gate6_3"
    log_root.mkdir(parents=True, exist_ok=True)

    executed = []
    for index, step in enumerate(plan.steps):
        argv = list(step.argv(executable))
        result = subprocess.run(
            argv,
            cwd=str(plan.dataset_root),
            capture_output=True,
            text=True,
            check=False,
        )
        log_path = log_root / f"{index:02d}_{step.command}.log"
        log_path.write_text(
            "COMMAND\n" + " ".join(argv)
            + "\n\nSTDOUT\n" + (result.stdout or "")
            + "\n\nSTDERR\n" + (result.stderr or ""),
            encoding="utf-8",
        )
        executed.append({
            "index": index,
            "command": step.command,
            "argv": argv,
            "returncode": int(result.returncode),
            "log_path": str(log_path),
        })
        if result.returncode != 0:
            raise RuntimeError(
                f"COLMAP {step.command} failed with exit code {result.returncode}; "
                f"see {log_path}"
            )

    model_files = {
        name: (plan.output_model_path / name).is_file()
        for name in ("cameras.bin", "images.bin", "points3D.bin")
    }
    if not all(model_files.values()):
        raise ContractError(
            "COLMAP triangulation completed without a complete binary sparse model"
        )
    point_count = _count_text_model_points(plan.output_text_path)

    result_manifest = {
        "schema": "ConceptGhost.P10SparseTriangulationResult.v0.1",
        **plan.manifest(),
        "status": "PASS",
        "colmap_executable": executable,
        "executed": executed,
        "binary_model_files": model_files,
        "sparse_point_count": point_count,
        "sparse_point_cloud_available": point_count > 0,
        "known_camera_pose_refinement": False,
        "known_camera_intrinsics_refinement": False,
    }
    result_path = plan.dataset_root / "sparse_triangulation_manifest.json"
    result_path.write_text(
        json.dumps(result_manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return result_manifest
