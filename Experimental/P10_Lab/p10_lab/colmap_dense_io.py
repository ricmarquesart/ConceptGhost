from __future__ import annotations

import math
import struct
from pathlib import Path
from typing import Iterable

from .contracts import ContractError


def _lazy_numpy():
    try:
        import numpy as np
    except ImportError as error:
        raise ContractError("COLMAP dense evidence reading requires NumPy") from error
    return np


def _read_mixed_header(stream, label: str) -> tuple[int, int, int]:
    values = []
    token = bytearray()
    while len(values) < 3:
        raw = stream.read(1)
        if not raw:
            raise ContractError(f"Unexpected EOF while reading {label} header")
        if raw == b"&":
            if not token:
                raise ContractError(f"Malformed {label} header")
            try:
                values.append(int(token.decode("ascii")))
            except ValueError as error:
                raise ContractError(f"Malformed {label} header integer") from error
            token.clear()
        else:
            token.extend(raw)
            if len(token) > 32:
                raise ContractError(f"Malformed {label} header")
    width, height, channels = values
    if width <= 0 or height <= 0 or channels <= 0:
        raise ContractError(f"{label} header dimensions must be positive")
    return width, height, channels


def read_colmap_float_map(
    path: str | Path,
    *,
    expected_channels: int | None = None,
):
    """Read COLMAP mixed text/binary depth or normal maps.

    COLMAP stores width&height&channels& followed by little-endian float32 data.
    The serialized array follows COLMAP's documented dense-map convention and
    is returned as [H,W] for one channel or [H,W,C] otherwise.
    """

    np = _lazy_numpy()
    path = Path(path).resolve()
    if not path.is_file():
        raise ContractError(f"COLMAP dense map does not exist: {path}")
    with path.open("rb") as stream:
        width, height, channels = _read_mixed_header(stream, path.name)
        if expected_channels is not None and channels != int(expected_channels):
            raise ContractError(
                f"{path.name} channels mismatch: expected {expected_channels}, got {channels}"
            )
        raw = stream.read()
    expected = width * height * channels
    values = np.frombuffer(raw, dtype="<f4")
    if values.size != expected:
        raise ContractError(
            f"{path.name} payload size mismatch: expected {expected} float32 values, got {values.size}"
        )
    # This is equivalent to COLMAP's historical read_dense.py helper.
    array = values.reshape((width, height, channels), order="F").transpose(1, 0, 2)
    if channels == 1:
        return array[:, :, 0].copy()
    return array.copy()


def read_colmap_consistency_graph(
    path: str | Path,
    *,
    selected_pixels: Iterable[tuple[int, int]] | None = None,
    max_source_index: int | None = None,
) -> tuple[tuple[int, int, int], dict[tuple[int, int], tuple[int, ...]]]:
    """Read selected records from a COLMAP consistency graph.

    The binary records are <row><col><N><image_idx...>, int32 little-endian.
    image_idx values are zero-based positions in dense sparse/images.txt.
    """

    path = Path(path).resolve()
    if not path.is_file():
        raise ContractError(f"COLMAP consistency graph does not exist: {path}")
    wanted = set(selected_pixels) if selected_pixels is not None else None
    with path.open("rb") as stream:
        width, height, channels = _read_mixed_header(stream, path.name)
        raw = stream.read()
    if len(raw) % 4:
        raise ContractError(f"{path.name} consistency payload is not int32 aligned")
    count = len(raw) // 4
    values = struct.unpack("<" + "i" * count, raw) if count else ()
    offset = 0
    records: dict[tuple[int, int], tuple[int, ...]] = {}
    while offset < count:
        if offset + 3 > count:
            raise ContractError(f"{path.name} truncated consistency record")
        row, col, n = values[offset : offset + 3]
        offset += 3
        if row < 0 or row >= height or col < 0 or col >= width or n < 0:
            raise ContractError(f"{path.name} contains invalid consistency record")
        if offset + n > count:
            raise ContractError(f"{path.name} truncated source-image list")
        sources = tuple(int(v) for v in values[offset : offset + n])
        offset += n
        if max_source_index is not None and any(
            source < 0 or source > max_source_index for source in sources
        ):
            raise ContractError(f"{path.name} contains out-of-range source image index")
        key = (int(row), int(col))
        if wanted is None or key in wanted:
            records[key] = sources
    return (width, height, channels), records


def parse_colmap_cameras_txt(path: str | Path) -> dict[int, dict[str, float | int | str]]:
    path = Path(path).resolve()
    if not path.is_file():
        raise ContractError(f"COLMAP cameras.txt does not exist: {path}")
    result = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 8:
            raise ContractError(f"Unsupported cameras.txt row: {line}")
        camera_id = int(parts[0])
        model = parts[1]
        if model != "PINHOLE":
            raise ContractError(f"Free-space evidence currently requires PINHOLE, got {model}")
        width, height = int(parts[2]), int(parts[3])
        fx, fy, cx, cy = (float(v) for v in parts[4:8])
        if camera_id <= 0 or width <= 0 or height <= 0:
            raise ContractError("Invalid COLMAP camera row")
        if not all(math.isfinite(v) for v in (fx, fy, cx, cy)) or fx <= 0 or fy <= 0:
            raise ContractError("Invalid COLMAP PINHOLE intrinsics")
        result[camera_id] = {
            "camera_id": camera_id,
            "model": model,
            "width": width,
            "height": height,
            "fx": fx,
            "fy": fy,
            "cx": cx,
            "cy": cy,
        }
    if not result:
        raise ContractError("COLMAP cameras.txt contains no cameras")
    return result


def parse_colmap_images_txt(path: str | Path) -> tuple[dict[str, object], ...]:
    """Parse image pose rows while ignoring POINTS2D rows."""

    path = Path(path).resolve()
    if not path.is_file():
        raise ContractError(f"COLMAP images.txt does not exist: {path}")
    rows = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 10:
            continue
        try:
            image_id = int(parts[0])
            qvec = tuple(float(v) for v in parts[1:5])
            tvec = tuple(float(v) for v in parts[5:8])
            camera_id = int(parts[8])
        except ValueError:
            continue
        name = parts[9]
        if image_id <= 0 or camera_id <= 0:
            raise ContractError(f"Invalid COLMAP image row: {line}")
        if not all(math.isfinite(v) for v in (*qvec, *tvec)):
            raise ContractError(f"Non-finite COLMAP image pose: {name}")
        rows.append(
            {
                "image_id": image_id,
                "qvec": qvec,
                "tvec": tvec,
                "camera_id": camera_id,
                "name": name,
            }
        )
    if not rows:
        raise ContractError("COLMAP images.txt contains no image pose rows")
    return tuple(rows)



_COLMAP_CAMERA_MODELS = {
    0: ("SIMPLE_PINHOLE", 3),
    1: ("PINHOLE", 4),
    2: ("SIMPLE_RADIAL", 4),
    3: ("RADIAL", 5),
    4: ("OPENCV", 8),
    5: ("OPENCV_FISHEYE", 8),
    6: ("FULL_OPENCV", 12),
    7: ("FOV", 5),
    8: ("SIMPLE_RADIAL_FISHEYE", 4),
    9: ("RADIAL_FISHEYE", 5),
    10: ("THIN_PRISM_FISHEYE", 12),
}


def _read_exact(stream, size: int, label: str) -> bytes:
    raw = stream.read(size)
    if len(raw) != size:
        raise ContractError(f"Unexpected EOF while reading {label}")
    return raw


def parse_colmap_cameras_bin(path: str | Path) -> dict[int, dict[str, float | int | str]]:
    """Parse COLMAP cameras.bin.

    Dense image_undistorter workspaces commonly keep sparse camera models in
    binary form even though Gate 7 only needs the undistorted PINHOLE model.
    """

    path = Path(path).resolve()
    if not path.is_file():
        raise ContractError(f"COLMAP cameras.bin does not exist: {path}")
    result = {}
    with path.open("rb") as stream:
        (count,) = struct.unpack("<Q", _read_exact(stream, 8, "cameras.bin count"))
        for _ in range(count):
            camera_id, model_id = struct.unpack(
                "<ii", _read_exact(stream, 8, "cameras.bin camera header")
            )
            width, height = struct.unpack(
                "<QQ", _read_exact(stream, 16, "cameras.bin dimensions")
            )
            model = _COLMAP_CAMERA_MODELS.get(model_id)
            if model is None:
                raise ContractError(f"Unsupported COLMAP camera model id: {model_id}")
            model_name, param_count = model
            params = struct.unpack(
                "<" + "d" * param_count,
                _read_exact(stream, 8 * param_count, "cameras.bin parameters"),
            )
            if model_name != "PINHOLE":
                raise ContractError(
                    f"Free-space evidence currently requires PINHOLE, got {model_name}"
                )
            fx, fy, cx, cy = (float(v) for v in params)
            if camera_id <= 0 or width <= 0 or height <= 0:
                raise ContractError("Invalid COLMAP binary camera row")
            if not all(math.isfinite(v) for v in (fx, fy, cx, cy)) or fx <= 0 or fy <= 0:
                raise ContractError("Invalid COLMAP binary PINHOLE intrinsics")
            result[int(camera_id)] = {
                "camera_id": int(camera_id),
                "model": model_name,
                "width": int(width),
                "height": int(height),
                "fx": fx,
                "fy": fy,
                "cx": cx,
                "cy": cy,
            }
        if stream.read(1):
            raise ContractError("COLMAP cameras.bin contains unexpected trailing bytes")
    if not result:
        raise ContractError("COLMAP cameras.bin contains no cameras")
    return result


def _read_c_string(stream, label: str, *, max_bytes: int = 32768) -> str:
    raw = bytearray()
    while True:
        value = stream.read(1)
        if not value:
            raise ContractError(f"Unexpected EOF while reading {label}")
        if value == b"\x00":
            break
        raw.extend(value)
        if len(raw) > max_bytes:
            raise ContractError(f"{label} exceeds maximum length")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ContractError(f"{label} is not valid UTF-8") from error


def parse_colmap_images_bin(path: str | Path) -> tuple[dict[str, object], ...]:
    """Parse COLMAP images.bin pose rows, skipping POINTS2D payloads."""

    path = Path(path).resolve()
    if not path.is_file():
        raise ContractError(f"COLMAP images.bin does not exist: {path}")
    rows = []
    with path.open("rb") as stream:
        (count,) = struct.unpack("<Q", _read_exact(stream, 8, "images.bin count"))
        for _ in range(count):
            (image_id,) = struct.unpack("<i", _read_exact(stream, 4, "images.bin image id"))
            qvec = struct.unpack("<dddd", _read_exact(stream, 32, "images.bin qvec"))
            tvec = struct.unpack("<ddd", _read_exact(stream, 24, "images.bin tvec"))
            (camera_id,) = struct.unpack("<i", _read_exact(stream, 4, "images.bin camera id"))
            name = _read_c_string(stream, "images.bin image name")
            (point_count,) = struct.unpack(
                "<Q", _read_exact(stream, 8, "images.bin POINTS2D count")
            )
            # Each POINT2D row = x(double), y(double), point3D_id(int64).
            skip = int(point_count) * 24
            if skip:
                _read_exact(stream, skip, "images.bin POINTS2D payload")
            if image_id <= 0 or camera_id <= 0:
                raise ContractError(f"Invalid COLMAP binary image row: {name}")
            if not all(math.isfinite(v) for v in (*qvec, *tvec)):
                raise ContractError(f"Non-finite COLMAP binary image pose: {name}")
            rows.append(
                {
                    "image_id": int(image_id),
                    "qvec": tuple(float(v) for v in qvec),
                    "tvec": tuple(float(v) for v in tvec),
                    "camera_id": int(camera_id),
                    "name": name,
                }
            )
        if stream.read(1):
            raise ContractError("COLMAP images.bin contains unexpected trailing bytes")
    if not rows:
        raise ContractError("COLMAP images.bin contains no image pose rows")
    return tuple(rows)


def load_colmap_sparse_cameras(sparse_root: str | Path):
    """Load dense-workspace camera authority from text when present, else binary."""

    root = Path(sparse_root).resolve()
    txt = root / "cameras.txt"
    binary = root / "cameras.bin"
    if txt.is_file():
        return parse_colmap_cameras_txt(txt), "TEXT"
    if binary.is_file():
        return parse_colmap_cameras_bin(binary), "BINARY"
    raise ContractError(
        f"COLMAP sparse camera model missing: expected {txt} or {binary}"
    )


def load_colmap_sparse_images(sparse_root: str | Path):
    """Load dense-workspace image poses from text when present, else binary."""

    root = Path(sparse_root).resolve()
    txt = root / "images.txt"
    binary = root / "images.bin"
    if txt.is_file():
        return parse_colmap_images_txt(txt), "TEXT"
    if binary.is_file():
        return parse_colmap_images_bin(binary), "BINARY"
    raise ContractError(
        f"COLMAP sparse image model missing: expected {txt} or {binary}"
    )

def qvec_to_rotation_matrix(qvec):
    """Return COLMAP world-to-camera rotation matrix from (qw,qx,qy,qz)."""

    qw, qx, qy, qz = (float(v) for v in qvec)
    norm = math.sqrt(qw * qw + qx * qx + qy * qy + qz * qz)
    if not math.isfinite(norm) or norm <= 1.0e-12:
        raise ContractError("Invalid COLMAP quaternion")
    qw, qx, qy, qz = (v / norm for v in (qw, qx, qy, qz))
    return (
        (
            1 - 2 * (qy * qy + qz * qz),
            2 * (qx * qy - qz * qw),
            2 * (qx * qz + qy * qw),
        ),
        (
            2 * (qx * qy + qz * qw),
            1 - 2 * (qx * qx + qz * qz),
            2 * (qy * qz - qx * qw),
        ),
        (
            2 * (qx * qz - qy * qw),
            2 * (qy * qz + qx * qw),
            1 - 2 * (qx * qx + qy * qy),
        ),
    )


def colmap_camera_center(qvec, tvec) -> tuple[float, float, float]:
    rotation = qvec_to_rotation_matrix(qvec)
    # C = -R^T t
    return tuple(
        -sum(rotation[row][col] * float(tvec[row]) for row in range(3))
        for col in range(3)
    )


def colmap_camera_point_to_world(qvec, tvec, point_camera) -> tuple[float, float, float]:
    rotation = qvec_to_rotation_matrix(qvec)
    shifted = tuple(float(point_camera[i]) - float(tvec[i]) for i in range(3))
    return tuple(
        sum(rotation[row][col] * shifted[row] for row in range(3))
        for col in range(3)
    )
