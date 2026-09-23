from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite, sqrt

from .contracts import ContractError
from .drone_route_plan import DroneRoutePlan, DroneMission, DroneWaypoint
from .mesh_clearance import ClearanceCloud
from .path_planner import RelativeWaypoint


@dataclass(frozen=True)
class SegmentCollisionReport:
    segment_index: int
    blocked: bool
    sample_count: int
    first_blocked_t: float | None
    last_blocked_t: float | None
    minimum_blocked_clearance: float | None

    def to_dict(self) -> dict[str, object]:
        return {
            "segment_index": self.segment_index,
            "blocked": self.blocked,
            "sample_count": self.sample_count,
            "first_blocked_t": self.first_blocked_t,
            "last_blocked_t": self.last_blocked_t,
            "minimum_blocked_clearance": self.minimum_blocked_clearance,
        }


@dataclass(frozen=True)
class MissionCollisionReport:
    mission_name: str
    mode: str
    blocked: bool
    start_blocked: bool
    blocked_segment_count: int
    segment_count: int
    segments: tuple[SegmentCollisionReport, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "mission_name": self.mission_name,
            "mode": self.mode,
            "blocked": self.blocked,
            "start_blocked": self.start_blocked,
            "blocked_segment_count": self.blocked_segment_count,
            "segment_count": self.segment_count,
            "segments": [segment.to_dict() for segment in self.segments],
        }


@dataclass(frozen=True)
class RouteCollisionReport:
    min_clearance: float
    sample_step: float
    blocked_mission_count: int
    blocked_segment_count: int
    missions: tuple[MissionCollisionReport, ...]
    policy: str = "P9_PRIMARYMESH_SURFACE_PREFLIGHT_V0_1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "ConceptGhost.P10DroneRouteCollisionReport.v0.1",
            "policy": self.policy,
            "min_clearance": self.min_clearance,
            "sample_step": self.sample_step,
            "blocked_mission_count": self.blocked_mission_count,
            "blocked_segment_count": self.blocked_segment_count,
            "missions": [mission.to_dict() for mission in self.missions],
        }


def _relative(point: DroneWaypoint) -> RelativeWaypoint:
    return point.to_relative()


def _distance(a: DroneWaypoint, b: DroneWaypoint) -> float:
    dr=a.right-b.right
    du=a.up-b.up
    df=a.forward-b.forward
    return sqrt(dr*dr+du*du+df*df)


def _segment_report(
    cloud: ClearanceCloud,
    start: DroneWaypoint,
    end: DroneWaypoint,
    *,
    segment_index: int,
    min_clearance: float,
    sample_step: float,
    max_samples_per_segment: int,
) -> SegmentCollisionReport:
    length=_distance(start,end)
    count=max(
        2,
        min(
            max_samples_per_segment,
            ceil(length/sample_step)+1,
        ),
    )
    first=None
    last=None
    minimum=None
    denominator=float(max(1,count-1))
    for index in range(count):
        t=index/denominator
        right=start.right+(end.right-start.right)*t
        up=start.up+(end.up-start.up)*t
        forward=start.forward+(end.forward-start.forward)*t
        clearance=cloud.clearance_below(right,up,forward,min_clearance)
        if clearance is None:
            continue
        if first is None:
            first=t
        last=t
        if minimum is None or clearance<minimum:
            minimum=clearance
    return SegmentCollisionReport(
        segment_index=segment_index,
        blocked=first is not None,
        sample_count=count,
        first_blocked_t=first,
        last_blocked_t=last,
        minimum_blocked_clearance=minimum,
    )


def preflight_drone_route_plan(
    plan: DroneRoutePlan,
    cloud: ClearanceCloud,
    *,
    sample_step: float | None = None,
    max_samples_per_segment: int = 4096,
) -> RouteCollisionReport:
    """Evaluate artist-authored mission segments against current P9 geometry.

    This is a preflight diagnostic and safety contract, not an auto-rerouter.
    A blocked segment is preserved as authored so the artist can see and move
    it. Runtime HOLD_AND_RESUME later prevents emitted cameras from crossing it.
    """

    if not isinstance(plan,DroneRoutePlan):
        raise ContractError("plan must be a DroneRoutePlan")
    threshold=float(plan.min_clearance_m)
    if threshold<0.0 or not isfinite(threshold):
        raise ContractError("min_clearance_m must be finite and non-negative")
    step=(
        max(0.025,threshold*0.50)
        if sample_step is None
        else float(sample_step)
    )
    if step<=0.0 or not isfinite(step):
        raise ContractError("sample_step must be finite and positive")
    if type(max_samples_per_segment) is not int or max_samples_per_segment<2:
        raise ContractError("max_samples_per_segment must be an integer >= 2")

    missions=[]
    total_blocked_segments=0
    for mission in plan.active_missions:
        points=mission.waypoints
        start_clearance=cloud.clearance_below(
            points[0].right,
            points[0].up,
            points[0].forward,
            threshold,
        )
        start_blocked=start_clearance is not None

        if mission.mode=="SPIN_360":
            blocked=start_blocked
            report=MissionCollisionReport(
                mission_name=mission.name,
                mode=mission.mode,
                blocked=blocked,
                start_blocked=start_blocked,
                blocked_segment_count=1 if blocked else 0,
                segment_count=1,
                segments=(
                    SegmentCollisionReport(
                        segment_index=0,
                        blocked=blocked,
                        sample_count=1,
                        first_blocked_t=0.0 if blocked else None,
                        last_blocked_t=0.0 if blocked else None,
                        minimum_blocked_clearance=start_clearance,
                    ),
                ),
            )
            total_blocked_segments+=report.blocked_segment_count
            missions.append(report)
            continue

        segments=tuple(
            _segment_report(
                cloud,
                points[index],
                points[index+1],
                segment_index=index,
                min_clearance=threshold,
                sample_step=step,
                max_samples_per_segment=max_samples_per_segment,
            )
            for index in range(len(points)-1)
        )
        blocked_segment_count=sum(1 for segment in segments if segment.blocked)
        total_blocked_segments+=blocked_segment_count
        missions.append(
            MissionCollisionReport(
                mission_name=mission.name,
                mode=mission.mode,
                blocked=start_blocked or blocked_segment_count>0,
                start_blocked=start_blocked,
                blocked_segment_count=blocked_segment_count,
                segment_count=len(segments),
                segments=segments,
            )
        )

    return RouteCollisionReport(
        min_clearance=threshold,
        sample_step=step,
        blocked_mission_count=sum(1 for mission in missions if mission.blocked),
        blocked_segment_count=total_blocked_segments,
        missions=tuple(missions),
    )
