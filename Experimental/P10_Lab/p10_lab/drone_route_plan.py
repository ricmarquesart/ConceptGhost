from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from math import cos, isfinite, pi, sin, sqrt

from .contracts import ContractError
from .path_planner import CameraPath, RelativeWaypoint


_ALLOWED_MODES = {"PATH", "SPIN_360"}
_ALLOWED_COLLISION_MODES = {"HOLD_AND_RESUME", "DISABLED"}
_ALLOWED_ROUTE_AUTHORITIES = {"EDITABLE_SEED", "ARTIST_AUTHORED"}
_ALLOWED_ORIENTATION_MODES = {"LOOK_AT_TARGET", "LOOK_ALONG_PATH", "MANUAL_DIRECTION"}
_MAX_DRONES = 7
_ROUTE_SCHEMA = "ConceptGhost.P10DroneRoutePlan.v0.3"
_LEGACY_ROUTE_SCHEMAS = {
    "ConceptGhost.P10DroneRoutePlan.v0.1",
    "ConceptGhost.P10DroneRoutePlan.v0.2",
    _ROUTE_SCHEMA,
}
_BOUND_ROUTE_SCHEMA = "ConceptGhost.P10BoundDroneRoutePlan.v0.3"
_LEGACY_BOUND_ROUTE_SCHEMAS = {
    "ConceptGhost.P10BoundDroneRoutePlan.v0.1",
    "ConceptGhost.P10BoundDroneRoutePlan.v0.2",
    _BOUND_ROUTE_SCHEMA,
}


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
    look_right: float | None = None
    look_up: float | None = None
    look_forward: float | None = None

    def __post_init__(self) -> None:
        for name in ("right", "up", "forward"):
            object.__setattr__(self, name, _finite(getattr(self, name), name))
        look_values=(self.look_right,self.look_up,self.look_forward)
        if any(value is not None for value in look_values):
            if any(value is None for value in look_values):
                raise ContractError("Waypoint per-point look direction must provide right/up/forward together")
            raw=tuple(float(value) for value in look_values)
            length=sqrt(sum(value*value for value in raw))
            if length<=1.0e-12:
                raise ContractError("waypoint per-point look direction cannot have zero length")
            # Preserve already-normalized serialized values exactly so a
            # v0.3 JSON round-trip is hash/idempotence stable.
            normalized=raw if abs(length-1.0)<=1.0e-12 else tuple(value/length for value in raw)
            object.__setattr__(self,"look_right",normalized[0])
            object.__setattr__(self,"look_up",normalized[1])
            object.__setattr__(self,"look_forward",normalized[2])

    @property
    def has_look_direction(self) -> bool:
        return self.look_right is not None

    def to_relative(self, *, look_right=0.0, look_up=0.0, look_forward=1.0) -> RelativeWaypoint:
        return RelativeWaypoint(
            right=self.right,
            up=self.up,
            forward=self.forward,
            look_right=float(look_right),
            look_up=float(look_up),
            look_forward=float(look_forward),
        )

    def to_dict(self) -> dict[str, object]:
        payload={"right": self.right, "up": self.up, "forward": self.forward}
        if self.has_look_direction:
            payload["look_direction"]={
                "right":float(self.look_right),
                "up":float(self.look_up),
                "forward":float(self.look_forward),
            }
        return payload


@dataclass(frozen=True)
class DroneMission:
    name: str
    mode: str
    waypoints: tuple[DroneWaypoint, ...]
    enabled: bool = True
    orientation_mode: str = "LOOK_ALONG_PATH"
    look_target: DroneWaypoint | None = None
    manual_direction: DroneWaypoint | None = None
    spin_pitch_deg: float = 0.0
    spin_yaw_start_deg: float = 0.0

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

        orientation = str(self.orientation_mode or "LOOK_ALONG_PATH").strip().upper()
        if orientation not in _ALLOWED_ORIENTATION_MODES:
            raise ContractError(f"Unsupported camera orientation mode: {orientation}")
        object.__setattr__(self, "orientation_mode", orientation)

        if mode == "PATH" and len(self.waypoints) < 2:
            raise ContractError("PATH mission requires at least two waypoints")
        if mode == "SPIN_360" and len(self.waypoints) != 1:
            raise ContractError("SPIN_360 mission requires exactly one anchor waypoint")
        if mode == "PATH" and orientation == "LOOK_AT_TARGET" and self.look_target is None:
            raise ContractError("LOOK_AT_TARGET PATH mission requires look_target")
        if mode == "PATH" and orientation == "MANUAL_DIRECTION" and self.manual_direction is None:
            raise ContractError("MANUAL_DIRECTION PATH mission requires manual_direction")
        pitch=_finite(self.spin_pitch_deg,"spin_pitch_deg")
        yaw=_finite(self.spin_yaw_start_deg,"spin_yaw_start_deg")
        if pitch < -89.0 or pitch > 89.0:
            raise ContractError("spin_pitch_deg must be in [-89, 89]")
        object.__setattr__(self,"spin_pitch_deg",pitch)
        object.__setattr__(self,"spin_yaw_start_deg",yaw)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "mode": self.mode,
            "enabled": self.enabled,
            "orientation_mode": self.orientation_mode,
            "look_target": self.look_target.to_dict() if self.look_target is not None else None,
            "manual_direction": (
                self.manual_direction.to_dict() if self.manual_direction is not None else None
            ),
            "spin_pitch_deg":self.spin_pitch_deg,
            "spin_yaw_start_deg":self.spin_yaw_start_deg,
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
            "schema": _ROUTE_SCHEMA,
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
        schema = str(payload.get("schema") or _ROUTE_SCHEMA)
        if schema not in _LEGACY_ROUTE_SCHEMAS:
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
                look_direction=p.get("look_direction")
                if look_direction is not None and not isinstance(look_direction,dict):
                    raise ContractError(
                        f"Mission {index} waypoint {point_index} look_direction must be an object"
                    )
                parsed_points.append(
                    DroneWaypoint(
                        right=p.get("right"),
                        up=p.get("up"),
                        forward=p.get("forward"),
                        look_right=(look_direction or {}).get("right"),
                        look_up=(look_direction or {}).get("up"),
                        look_forward=(look_direction or {}).get("forward"),
                    )
                )
            def parse_optional_waypoint(value, label):
                if value is None:
                    return None
                if not isinstance(value, dict):
                    raise ContractError(f"Mission {index} {label} must be an object")
                return DroneWaypoint(
                    right=value.get("right"),
                    up=value.get("up"),
                    forward=value.get("forward"),
                )

            # v0.1 route files had implicit tangent-follow orientation.
            orientation_mode=str(
                item.get("orientation_mode")
                or ("LOOK_ALONG_PATH" if schema=="ConceptGhost.P10DroneRoutePlan.v0.1" else "LOOK_ALONG_PATH")
            )
            missions.append(
                DroneMission(
                    name=str(item.get("name") or f"drone_{index + 1}"),
                    mode=str(item.get("mode") or "PATH"),
                    enabled=bool(item.get("enabled", True)),
                    waypoints=tuple(parsed_points),
                    orientation_mode=orientation_mode,
                    look_target=parse_optional_waypoint(item.get("look_target"), "look_target"),
                    manual_direction=parse_optional_waypoint(
                        item.get("manual_direction"), "manual_direction"
                    ),
                    spin_pitch_deg=float(item.get("spin_pitch_deg",0.0)),
                    spin_yaw_start_deg=float(item.get("spin_yaw_start_deg",0.0)),
                )
            )
        return cls(
            missions=tuple(missions),
            frames_per_drone=int(payload.get("frames_per_drone", 30)),
            collision_mode=str(payload.get("collision_mode") or "HOLD_AND_RESUME"),
            min_clearance_m=float(payload.get("min_clearance_m", 0.20)),
        )


def _clean_binding_text(value: object, label: str) -> str:
    text=str(value or "").strip()
    if not text:
        raise ContractError(f"{label} cannot be empty")
    return text


def _normalize_route_authority(value: object) -> str:
    authority=str(value or "").strip().upper()
    if authority not in _ALLOWED_ROUTE_AUTHORITIES:
        raise ContractError(f"Unsupported route authority: {authority or '<empty>'}")
    return authority


def _route_identity_payload(
    plan: DroneRoutePlan,
    *,
    scene_contract_id: str,
    source_run_id: str,
    route_authority: str,
) -> dict[str, object]:
    payload=plan.to_dict()
    payload.update({
        "binding_schema":_BOUND_ROUTE_SCHEMA,
        "scene_contract_id":_clean_binding_text(scene_contract_id,"scene_contract_id"),
        "source_run_id":_clean_binding_text(source_run_id,"source_run_id"),
        "route_authority":_normalize_route_authority(route_authority),
    })
    return payload


def compute_route_plan_sha256(
    plan: DroneRoutePlan,
    *,
    scene_contract_id: str,
    source_run_id: str,
    route_authority: str,
) -> str:
    payload=_route_identity_payload(
        plan,
        scene_contract_id=scene_contract_id,
        source_run_id=source_run_id,
        route_authority=route_authority,
    )
    canonical=json.dumps(
        payload,
        sort_keys=True,
        separators=(",",":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def bind_route_plan(
    plan: DroneRoutePlan,
    *,
    scene_contract_id: str,
    source_run_id: str,
    route_authority: str,
) -> dict[str, object]:
    payload=_route_identity_payload(
        plan,
        scene_contract_id=scene_contract_id,
        source_run_id=source_run_id,
        route_authority=route_authority,
    )
    payload["route_plan_sha256"]=compute_route_plan_sha256(
        plan,
        scene_contract_id=payload["scene_contract_id"],
        source_run_id=payload["source_run_id"],
        route_authority=payload["route_authority"],
    )
    return payload



def _legacy_v01_route_payload(plan: DroneRoutePlan) -> dict[str, object]:
    return {
        "schema": "ConceptGhost.P10DroneRoutePlan.v0.1",
        "coordinate_space": "P9_CAMERA_LOCAL_RIGHT_UP_FORWARD_METERS",
        "maximum_drone_count": _MAX_DRONES,
        "frames_per_drone": plan.frames_per_drone,
        "collision_mode": plan.collision_mode,
        "min_clearance_m": plan.min_clearance_m,
        "missions": [
            {
                "name": mission.name,
                "mode": mission.mode,
                "enabled": mission.enabled,
                "waypoints": [point.to_dict() for point in mission.waypoints],
            }
            for mission in plan.missions
        ],
    }


def _legacy_v01_route_hash(
    plan: DroneRoutePlan,
    *,
    scene_contract_id: str,
    source_run_id: str,
    route_authority: str,
) -> str:
    payload=_legacy_v01_route_payload(plan)
    payload.update({
        "binding_schema":"ConceptGhost.P10BoundDroneRoutePlan.v0.1",
        "scene_contract_id":_clean_binding_text(scene_contract_id,"scene_contract_id"),
        "source_run_id":_clean_binding_text(source_run_id,"source_run_id"),
        "route_authority":_normalize_route_authority(route_authority),
    })
    canonical=json.dumps(
        payload,
        sort_keys=True,
        separators=(",",":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()



def _legacy_v02_route_payload(plan: DroneRoutePlan) -> dict[str, object]:
    return {
        "schema":"ConceptGhost.P10DroneRoutePlan.v0.2",
        "coordinate_space":"P9_CAMERA_LOCAL_RIGHT_UP_FORWARD_METERS",
        "maximum_drone_count":_MAX_DRONES,
        "frames_per_drone":plan.frames_per_drone,
        "collision_mode":plan.collision_mode,
        "min_clearance_m":plan.min_clearance_m,
        "missions":[
            {
                "name":mission.name,
                "mode":mission.mode,
                "enabled":mission.enabled,
                "orientation_mode":mission.orientation_mode,
                "look_target":(
                    {
                        "right":mission.look_target.right,
                        "up":mission.look_target.up,
                        "forward":mission.look_target.forward,
                    }
                    if mission.look_target is not None else None
                ),
                "manual_direction":(
                    {
                        "right":mission.manual_direction.right,
                        "up":mission.manual_direction.up,
                        "forward":mission.manual_direction.forward,
                    }
                    if mission.manual_direction is not None else None
                ),
                "waypoints":[
                    {"right":point.right,"up":point.up,"forward":point.forward}
                    for point in mission.waypoints
                ],
            }
            for mission in plan.missions
        ],
    }


def _legacy_v02_route_hash(
    plan: DroneRoutePlan,
    *,
    scene_contract_id: str,
    source_run_id: str,
    route_authority: str,
) -> str:
    payload=_legacy_v02_route_payload(plan)
    payload.update({
        "binding_schema":"ConceptGhost.P10BoundDroneRoutePlan.v0.2",
        "scene_contract_id":_clean_binding_text(scene_contract_id,"scene_contract_id"),
        "source_run_id":_clean_binding_text(source_run_id,"source_run_id"),
        "route_authority":_normalize_route_authority(route_authority),
    })
    canonical=json.dumps(
        payload,
        sort_keys=True,
        separators=(",",":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def parse_bound_route_plan(
    payload: dict[str, object],
    *,
    expected_scene_contract_id: str,
    expected_source_run_id: str,
    require_hash: bool=False,
) -> tuple[DroneRoutePlan,str,str]:
    """Parse, scene-bind and verify a serialized artist route.

    Missing hashes are allowed while the artist is actively editing a saved
    workflow. A present hash is always authoritative and must match exactly.
    Execution returns a freshly bound/hashed payload for persistence.
    """

    if not isinstance(payload,dict):
        raise ContractError("Bound drone route plan must be a JSON object")
    binding_schema=str(payload.get("binding_schema") or _BOUND_ROUTE_SCHEMA)
    route_schema=str(payload.get("schema") or _ROUTE_SCHEMA)
    if binding_schema not in _LEGACY_BOUND_ROUTE_SCHEMAS:
        raise ContractError(f"Unsupported route binding schema: {binding_schema}")

    scene_contract_id=_clean_binding_text(payload.get("scene_contract_id"),"scene_contract_id")
    source_run_id=_clean_binding_text(payload.get("source_run_id"),"source_run_id")
    expected_scene=_clean_binding_text(expected_scene_contract_id,"expected_scene_contract_id")
    expected_run=_clean_binding_text(expected_source_run_id,"expected_source_run_id")
    if scene_contract_id!=expected_scene:
        raise ContractError(
            "Saved drone route belongs to a different scene contract: "
            f"route={scene_contract_id!r}, current={expected_scene!r}"
        )
    if source_run_id!=expected_run:
        raise ContractError(
            "Saved drone route belongs to a different source run: "
            f"route={source_run_id!r}, current={expected_run!r}"
        )

    authority=_normalize_route_authority(payload.get("route_authority"))
    plan=DroneRoutePlan.from_dict(payload)
    expected_hash=compute_route_plan_sha256(
        plan,
        scene_contract_id=scene_contract_id,
        source_run_id=source_run_id,
        route_authority=authority,
    )
    stored_hash=str(payload.get("route_plan_sha256") or "").strip().lower()
    if require_hash and not stored_hash:
        raise ContractError("Bound drone route is missing route_plan_sha256")
    legacy_hash=None
    if (
        binding_schema=="ConceptGhost.P10BoundDroneRoutePlan.v0.1"
        and route_schema=="ConceptGhost.P10DroneRoutePlan.v0.1"
    ):
        legacy_hash=_legacy_v01_route_hash(
            plan,
            scene_contract_id=scene_contract_id,
            source_run_id=source_run_id,
            route_authority=authority,
        )
    elif (
        binding_schema=="ConceptGhost.P10BoundDroneRoutePlan.v0.2"
        and route_schema=="ConceptGhost.P10DroneRoutePlan.v0.2"
    ):
        legacy_hash=_legacy_v02_route_hash(
            plan,
            scene_contract_id=scene_contract_id,
            source_run_id=source_run_id,
            route_authority=authority,
        )
    if stored_hash and stored_hash not in {expected_hash,legacy_hash}:
        raise ContractError(
            "Saved drone route hash does not match its serialized plan; "
            "clear/reset the route or execute the editor to rebind it"
        )
    verified_hash=stored_hash or expected_hash
    return plan,authority,verified_hash


@dataclass(frozen=True)
class CollisionHoldReport:
    mission_name: str
    input_frame_count: int
    held_frame_count: int
    resumed_frame_count: int
    minimum_candidate_clearance: float | None
    minimum_output_clearance: float | None
    policy: str = "P9_SURFACE_CLEARANCE_HOLD_LAST_SAFE_UNTIL_REACHABLE_ROUTE_REEMERGES"

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


def _normalize_strict(
    v: tuple[float, float, float],
    *,
    label: str,
) -> tuple[float, float, float]:
    length = sqrt(sum(value * value for value in v))
    if length <= 1.0e-12:
        raise ContractError(f"{label} cannot have zero length")
    return tuple(value / length for value in v)



def _interpolate_authored_look(
    left: DroneWaypoint,
    right: DroneWaypoint,
    amount: float,
) -> tuple[float,float,float] | None:
    if not left.has_look_direction and not right.has_look_direction:
        return None
    if left.has_look_direction:
        a=(float(left.look_right),float(left.look_up),float(left.look_forward))
    else:
        a=(float(right.look_right),float(right.look_up),float(right.look_forward))
    if right.has_look_direction:
        b=(float(right.look_right),float(right.look_up),float(right.look_forward))
    else:
        b=a
    amount=max(0.0,min(1.0,float(amount)))
    dot=sum(x*y for x,y in zip(a,b))
    raw=tuple(a[i]*(1.0-amount)+b[i]*amount for i in range(3))
    length=sqrt(sum(value*value for value in raw))
    if length>1.0e-8:
        return tuple(value/length for value in raw)
    # Deterministic antipodal fallback: rotate through an orthogonal axis.
    candidate=(a[2],0.0,-a[0])
    candidate_length=sqrt(sum(value*value for value in candidate))
    if candidate_length<=1.0e-8:
        candidate=(0.0,a[2],-a[1])
        candidate_length=sqrt(sum(value*value for value in candidate))
    orthogonal=tuple(value/candidate_length for value in candidate)
    angle=pi*amount
    return _normalize_strict(
        tuple(a[i]*cos(angle)+orthogonal[i]*sin(angle) for i in range(3)),
        label="interpolated per-waypoint look direction",
    )


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
        target_distance = total * frame / float(max(1, frame_count - 1))
        segment = len(lengths) - 1
        for index, end in enumerate(cumulative[1:]):
            if target_distance <= end + 1.0e-12:
                segment = index
                break
        left = points[segment]
        right = points[segment + 1]
        length = lengths[segment]
        amount = (
            0.0 if length <= 1.0e-12
            else (target_distance - cumulative[segment]) / length
        )
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
        authored_look=_interpolate_authored_look(left,right,amount)
        if authored_look is not None:
            look=authored_look
        elif mission.orientation_mode == "LOOK_AT_TARGET":
            target = mission.look_target
            if target is None:
                raise ContractError(
                    f"Mission {mission.name} LOOK_AT_TARGET has no target"
                )
            look = _normalize_strict((
                target.right - position.right,
                target.up - position.up,
                target.forward - position.forward,
            ), label=f"Mission {mission.name} LOOK_AT_TARGET direction")
        elif mission.orientation_mode == "MANUAL_DIRECTION":
            manual = mission.manual_direction
            if manual is None:
                raise ContractError(
                    f"Mission {mission.name} MANUAL_DIRECTION has no direction"
                )
            look = _normalize_strict(
                (manual.right, manual.up, manual.forward),
                label=f"Mission {mission.name} MANUAL_DIRECTION",
            )
        else:
            look = tangent

        result.append(position.to_relative(
            look_right=look[0],
            look_up=look[1],
            look_forward=look[2],
        ))
    return CameraPath(mission.name, tuple(result))

def _sample_spin(mission: DroneMission, frame_count: int) -> CameraPath:
    anchor = mission.waypoints[0]
    result = []
    pitch=mission.spin_pitch_deg*pi/180.0
    yaw_start=mission.spin_yaw_start_deg*pi/180.0
    cp=cos(pitch)
    for frame in range(frame_count):
        angle = yaw_start + 2.0 * pi * frame / float(frame_count)
        result.append(anchor.to_relative(
            look_right=sin(angle)*cp,
            look_up=sin(pitch),
            look_forward=cos(angle)*cp,
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



def reorient_path_for_mission(
    mission: DroneMission,
    path: CameraPath,
) -> CameraPath:
    """Reapply mission orientation after collision holds alter emitted positions."""

    if mission.mode=="SPIN_360":
        return path
    waypoints=path.waypoints
    if not waypoints:
        raise ContractError(f"Mission {mission.name} emitted path is empty")

    result=[]
    has_per_waypoint_aim=any(control.has_look_direction for control in mission.waypoints)
    for index,point in enumerate(waypoints):
        if has_per_waypoint_aim:
            look=_normalize_strict(
                (point.look_right,point.look_up,point.look_forward),
                label=f"Mission {mission.name} interpolated per-waypoint direction",
            )
        elif mission.orientation_mode=="LOOK_AT_TARGET":
            target=mission.look_target
            if target is None:
                raise ContractError(f"Mission {mission.name} LOOK_AT_TARGET has no target")
            look=_normalize_strict(
                (
                    target.right-point.right,
                    target.up-point.up,
                    target.forward-point.forward,
                ),
                label=f"Mission {mission.name} LOOK_AT_TARGET direction",
            )
        elif mission.orientation_mode=="MANUAL_DIRECTION":
            manual=mission.manual_direction
            if manual is None:
                raise ContractError(f"Mission {mission.name} MANUAL_DIRECTION has no direction")
            look=_normalize_strict(
                (manual.right,manual.up,manual.forward),
                label=f"Mission {mission.name} MANUAL_DIRECTION",
            )
        else:
            # Preserve the original sampled tangent when a hold creates repeated
            # positions; otherwise derive the tangent from the emitted path.
            neighbor=None
            for candidate_index in range(index+1,len(waypoints)):
                candidate=waypoints[candidate_index]
                delta=(
                    candidate.right-point.right,
                    candidate.up-point.up,
                    candidate.forward-point.forward,
                )
                if sqrt(sum(v*v for v in delta))>1.0e-12:
                    neighbor=delta
                    break
            if neighbor is None:
                for candidate_index in range(index-1,-1,-1):
                    candidate=waypoints[candidate_index]
                    delta=(
                        point.right-candidate.right,
                        point.up-candidate.up,
                        point.forward-candidate.forward,
                    )
                    if sqrt(sum(v*v for v in delta))>1.0e-12:
                        neighbor=delta
                        break
            if neighbor is None:
                look=(point.look_right,point.look_up,point.look_forward)
            else:
                look=_normalize(neighbor)

        result.append(
            RelativeWaypoint(
                right=point.right,
                up=point.up,
                forward=point.forward,
                look_right=look[0],
                look_up=look[1],
                look_forward=look[2],
            )
        )
    return CameraPath(path.name,tuple(result))


def apply_hold_and_resume_clearance(
    path: CameraPath,
    clearance_query,
    *,
    min_clearance: float,
    segment_is_blocked=None,
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

        # Endpoint-only clearance can miss a thin wall between two valid camera
        # frames. When a segment callback is available, every translation from
        # the last emitted safe position to the requested candidate must also
        # be collision-free. During a hold this prevents "teleporting" through
        # a facade when the authored route later emerges on the other side.
        if safe and last_safe is not None and segment_is_blocked is not None:
            safe = not bool(segment_is_blocked(last_safe, candidate))

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
    target = DroneWaypoint(
        float(footprint.center_right),
        0.5 * (float(footprint.up_min) + float(footprint.up_max)),
        float(footprint.center_forward),
    )
    mission = DroneMission(
        name="drone_1",
        mode="PATH",
        enabled=True,
        orientation_mode="LOOK_AT_TARGET",
        look_target=target,
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
