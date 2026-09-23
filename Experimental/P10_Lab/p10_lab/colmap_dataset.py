from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path

from .contracts import ContractError
from .reconstruction_inputs import build_reconstruction_input_manifest


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _finite_matrix4(value) -> tuple[tuple[float, float, float, float], ...]:
    try:
        rows = tuple(tuple(float(v) for v in row) for row in value)
    except Exception as error:
        raise ContractError("world_matrix must be a numeric 4x4 matrix") from error
    if len(rows) != 4 or any(len(row) != 4 for row in rows):
        raise ContractError("world_matrix must be 4x4")
    if not all(math.isfinite(v) for row in rows for v in row):
        raise ContractError("world_matrix must be finite")
    if any(abs(rows[3][i] - expected) > 1e-6 for i, expected in enumerate((0.0, 0.0, 0.0, 1.0))):
        raise ContractError("world_matrix must be affine")
    return rows


def _mat3_transpose(m):
    return (
        (m[0][0], m[1][0], m[2][0]),
        (m[0][1], m[1][1], m[2][1]),
        (m[0][2], m[1][2], m[2][2]),
    )


def _mat3_mul(a, b):
    return tuple(
        tuple(
            sum(a[r][k] * b[k][c] for k in range(3))
            for c in range(3)
        )
        for r in range(3)
    )


def _mat3_vec_mul(m, v):
    return tuple(
        sum(m[r][k] * v[k] for k in range(3))
        for r in range(3)
    )


def _rotation_to_qvec(rotation) -> tuple[float, float, float, float]:
    """Return COLMAP quaternion order (qw, qx, qy, qz)."""

    r = rotation
    trace = r[0][0] + r[1][1] + r[2][2]
    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        qw = 0.25 * s
        qx = (r[2][1] - r[1][2]) / s
        qy = (r[0][2] - r[2][0]) / s
        qz = (r[1][0] - r[0][1]) / s
    elif r[0][0] > r[1][1] and r[0][0] > r[2][2]:
        s = math.sqrt(1.0 + r[0][0] - r[1][1] - r[2][2]) * 2.0
        qw = (r[2][1] - r[1][2]) / s
        qx = 0.25 * s
        qy = (r[0][1] + r[1][0]) / s
        qz = (r[0][2] + r[2][0]) / s
    elif r[1][1] > r[2][2]:
        s = math.sqrt(1.0 + r[1][1] - r[0][0] - r[2][2]) * 2.0
        qw = (r[0][2] - r[2][0]) / s
        qx = (r[0][1] + r[1][0]) / s
        qy = 0.25 * s
        qz = (r[1][2] + r[2][1]) / s
    else:
        s = math.sqrt(1.0 + r[2][2] - r[0][0] - r[1][1]) * 2.0
        qw = (r[1][0] - r[0][1]) / s
        qx = (r[0][2] + r[2][0]) / s
        qy = (r[1][2] + r[2][1]) / s
        qz = 0.25 * s

    norm = math.sqrt(qw * qw + qx * qx + qy * qy + qz * qz)
    if not math.isfinite(norm) or norm <= 1e-12:
        raise ContractError("Cannot convert camera rotation to a valid quaternion")
    qvec = (qw / norm, qx / norm, qy / norm, qz / norm)
    if qvec[0] < 0.0:
        qvec = tuple(-v for v in qvec)
    return qvec


def world_matrix_to_colmap_pose(world_matrix):
    """Convert ConceptGhost/Maya camera-to-world to COLMAP world-to-camera pose.

    ConceptGhost/Maya local camera axes:
      +X right, +Y up, -Z forward.
    COLMAP camera axes:
      +X right, +Y down, +Z forward.

    The local-axis conversion is therefore diag(+1,-1,-1).
    """

    world = _finite_matrix4(world_matrix)
    rotation_c2w = tuple(tuple(world[r][c] for c in range(3)) for r in range(3))
    center = (world[0][3], world[1][3], world[2][3])

    rotation_w2maya = _mat3_transpose(rotation_c2w)
    maya_to_colmap = (
        (1.0, 0.0, 0.0),
        (0.0, -1.0, 0.0),
        (0.0, 0.0, -1.0),
    )
    rotation_w2colmap = _mat3_mul(maya_to_colmap, rotation_w2maya)
    rotated_center = _mat3_vec_mul(rotation_w2colmap, center)
    tvec = tuple(-v for v in rotated_center)
    qvec = _rotation_to_qvec(rotation_w2colmap)
    return qvec, tvec


def _camera_key(camera: dict) -> tuple:
    if camera.get("model") != "PINHOLE":
        raise ContractError("Gate 6.2 currently requires PINHOLE cameras")
    values = (
        camera.get("width"),
        camera.get("height"),
        camera.get("fx"),
        camera.get("fy"),
        camera.get("cx"),
        camera.get("cy"),
    )
    if type(values[0]) is not int or type(values[1]) is not int:
        raise ContractError("Camera width/height must be integers")
    if values[0] <= 0 or values[1] <= 0:
        raise ContractError("Camera width/height must be positive")
    normalized = [values[0], values[1]]
    for value in values[2:]:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ContractError("Camera intrinsics must be finite")
        normalized.append(float(value))
    if normalized[2] <= 0.0 or normalized[3] <= 0.0:
        raise ContractError("Camera fx/fy must be positive")
    return tuple(normalized)


def _fmt(value: float) -> str:
    return f"{float(value):.17g}"


def prepare_known_camera_colmap_dataset(
    wan_manifest_path: str | Path,
    camera_manifest_path: str | Path,
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, object]:
    """Materialize source-preserved P10 frames as a known-camera COLMAP dataset.

    This dataset is the primary Gate 6 path because ConceptGhost already knows
    every virtual-camera pose. SphereSfM remains an optional validation/fallback
    for future ERP-specific workflows, not the authoritative pose solver here.
    """

    output_dir = Path(output_dir).resolve()
    if output_dir.exists():
        if any(output_dir.iterdir()):
            if not overwrite:
                raise ContractError(
                    f"Refusing to overwrite non-empty reconstruction dataset: {output_dir}"
                )
            shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    reconstruction = build_reconstruction_input_manifest(
        wan_manifest_path,
        camera_manifest_path,
    )
    scene_contract_id = str(reconstruction.get("scene_contract_id") or "").strip()
    if not scene_contract_id:
        raise ContractError("Gate 6.2 requires a nonempty Scene Contract ID")

    images_dir = output_dir / "images"
    sparse_dir = output_dir / "sparse" / "known"
    images_dir.mkdir(parents=True, exist_ok=True)
    sparse_dir.mkdir(parents=True, exist_ok=True)

    camera_id_by_key: dict[tuple, int] = {}
    camera_rows = []
    image_rows = []
    materialized_frames = []

    for image_id, frame in enumerate(reconstruction["frames"], start=1):
        global_index = frame["global_frame_index"]
        source_path = Path(frame["image_path"]).resolve()
        if not source_path.is_file():
            raise ContractError(f"Missing reconstruction source image: {source_path}")

        image_name = f"frame_{global_index:06d}{source_path.suffix.lower() or '.png'}"
        destination = images_dir / image_name
        shutil.copy2(source_path, destination)

        camera = frame["camera"]
        key = _camera_key(camera)
        camera_id = camera_id_by_key.get(key)
        if camera_id is None:
            camera_id = len(camera_id_by_key) + 1
            camera_id_by_key[key] = camera_id
            width, height, fx, fy, cx, cy = key
            camera_rows.append(
                f"{camera_id} PINHOLE {width} {height} "
                f"{_fmt(fx)} {_fmt(fy)} {_fmt(cx)} {_fmt(cy)}"
            )

        qvec, tvec = world_matrix_to_colmap_pose(camera["world_matrix"])
        pose_numbers = " ".join(_fmt(value) for value in (*qvec, *tvec))
        image_rows.append(
            f"{image_id} {pose_numbers} {camera_id} {image_name}\n"
        )

        materialized_frames.append({
            "image_id": image_id,
            "camera_id": camera_id,
            "global_frame_index": global_index,
            "path_name": frame["path_name"],
            "path_frame_index": frame["path_frame_index"],
            "image_name": image_name,
            "source_image_path": str(source_path),
            "materialized_image_path": str(destination),
            "image_provenance": frame["image_provenance"],
            "camera_authority": frame["camera_authority"],
            "qvec": list(qvec),
            "tvec": list(tvec),
        })

    cameras_txt = (
        "# Camera list with one line of data per camera:\n"
        "#   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n"
        f"# Number of cameras: {len(camera_rows)}\n"
        + "\n".join(camera_rows)
        + "\n"
    )
    images_txt = (
        "# Image list with two lines of data per image:\n"
        "#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n"
        "#   POINTS2D[] as (X, Y, POINT3D_ID)\n"
        f"# Number of images: {len(image_rows)}\n"
        + "".join(row + "\n" for row in image_rows)
    )
    points_txt = (
        "# 3D point list with one line of data per point:\n"
        "#   POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[]\n"
        "# Number of points: 0\n"
    )

    (sparse_dir / "cameras.txt").write_text(cameras_txt, encoding="utf-8")
    (sparse_dir / "images.txt").write_text(images_txt, encoding="utf-8")
    (sparse_dir / "points3D.txt").write_text(points_txt, encoding="utf-8")

    reconstruction_path = output_dir / "reconstruction_inputs.json"
    reconstruction_path.write_text(
        json.dumps(reconstruction, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    dataset_manifest = {
        "schema": "ConceptGhost.P10KnownCameraColmapDataset.v0.2",
        "run_id": reconstruction.get("run_id"),
        "scene_contract_id": scene_contract_id,
        "frame_count": len(materialized_frames),
        "camera_count": len(camera_rows),
        "reconstruction_strategy": "KNOWN_CAMERA_COLMAP_PRIMARY",
        "camera_authority": "P9_BASELINE_WORLD_DERIVED",
        "image_authority": "SOURCE_PRESERVED_P10_COMPOSITE",
        "route_authority": reconstruction.get("route_authority"),
        "route_plan_sha256": reconstruction.get("route_plan_sha256"),
        "mission_order": reconstruction.get("mission_order"),
        "mission_modes": reconstruction.get("mission_modes"),
        "camera_image_mapping_policy": reconstruction.get("camera_image_mapping_policy"),
        "composite_dimensions": reconstruction.get("composite_dimensions"),
        "source_inputs": {
            "wan_manifest_path": str(Path(wan_manifest_path).resolve()),
            "wan_manifest_sha256": _sha256_file(Path(wan_manifest_path).resolve()),
            "camera_manifest_path": str(Path(camera_manifest_path).resolve()),
            "camera_manifest_sha256": _sha256_file(Path(camera_manifest_path).resolve()),
        },
        "coordinate_conversion": {
            "source": "CONCEPTGHOST_MAYA_CAMERA_C2W_XRIGHT_YUP_MINUSZ_FORWARD",
            "target": "COLMAP_W2C_XRIGHT_YDOWN_ZFORWARD",
            "axis_transform": "diag(1,-1,-1)",
        },
        "spheresfm_role": "OPTIONAL_ERP_VALIDATION_NOT_PRIMARY_POSE_SOLVER",
        "spheresfm_reason": (
            "Gate 5 outputs are perspective virtual-camera composites with known "
            "P9-derived poses; SphereSfM's spherical-camera pose estimation is not "
            "authoritative for this path."
        ),
        "images_dir": str(images_dir),
        "known_sparse_model_dir": str(sparse_dir),
        "frames": materialized_frames,
    }
    manifest_path = output_dir / "dataset_manifest.json"
    manifest_path.write_text(
        json.dumps(dataset_manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return dataset_manifest
