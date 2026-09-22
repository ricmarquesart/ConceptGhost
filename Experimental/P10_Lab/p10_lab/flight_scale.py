from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from math import isfinite

from .contracts import ContractError, SceneScale


@dataclass(frozen=True)
class FlightScaleEvidence:
    method: str
    sample_count: int
    median_depth: float
    p80_depth: float
    p95_depth: float
    max_depth: float

    def manifest(self) -> dict[str, object]:
        return {
            "method": self.method,
            "sample_count": self.sample_count,
            "median_depth": self.median_depth,
            "p80_depth": self.p80_depth,
            "p95_depth": self.p95_depth,
            "max_depth": self.max_depth,
            "selected_radius": self.median_depth,
        }


def derive_flight_scale_from_primary_mesh(
    primary_mesh: str | Path,
) -> tuple[SceneScale, FlightScaleEvidence]:
    """Measure a local camera-motion scale from authoritative P9 depth.

    Camera flights should respond to the scene that occupies the current view,
    not to the single farthest vertex. The median positive canonical camera
    depth is robust to long streets, skyline points and other far geometry while
    preserving the existing P9 world units. No geometry rescaling is performed.
    """

    try:
        import numpy as np
    except ImportError as error:
        raise ContractError("NumPy is required to derive the P10 flight scale") from error

    path = Path(primary_mesh)
    if not path.is_file() or path.suffix.lower() != ".npz":
        raise ContractError(f"P10 flight scale requires authoritative PrimaryMesh NPZ: {path}")

    try:
        with np.load(path, allow_pickle=False) as payload:
            if "camera_depth" not in payload.files:
                raise ContractError("PrimaryMesh NPZ is missing camera_depth")
            depths = np.asarray(payload["camera_depth"], dtype=np.float64).reshape(-1)
    except ContractError:
        raise
    except Exception as error:
        raise ContractError(f"Cannot read PrimaryMesh NPZ flight scale: {path}: {error}") from error

    valid = depths[np.isfinite(depths) & (depths > 0.0)]
    if valid.size < 3:
        raise ContractError("PrimaryMesh does not contain enough finite positive camera_depth samples")

    median = float(np.median(valid))
    p80 = float(np.percentile(valid, 80.0))
    p95 = float(np.percentile(valid, 95.0))
    maximum = float(np.max(valid))
    if not all(isfinite(value) and value > 0.0 for value in (median, p80, p95, maximum)):
        raise ContractError("Derived P10 flight scale is invalid")

    evidence = FlightScaleEvidence(
        method="PRIMARY_MESH_MEDIAN_CAMERA_DEPTH",
        sample_count=int(valid.size),
        median_depth=median,
        p80_depth=p80,
        p95_depth=p95,
        max_depth=maximum,
    )
    return SceneScale(median), evidence
