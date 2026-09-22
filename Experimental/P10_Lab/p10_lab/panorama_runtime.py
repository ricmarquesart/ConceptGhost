from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .contracts import ContractError, SceneScale
from .observation_map import ObservationMap
from .panorama import CameraAuthority, PanoramaSpec
from .completion_envelope import GenerationCandidateMap


@dataclass(frozen=True)
class SceneScaleEvidence:
    radius: float
    vertex_count: int
    bbox_min: tuple[float, float, float]
    bbox_max: tuple[float, float, float]
    bbox_center: tuple[float, float, float]
    method: str = "PRIMARY_MESH_MAX_DISTANCE_FROM_BBOX_CENTER"

    def manifest(self) -> dict[str, object]:
        return {
            "method": self.method,
            "radius": self.radius,
            "vertex_count": self.vertex_count,
            "bbox_min": list(self.bbox_min),
            "bbox_max": list(self.bbox_max),
            "bbox_center": list(self.bbox_center),
        }


def derive_scene_scale_from_primary_mesh(
    primary_mesh: str | Path,
) -> tuple[SceneScale, SceneScaleEvidence]:
    """Derive a characteristic scene radius without changing canonical scale.

    The PrimaryMesh is already in authoritative P9/Baseline world units. This
    function measures those existing coordinates; it never rescales geometry.
    Heavy NumPy import is intentionally lazy so the custom node can register in
    ComfyUI before any preview execution.
    """

    try:
        import numpy as np
    except ImportError as error:
        raise ContractError("NumPy is required to inspect the authoritative PrimaryMesh") from error

    path = Path(primary_mesh)
    if not path.is_file() or path.suffix.lower() != ".npz":
        raise ContractError(f"Gate 3 preview requires the current authoritative PrimaryMesh NPZ: {path}")

    try:
        with np.load(path, allow_pickle=False) as payload:
            if "vertices" not in payload.files:
                raise ContractError("PrimaryMesh NPZ is missing vertices")
            vertices = np.asarray(payload["vertices"], dtype=np.float64)
    except ContractError:
        raise
    except Exception as error:
        raise ContractError(f"Cannot read PrimaryMesh NPZ: {path}: {error}") from error

    if vertices.ndim != 2 or vertices.shape[1] != 3 or vertices.shape[0] < 3:
        raise ContractError("PrimaryMesh vertices must have shape [N,3] with N >= 3")
    if not np.isfinite(vertices).all():
        raise ContractError("PrimaryMesh contains non-finite vertices")

    bbox_min_array = vertices.min(axis=0)
    bbox_max_array = vertices.max(axis=0)
    center_array = (bbox_min_array + bbox_max_array) * 0.5
    distances = np.linalg.norm(vertices - center_array[None, :], axis=1)
    radius = float(distances.max())
    if not np.isfinite(radius) or radius <= 0.0:
        raise ContractError("PrimaryMesh scene radius must be finite and positive")

    evidence = SceneScaleEvidence(
        radius=radius,
        vertex_count=int(vertices.shape[0]),
        bbox_min=tuple(float(value) for value in bbox_min_array),
        bbox_max=tuple(float(value) for value in bbox_max_array),
        bbox_center=tuple(float(value) for value in center_array),
    )
    return SceneScale(radius), evidence


def render_temporary_panorama(
    source_image: str | Path,
    camera: CameraAuthority,
    spec: PanoramaSpec,
    observation: ObservationMap,
    candidates: GenerationCandidateMap,
):
    """Render the source-preserving temporary ERP plus its two authority masks.

    Returns ComfyUI-native tensors:
    IMAGE [1,H,W,3], source-lock MASK [1,H,W], candidate MASK [1,H,W].
    Torch/Pillow/NumPy imports are lazy to keep node discovery lightweight.
    """

    try:
        import numpy as np
        import torch
        import torch.nn.functional as functional
        from PIL import Image
    except ImportError as error:
        raise ContractError(
            "Gate 3 visual preview requires NumPy, Pillow and Torch from the existing ComfyUI environment"
        ) from error

    image_path = Path(source_image)
    if not image_path.is_file():
        raise ContractError(f"Source image does not exist: {image_path}")

    try:
        with Image.open(image_path) as opened:
            rgb = opened.convert("RGB")
            if rgb.size != (camera.width, camera.height):
                raise ContractError(
                    f"Source image dimensions {rgb.size} do not match camera "
                    f"{(camera.width, camera.height)}"
                )
            source_array = np.asarray(rgb, dtype=np.float32).copy() / 255.0
    except ContractError:
        raise
    except Exception as error:
        raise ContractError(f"Cannot decode source image: {image_path}: {error}") from error

    source = torch.from_numpy(source_array).unsqueeze(0).permute(0, 3, 1, 2)
    height = spec.height
    width = spec.width

    ys = torch.arange(height, dtype=torch.float32) + 0.5
    xs = torch.arange(width, dtype=torch.float32) + 0.5
    latitude = (0.5 - ys[:, None] / float(height)) * torch.pi
    longitude = (xs[None, :] / float(width) - 0.5) * (2.0 * torch.pi)

    cos_latitude = torch.cos(latitude)
    ray_x = torch.sin(longitude) * cos_latitude
    ray_y = torch.sin(latitude).expand(height, width)
    ray_z = -torch.cos(longitude) * cos_latitude

    forward = -ray_z
    safe_forward = torch.clamp(forward, min=1.0e-8)
    source_x = camera.cx + camera.fx * (ray_x / safe_forward)
    source_y = camera.cy - camera.fy * (ray_y / safe_forward)

    grid_x = 2.0 * source_x / float(camera.width) - 1.0
    grid_y = 2.0 * source_y / float(camera.height) - 1.0
    grid = torch.stack((grid_x, grid_y), dim=-1).unsqueeze(0)

    sampled = functional.grid_sample(
        source,
        grid,
        mode="bilinear",
        padding_mode="border",
        align_corners=False,
    ).permute(0, 2, 3, 1)

    source_lock_array = (
        np.frombuffer(observation.source_lock_bytes(), dtype=np.uint8)
        .reshape(height, width)
        .copy()
        .astype(np.float32)
        / 255.0
    )
    candidate_array = (
        np.frombuffer(candidates.mask_bytes(), dtype=np.uint8)
        .reshape(height, width)
        .copy()
        .astype(np.float32)
        / 255.0
    )
    source_lock = torch.from_numpy(source_lock_array).unsqueeze(0)
    candidate_mask = torch.from_numpy(candidate_array).unsqueeze(0)

    panorama = sampled * source_lock.unsqueeze(-1)
    panorama = torch.clamp(panorama, 0.0, 1.0).contiguous()

    return panorama, source_lock.contiguous(), candidate_mask.contiguous()
