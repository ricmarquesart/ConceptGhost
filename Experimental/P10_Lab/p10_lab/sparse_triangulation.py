from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
import json
from pathlib import Path
import math
import shutil
import sqlite3
import struct
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
            "image_id_policy": "DATABASE_IDS_SYNCHRONIZED_BEFORE_TRIANGULATION",
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
        if len(parts) != 8:
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


MAX_COLMAP_IMAGE_ID = 2**31 - 1
PINHOLE_MODEL_ID = 1


@dataclass(frozen=True)
class DatabaseSyncedModel:
    text_path: Path
    binary_path: Path
    diagnostics_path: Path
    selected_image_count: int
    dropped_image_count: int
    verified_pair_count: int
    selected_image_ids: tuple[int, ...]

    def manifest(self) -> dict[str, object]:
        return {
            "text_path": str(self.text_path),
            "binary_path": str(self.binary_path),
            "diagnostics_path": str(self.diagnostics_path),
            "selected_image_count": self.selected_image_count,
            "dropped_image_count": self.dropped_image_count,
            "verified_pair_count": self.verified_pair_count,
            "selected_image_ids": list(self.selected_image_ids),
        }


def _decode_pair_id(pair_id: int) -> tuple[int, int]:
    if type(pair_id) is not int or pair_id <= 0:
        raise ContractError(f"Invalid COLMAP pair_id: {pair_id!r}")
    image_id2 = pair_id % MAX_COLMAP_IMAGE_ID
    image_id1 = (pair_id - image_id2) // MAX_COLMAP_IMAGE_ID
    if image_id1 <= 0 or image_id2 <= 0:
        raise ContractError(f"Invalid COLMAP image ids decoded from pair_id {pair_id}")
    return int(image_id1), int(image_id2)


def _largest_connected_component(
    image_ids: set[int],
    edges: list[tuple[int, int]],
) -> tuple[int, ...]:
    adjacency = {image_id: set() for image_id in image_ids}
    for a, b in edges:
        if a in adjacency and b in adjacency and a != b:
            adjacency[a].add(b)
            adjacency[b].add(a)

    visited: set[int] = set()
    components: list[tuple[int, ...]] = []
    for start in sorted(image_ids):
        if start in visited or not adjacency[start]:
            continue
        stack = [start]
        component: list[int] = []
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component.append(current)
            stack.extend(sorted(adjacency[current] - visited, reverse=True))
        if component:
            components.append(tuple(sorted(component)))

    if not components:
        return ()
    components.sort(key=lambda component: (-len(component), component))
    return components[0]


def _read_database_camera_params(
    connection: sqlite3.Connection,
) -> dict[int, tuple[int, int, int, tuple[float, ...]]]:
    cameras: dict[int, tuple[int, int, int, tuple[float, ...]]] = {}
    for camera_id, model, width, height, params_blob in connection.execute(
        "SELECT camera_id, model, width, height, params FROM cameras"
    ):
        if params_blob is None or len(params_blob) % 8 != 0:
            raise ContractError(f"Invalid COLMAP camera parameter blob for camera {camera_id}")
        params = struct.unpack("<" + "d" * (len(params_blob) // 8), params_blob)
        cameras[int(camera_id)] = (
            int(model),
            int(width),
            int(height),
            tuple(float(value) for value in params),
        )
    return cameras


def _intrinsics_close(
    expected: tuple[int, int, float, float, float, float],
    actual: tuple[int, int, int, tuple[float, ...]],
) -> bool:
    width, height, fx, fy, cx, cy = expected
    model, db_width, db_height, params = actual
    if model != PINHOLE_MODEL_ID or db_width != width or db_height != height:
        return False
    if len(params) != 4:
        return False
    target = (fx, fy, cx, cy)
    return all(
        math.isfinite(value)
        and math.isclose(value, reference, rel_tol=1e-9, abs_tol=1e-6)
        for value, reference in zip(params, target)
    )


def _write_database_synced_model(plan: SparseTriangulationPlan) -> DatabaseSyncedModel:
    """Synchronize known poses with COLMAP's actual database identities.

    Feature extraction can assign image/camera/rig/frame identifiers in a
    different order than ConceptGhost's pre-authored known-camera text model,
    especially because extraction is grouped by intrinsics. COLMAP 4.2 also
    represents images through rigs/frames. Before point_triangulator runs we
    therefore rebuild the known model using the exact database-assigned
    image/camera/rig/frame ids while preserving the authoritative P9 qvec/tvec
    and intrinsics. Only the largest verified-match component is triangulated,
    so disconnected or featureless generated views cannot crash the native
    triangulator.
    """

    manifest = _read_json(plan.dataset_root / "dataset_manifest.json", "dataset manifest")
    frames = manifest.get("frames")
    if not isinstance(frames, list) or len(frames) != plan.frame_count:
        raise ContractError("dataset_manifest frames do not match sparse plan")

    known_cameras = _parse_cameras_txt(plan.known_model_path / "cameras.txt")
    if not plan.database_path.is_file():
        raise ContractError(f"COLMAP database does not exist: {plan.database_path}")

    with closing(sqlite3.connect(str(plan.database_path))) as connection:
        db_images_rows = connection.execute(
            "SELECT image_id, name, camera_id FROM images"
        ).fetchall()
        db_images_by_name = {
            str(name): (int(image_id), int(camera_id))
            for image_id, name, camera_id in db_images_rows
        }
        if len(db_images_by_name) != len(db_images_rows):
            raise ContractError("COLMAP database contains duplicate image names")

        db_frame_rows = connection.execute(
            """
            SELECT
                i.image_id,
                i.camera_id,
                fd.frame_id,
                f.rig_id,
                fd.sensor_id,
                fd.sensor_type,
                r.ref_sensor_id,
                r.ref_sensor_type
            FROM images AS i
            JOIN frame_data AS fd
              ON fd.data_id = i.image_id
             AND fd.sensor_id = i.camera_id
            JOIN frames AS f
              ON f.frame_id = fd.frame_id
            JOIN rigs AS r
              ON r.rig_id = f.rig_id
            """
        ).fetchall()
        db_frame_by_image: dict[int, tuple[int, int, int, int, int, int]] = {}
        for (
            image_id,
            camera_id,
            frame_id,
            rig_id,
            sensor_id,
            sensor_type,
            ref_sensor_id,
            ref_sensor_type,
        ) in db_frame_rows:
            image_id = int(image_id)
            row = (
                int(camera_id),
                int(frame_id),
                int(rig_id),
                int(sensor_id),
                int(sensor_type),
                int(ref_sensor_type),
            )
            if int(ref_sensor_id) != int(camera_id):
                raise ContractError(
                    f"COLMAP database image {image_id} is not attached to a trivial "
                    "camera-reference rig"
                )
            if image_id in db_frame_by_image:
                raise ContractError(
                    f"COLMAP database image {image_id} maps to multiple frames"
                )
            db_frame_by_image[image_id] = row

        nontrivial_rig_sensor_counts = {
            int(rig_id): int(count)
            for rig_id, count in connection.execute(
                "SELECT rig_id, COUNT(*) FROM rig_sensors GROUP BY rig_id"
            ).fetchall()
        }

        db_cameras = _read_database_camera_params(connection)
        keypoint_rows = {
            int(image_id): int(rows)
            for image_id, rows in connection.execute(
                "SELECT image_id, rows FROM keypoints"
            ).fetchall()
        }
        descriptor_rows = {
            int(image_id): int(rows)
            for image_id, rows in connection.execute(
                "SELECT image_id, rows FROM descriptors"
            ).fetchall()
        }
        geometry_rows = connection.execute(
            "SELECT pair_id, rows, config FROM two_view_geometries"
        ).fetchall()

    frame_by_db_id: dict[int, dict] = {}
    original_camera_by_db_camera: dict[int, int] = {}
    missing_names: list[str] = []
    intrinsic_mismatches: list[dict[str, object]] = []

    for frame in frames:
        name = str(frame.get("image_name") or "").strip()
        original_camera_id = frame.get("camera_id")
        if not name:
            raise ContractError("dataset_manifest frame image_name cannot be empty")
        if type(original_camera_id) is not int or original_camera_id not in known_cameras:
            raise ContractError(
                f"dataset_manifest frame {name} references unknown camera {original_camera_id!r}"
            )
        row = db_images_by_name.get(name)
        if row is None:
            missing_names.append(name)
            continue

        db_image_id, db_camera_id = row
        if db_image_id in frame_by_db_id:
            raise ContractError(f"Duplicate database image id {db_image_id} for Gate 6 frame set")
        frame_by_db_id[db_image_id] = frame

        expected_intrinsics = known_cameras[original_camera_id]
        actual_intrinsics = db_cameras.get(db_camera_id)
        if actual_intrinsics is None or not _intrinsics_close(expected_intrinsics, actual_intrinsics):
            intrinsic_mismatches.append({
                "image_name": name,
                "db_image_id": db_image_id,
                "db_camera_id": db_camera_id,
                "source_camera_id": original_camera_id,
            })
            continue

        prior = original_camera_by_db_camera.get(db_camera_id)
        if prior is None:
            original_camera_by_db_camera[db_camera_id] = original_camera_id
        elif known_cameras[prior] != expected_intrinsics:
            raise ContractError(
                f"Database camera {db_camera_id} maps to inconsistent ConceptGhost intrinsics"
            )

    if missing_names:
        preview = ", ".join(missing_names[:5])
        raise ContractError(
            f"COLMAP database is missing {len(missing_names)} dataset images: {preview}"
        )
    if intrinsic_mismatches:
        raise ContractError(
            "COLMAP database camera parameters diverged from authoritative Gate 6 intrinsics: "
            + json.dumps(intrinsic_mismatches[:5], sort_keys=True)
        )

    dataset_ids = set(frame_by_db_id)
    verified_edges: list[tuple[int, int]] = []
    verified_pairs_detail: list[dict[str, int]] = []
    for pair_id, rows, config in geometry_rows:
        rows = int(rows)
        config = int(config)
        if rows <= 0 or config == 0:
            continue
        image_id1, image_id2 = _decode_pair_id(int(pair_id))
        if image_id1 in dataset_ids and image_id2 in dataset_ids:
            verified_edges.append((image_id1, image_id2))
            verified_pairs_detail.append({
                "image_id1": image_id1,
                "image_id2": image_id2,
                "rows": rows,
                "config": config,
            })

    feature_ready_ids = {
        image_id
        for image_id in dataset_ids
        if keypoint_rows.get(image_id, 0) > 0 and descriptor_rows.get(image_id, 0) > 0
    }
    selected = _largest_connected_component(feature_ready_ids, verified_edges)
    if len(selected) < 2:
        raise ContractError(
            "COLMAP matching produced no triangulatable connected component with at least "
            "two feature-bearing images. Inspect logs/gate6_3 and the generated "
            "database_alignment.json diagnostics."
        )

    selected_set = set(selected)
    selected_frames = [
        (image_id, frame_by_db_id[image_id])
        for image_id in sorted(selected)
    ]
    used_db_cameras = sorted(
        {db_images_by_name[str(frame["image_name"])][1] for _, frame in selected_frames}
    )

    text_root = plan.dataset_root / "sparse" / "known_db_synced"
    binary_root = plan.dataset_root / "sparse" / "known_db_synced_bin"
    diagnostics_path = plan.dataset_root / "database_alignment.json"
    if text_root.exists():
        shutil.rmtree(text_root)
    if binary_root.exists():
        shutil.rmtree(binary_root)
    text_root.mkdir(parents=True, exist_ok=True)
    binary_root.mkdir(parents=True, exist_ok=True)

    camera_lines = []
    for db_camera_id in used_db_cameras:
        source_camera_id = original_camera_by_db_camera[db_camera_id]
        width, height, fx, fy, cx, cy = known_cameras[source_camera_id]
        camera_lines.append(
            f"{db_camera_id} PINHOLE {width} {height} "
            f"{fx:.17g} {fy:.17g} {cx:.17g} {cy:.17g}"
        )

    selected_db_rigs: dict[int, int] = {}
    for db_image_id, frame in selected_frames:
        name = str(frame["image_name"])
        db_camera_id = db_images_by_name[name][1]
        frame_row = db_frame_by_image.get(db_image_id)
        if frame_row is None:
            raise ContractError(
                f"COLMAP database image {db_image_id} has no camera frame/rig assignment"
            )
        (
            frame_camera_id,
            _db_frame_id,
            db_rig_id,
            sensor_id,
            sensor_type,
            ref_sensor_type,
        ) = frame_row
        if frame_camera_id != db_camera_id or sensor_id != db_camera_id:
            raise ContractError(
                f"COLMAP database frame assignment for image {db_image_id} "
                "does not match its camera"
            )
        if sensor_type != ref_sensor_type:
            raise ContractError(
                f"COLMAP database frame assignment for image {db_image_id} "
                "has inconsistent sensor types"
            )
        if nontrivial_rig_sensor_counts.get(db_rig_id, 0) != 0:
            raise ContractError(
                "Gate 6 known-camera reconstruction expects the fresh COLMAP database "
                f"to use trivial one-camera rigs; rig {db_rig_id} is non-trivial"
            )
        prior_camera = selected_db_rigs.get(db_rig_id)
        if prior_camera is None:
            selected_db_rigs[db_rig_id] = db_camera_id
        elif prior_camera != db_camera_id:
            raise ContractError(
                f"COLMAP database rig {db_rig_id} references multiple cameras"
            )

    rig_lines = [
        f"{db_rig_id} 1 CAMERA {db_camera_id}"
        for db_rig_id, db_camera_id in sorted(selected_db_rigs.items())
    ]

    image_lines = []
    frame_lines = []
    for db_image_id, frame in selected_frames:
        name = str(frame["image_name"])
        db_camera_id = db_images_by_name[name][1]
        (
            _frame_camera_id,
            db_frame_id,
            db_rig_id,
            _sensor_id,
            _sensor_type,
            _ref_sensor_type,
        ) = db_frame_by_image[db_image_id]
        qvec = frame.get("qvec")
        tvec = frame.get("tvec")
        if (
            not isinstance(qvec, list)
            or len(qvec) != 4
            or not isinstance(tvec, list)
            or len(tvec) != 3
        ):
            raise ContractError(f"dataset_manifest frame {name} is missing qvec/tvec")
        pose = [float(v) for v in (*qvec, *tvec)]
        if not all(math.isfinite(v) for v in pose):
            raise ContractError(f"dataset_manifest frame {name} contains non-finite pose")
        pose_text = " ".join(f"{v:.17g}" for v in pose)
        image_lines.append(
            f"{db_image_id} {pose_text} {db_camera_id} {name}\n"
        )
        frame_lines.append(
            f"{db_frame_id} {db_rig_id} {pose_text} "
            f"1 CAMERA {db_camera_id} {db_image_id}"
        )

    (text_root / "cameras.txt").write_text(
        "# Camera list with one line of data per camera:\n"
        "#   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n"
        f"# Number of cameras: {len(camera_lines)}\n"
        + "\n".join(camera_lines)
        + "\n",
        encoding="utf-8",
    )
    (text_root / "images.txt").write_text(
        "# Image list with two lines of data per image:\n"
        "#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n"
        "#   POINTS2D[] as (X, Y, POINT3D_ID)\n"
        f"# Number of images: {len(image_lines)}\n"
        + "".join(line + "\n" for line in image_lines),
        encoding="utf-8",
    )
    (text_root / "points3D.txt").write_text(
        "# 3D point list with one line of data per point:\n"
        "#   POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[]\n"
        "# Number of points: 0\n",
        encoding="utf-8",
    )
    (text_root / "rigs.txt").write_text(
        "# Rig calib list with one line of data per calib:\n"
        "#   RIG_ID, NUM_SENSORS, REF_SENSOR_TYPE, REF_SENSOR_ID, SENSORS[]\n"
        f"# Number of rigs: {len(rig_lines)}\n"
        + "\n".join(rig_lines)
        + "\n",
        encoding="utf-8",
    )
    (text_root / "frames.txt").write_text(
        "# Frame list with one line of data per frame:\n"
        "#   FRAME_ID, RIG_ID, RIG_FROM_WORLD[QW,QX,QY,QZ,TX,TY,TZ], "
        "NUM_DATA_IDS, DATA_IDS[]\n"
        f"# Number of frames: {len(frame_lines)}\n"
        + "\n".join(frame_lines)
        + "\n",
        encoding="utf-8",
    )

    dropped = sorted(dataset_ids - selected_set)
    diagnostics = {
        "schema": "ConceptGhost.P10ColmapDatabaseAlignment.v0.2",
        "status": "PASS",
        "dataset_frame_count": len(dataset_ids),
        "database_image_count": len(db_images_by_name),
        "feature_ready_count": len(feature_ready_ids),
        "verified_pair_count": len(verified_edges),
        "selected_component_count": len(selected),
        "dropped_image_count": len(dropped),
        "selected_image_ids": list(selected),
        "dropped_image_ids": dropped,
        "selected_image_names": [
            str(frame_by_db_id[image_id]["image_name"]) for image_id in selected
        ],
        "dropped_image_names": [
            str(frame_by_db_id[image_id]["image_name"]) for image_id in dropped
        ],
        "camera_id_policy": "DATABASE_ASSIGNED_IDS_WITH_AUTHORITATIVE_P9_INTRINSICS",
        "image_id_policy": "DATABASE_ASSIGNED_IDS_WITH_AUTHORITATIVE_P9_POSES",
        "component_policy": "LARGEST_VERIFIED_MATCH_COMPONENT",
        "rig_frame_policy": "DATABASE_ASSIGNED_TRIVIAL_RIG_AND_FRAME_IDS",
        "verified_pairs": verified_pairs_detail,
        "known_text_model": str(text_root),
        "known_binary_model": str(binary_root),
    }
    diagnostics_path.write_text(
        json.dumps(diagnostics, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return DatabaseSyncedModel(
        text_path=text_root,
        binary_path=binary_root,
        diagnostics_path=diagnostics_path,
        selected_image_count=len(selected),
        dropped_image_count=len(dropped),
        verified_pair_count=len(verified_edges),
        selected_image_ids=tuple(selected),
    )


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
    synchronized_model: DatabaseSyncedModel | None = None

    def execute_colmap(index: int, command: str, argv: list[str], log_name: str) -> None:
        result = subprocess.run(
            argv,
            cwd=str(plan.dataset_root),
            capture_output=True,
            text=True,
            check=False,
        )
        log_path = log_root / log_name
        log_path.write_text(
            "COMMAND\n" + " ".join(argv)
            + "\n\nSTDOUT\n" + (result.stdout or "")
            + "\n\nSTDERR\n" + (result.stderr or ""),
            encoding="utf-8",
        )
        executed.append({
            "index": index,
            "command": command,
            "argv": argv,
            "returncode": int(result.returncode),
            "log_path": str(log_path),
        })
        if result.returncode != 0:
            raise RuntimeError(
                f"COLMAP {command} failed with exit code {result.returncode}; "
                f"see {log_path}"
            )

    for index, step in enumerate(plan.steps):
        argv = list(step.argv(executable))

        if step.command == "point_triangulator":
            synchronized_model = _write_database_synced_model(plan)

            converter_argv = [
                executable,
                "model_converter",
                "--input_path", str(synchronized_model.text_path),
                "--output_path", str(synchronized_model.binary_path),
                "--output_type", "BIN",
            ]
            execute_colmap(
                index,
                "model_converter_known_db_synced",
                converter_argv,
                f"{index:02d}_model_converter_known_db_synced.log",
            )

            try:
                input_index = argv.index("--input_path") + 1
            except ValueError as error:
                raise ContractError("point_triangulator plan is missing --input_path") from error
            argv[input_index] = str(synchronized_model.binary_path)

        execute_colmap(index, step.command, argv, f"{index:02d}_{step.command}.log")

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
        "database_synchronized_model": (
            synchronized_model.manifest() if synchronized_model is not None else None
        ),
    }
    result_path = plan.dataset_root / "sparse_triangulation_manifest.json"
    result_path.write_text(
        json.dumps(result_manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return result_manifest
