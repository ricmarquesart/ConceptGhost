from __future__ import annotations

from dataclasses import dataclass
from math import cos, isfinite, pi, sin, sqrt

from .contracts import ContractError
from .path_planner import CameraPath, RelativeWaypoint


_ALLOWED_MODES = {"PATH", "SPIN_360"}
_ALLOWED_COLLISION_MODES = {"HOLD_AND_RESUME", "DISABLED"}
_MAX_DRONES = 7


def _finite(value, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{label} must be a finite number")
    value = float(value)
    if not isfinite(value):
        raise ContractError(f"{label} must be finite")
    return value


@dataclass(frozen=True)
class DroneWaypoint:
    right: float
    up: float
    forward: float

    def __post_init__(self) -> None:
        for name in ("right", "up", "forward"):
            object.__setattr__(self, name, _finite(getattr(self, name), name))

    def to_relative(self, *, look_right=0.0, look_up=0.0, look_forward=1.0) -> RelativeWaypoint:
        return RelativeWaypoint(
            right=self.right,
            up=self.up,
            forward=self.forward,
            look_right=float(look_right),
            look_up=float(look_up),
            look_forward=float(look_forward),
        )

    def to_dict(self) -> dict[str, float]:
        return {"right": self.right, "up": self.up, "forward": self.forward}


@dataclass(frozen=True)
class DroneMission:
    name: str
    mode: str
    waypoints: tuple[DroneWaypoint, ...]
    enabled: bool = True

    def __post_init__(self) -> None:
        name = str(self.name).strip()
        if not name:
            raise ContractError("Drone mission name cannot be empty")
        object.__setattr__(self, "name", name)
        mode = str(self.mode).strip().upper()
        if mode not in _ALLOWED_MODES:
            raise ContractError(f"Unsupported drone mission mode: {mode}")
        object.__setattr__(self, "mode", mode)
        if not isinstance(self.enabled, bool):
            raise ContractError("Drone mission enabled must be boolean")
        if mode == "PATH" and len(self.waypoints) < 2:
            raise ContractError("PATH mission requires at least two waypoints")
        if mode == "SPIN_360" and len(self.waypoints) != 1:
            raise ContractError("SPIN_360 mission requires exactly one anchor waypoint")

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "mode": self.mode,
            "enabled": self.enabled,
            "waypoints": [p.to_dict() for p in self.waypoints],
        }


@dataclass(frozen=True)
class DroneRoutePlan:
    missions: tuple[DroneMission, ...]
    frames_per_drone: int = 30
    collision_mode: str = "HOLD_AND_RESUME"
    min_clearance_m: float = 0.20

    def __post_init__(self) -> None:
        if not 1 <= len(self.missions) <= _MAX_DRONES:
            raise ContractError("Drone route plan must contain between 1 and 7 missions")
        if type(self.frames_per_drone) is not int or not 2 <= self.frames_per_drone <= 240:
            raise ContractError("frames_per_drone must be an integer in [2, 240]")
        mode = str(self.collision_mode).strip().upper()
        if mode not in _ALLOWED_COLLISION_MODES:
            raise ContractError(f"Unsupported collision mode: {mode}")
        object.__setattr__(self, "collision_mode", mode)
        clearance = _finite(self.min_clearance_m, "min_clearance_m")
        if clearance < 0.0 or clearance > 10.0:
            raise ContractError("min_clearance_m must be in [0, 10]")
        object.__setattr__(self, "min_clearance_m", clearance)
        names = [m.name for m in self.missions]
        if len(names) != len(set(names)):
            raise ContractError("Drone mission names must be unique")

    @property
    def active_missions(self) -> tuple[DroneMission, ...]:
        return tuple(m for m in self.missions if m.enabled)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "ConceptGhost.P10DroneRoutePlan.v0.1",
            "coordinate_space": "P9_CAMERA_LOCAL_RIGHT_UP_FORWARD_METERS",
            "maximum_drone_count": _MAX_DRONES,
            "frames_per_drone": self.frames_per_drone,
            "collision_mode": self.collision_mode,
            "min_clearance_m": self.min_clearance_m,
            "missions": [m.to_dict() for m in self.missions],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "DroneRoutePlan":
        if not isinstance(payload, dict):
            raise ContractError("Drone route plan must be an object")
        schema = str(payload.get("schema") or "ConceptGhost.P10DroneRoutePlan.v0.1")
        if schema != "ConceptGhost.P10DroneRoutePlan.v0.1":
            raise ContractError(f"Unsupported drone route schema: {schema}")
        raw = payload.get("missions")
        if not isinstance(raw, list):
            raise ContractError("Drone route plan missions must be a list")
        missions = []
        for index, item in enumerate(raw):
            if not isinstance(item, dict):
                raise ContractError(f"Mission {index} must be an object")
            points = item.get("waypoints")
            if not isinstance(points, list):
                raise ContractError(f"Mission {index} waypoints must be a list")
            parsed_points = []
            for point_index, p in enumerate(points):
                if not isinstance(p, dict):
                    raise ContractError(
                        f"Mission {index} waypoint {point_index} must be an object"
                    )
                parsed_points.append(
                    DroneWaypoint(
                        right=p.get("right"),
                        up=p.get("up"),
                        forward=p.get("forward"),
                    )
                )
            missions.append(
                DroneMission(
                    name=str(item.get("name") or f"drone_{index + 1}"),
                    mode=str(item.get("mode") or "PATH"),
                    enabled=bool(item.get("enabled", True)),
                    waypoints=tuple(parsed_points),
                )
            )
        return cls(
            missions=tuple(missions),
            frames_per_drone=int(payload.get("frames_per_drone", 30)),
            collision_mode=str(payload.get("collision_mode") or "HOLD_AND_RESUME"),
            min_clearance_m=float(payload.get("min_clearance_m", 0.20)),
        )


@dataclass(frozen=True)
class CollisionHoldReport:
    mission_name: str
    input_frame_count: int
    held_frame_count: int
    resumed_frame_count: int
    minimum_candidate_clearance: float | None
    minimum_output_clearance: float | None
    policy: str = "P9_CLEARANCE_HOLD_LAST_SAFE_UNTIL_ROUTE_REEMERGES"

    def to_dict(self) -> dict[str, object]:
        return {
            "mission_name": self.mission_name,
            "input_frame_count": self.input_frame_count,
            "held_frame_count": self.held_frame_count,
            "resumed_frame_count": self.resumed_frame_count,
            "minimum_candidate_clearance": self.minimum_candidate_clearance,
            "minimum_output_clearance": self.minimum_output_clearance,
            "policy": self.policy,
        }


def _distance(a: DroneWaypoint, b: DroneWaypoint) -> float:
    return sqrt(
        (a.right - b.right) ** 2
        + (a.up - b.up) ** 2
        + (a.forward - b.forward) ** 2
    )


def _normalize(v: tuple[float, float, float]) -> tuple[float, float, float]:
    length = sqrt(sum(value * value for value in v))
    if length <= 1.0e-12:
        return (0.0, 0.0, 1.0)
    return tuple(value / length for value in v)


def _sample_path(mission: DroneMission, frame_count: int) -> CameraPath:
    points = mission.waypoints
    lengths = [_distance(points[i], points[i + 1]) for i in range(len(points) - 1)]
    total = sum(lengths)
    if total <= 1.0e-9:
        raise ContractError(f"Mission {mission.name} path has zero length")
    cumulative = [0.0]
    for length in lengths:
        cumulative.append(cumulative[-1] + length)

    result = []
    for frame in range(frame_count):
        target = total * frame / float(max(1, frame_count - 1))
        segment = len(lengths) - 1
        for index, end in enumerate(cumulative[1:]):
            if target <= end + 1.0e-12:
                segment = index
                break
        left = points[segment]
        right = points[segment + 1]
        length = lengths[segment]
        amount = 0.0 if length <= 1.0e-12 else (target - cumulative[segment]) / length
        amount = max(0.0, min(1.0, amount))
        position = DroneWaypoint(
            left.right * (1.0 - amount) + right.right * amount,
            left.up * (1.0 - amount) + right.up * amount,
            left.forward * (1.0 - amount) + right.forward * amount,
        )
        tangent = _normalize(
            (
                right.right - left.right,
                right.up - left.up,
                right.forward - left.forward,
            )
        )
        result.append(position.to_relative(
            look_right=tangent[0],
            look_up=tangent[1],
            look_forward=tangent[2],
        ))
    return CameraPath(mission.name, tuple(result))


def _sample_spin(mission: DroneMission, frame_count: int) -> CameraPath:
    anchor = mission.waypoints[0]
    result = []
    for frame in range(frame_count):
        angle = 2.0 * pi * frame / float(frame_count)
        result.append(anchor.to_relative(
            look_right=sin(angle),
            look_up=0.0,
            look_forward=cos(angle),
        ))
    return CameraPath(mission.name, tuple(result))


def sample_mission(mission: DroneMission, frame_count: int) -> CameraPath:
    if type(frame_count) is not int or frame_count < 2:
        raise ContractError("frame_count must be an integer >= 2")
    if mission.mode == "PATH":
        return _sample_path(mission, frame_count)
    if mission.mode == "SPIN_360":
        return _sample_spin(mission, frame_count)
    raise ContractError(f"Unsupported mission mode: {mission.mode}")


def sample_route_plan(plan: DroneRoutePlan) -> tuple[CameraPath, ...]:
    active = plan.active_missions
    if not active:
        raise ContractError("Drone route plan has no enabled missions")
    return tuple(sample_mission(m, plan.frames_per_drone) for m in active)


def apply_hold_and_resume_clearance(
    path: CameraPath,
    clearance_query,
    *,
    min_clearance: float,
) -> tuple[CameraPath, CollisionHoldReport]:
    """Keep the camera at the last safe point while the authored route is blocked.

    Time keeps advancing along the authored path. When the requested position
    enters the current collision envelope, the drone remains at the last safe
    position; when the authored route becomes safe again it resumes. This
    prevents an authored path from simply passing through a facade.

    The route contract is independent of the collision backend. The first
    implementation can use the existing P9 clearance cloud; later Gate 7
    free-space / visibility evidence can replace or augment the query without
    changing authored route files.
    """

    threshold = _finite(min_clearance, "min_clearance")
    if threshold < 0.0:
        raise ContractError("min_clearance cannot be negative")
    if not path.waypoints:
        raise ContractError("Camera path cannot be empty")

    output = []
    last_safe = None
    held = 0
    resumed = 0
    was_holding = False
    candidate_clearances = []
    output_clearances = []

    for candidate in path.waypoints:
        clearance = float(clearance_query(candidate))
        if isfinite(clearance):
            candidate_clearances.append(clearance)
        safe = isfinite(clearance) and clearance >= threshold

        if safe:
            if was_holding:
                resumed += 1
            output.append(candidate)
            last_safe = candidate
            output_clearances.append(clearance)
            was_holding = False
            continue

        if last_safe is None:
            raise ContractError(
                f"Mission {path.name} starts inside the collision clearance envelope"
            )

        output.append(
            RelativeWaypoint(
                right=last_safe.right,
                up=last_safe.up,
                forward=last_safe.forward,
                look_right=candidate.look_right,
                look_up=candidate.look_up,
                look_forward=candidate.look_forward,
            )
        )
        held += 1
        was_holding = True
        held_clearance = float(clearance_query(last_safe))
        if isfinite(held_clearance):
            output_clearances.append(held_clearance)

    report = CollisionHoldReport(
        mission_name=path.name,
        input_frame_count=len(path.waypoints),
        held_frame_count=held,
        resumed_frame_count=resumed,
        minimum_candidate_clearance=min(candidate_clearances) if candidate_clearances else None,
        minimum_output_clearance=min(output_clearances) if output_clearances else None,
    )
    return CameraPath(path.name, tuple(output)), report


def seed_plan_from_footprint(footprint, *, frames_per_drone: int = 30) -> DroneRoutePlan:
    """Create one editable starter mission; it is a UI seed, not route authority."""

    start_forward = max(0.0, float(footprint.forward_near) * 0.25)
    end_forward = float(footprint.center_forward)
    start_up = max(0.0, float(footprint.up_min) * 0.05)
    end_up = max(
        start_up,
        0.5 * (float(footprint.up_min) + float(footprint.up_max)) * 0.05,
    )
    mission = DroneMission(
        name="drone_1",
        mode="PATH",
        enabled=True,
        waypoints=(
            DroneWaypoint(0.0, start_up, start_forward),
            DroneWaypoint(float(footprint.center_right) * 0.25, end_up, end_forward),
        ),
    )
    return DroneRoutePlan(
        missions=(mission,),
        frames_per_drone=frames_per_drone,
        collision_mode="HOLD_AND_RESUME",
        min_clearance_m=0.20,
    )
