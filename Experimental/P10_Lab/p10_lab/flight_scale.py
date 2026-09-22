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


def select_local_flight_radius(depths) -> tuple[float, dict[str, float | int]]:
    values = []
    for value in depths:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        value = float(value)
        if isfinite(value) and value > 0.0:
            values.append(value)
    if len(values) < 3:
        raise ContractError("At least three finite positive camera depths are required")
    values.sort()

    def percentile(percent: float) -> float:
        position = (len(values) - 1) * percent
        lower = int(position)
        upper = min(len(values) - 1, lower + 1)
        weight = position - lower
        return values[lower] * (1.0 - weight) + values[upper] * weight

    median = percentile(0.50)
    stats = {
        "sample_count": len(values),
        "median_depth": median,
        "p80_depth": percentile(0.80),
        "p95_depth": percentile(0.95),
        "max_depth": values[-1],
    }
    return median, stats


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

    median, stats = select_local_flight_radius(depths.tolist())
    evidence = FlightScaleEvidence(
        method="PRIMARY_MESH_MEDIAN_CAMERA_DEPTH",
        sample_count=int(stats["sample_count"]),
        median_depth=float(stats["median_depth"]),
        p80_depth=float(stats["p80_depth"]),
        p95_depth=float(stats["p95_depth"]),
        max_depth=float(stats["max_depth"]),
    )
    return SceneScale(median), evidence
