from __future__ import annotations

from math import isfinite, sqrt
from typing import Iterable

from .contracts import ContractError
from .drone_route_plan import DroneRoutePlan
from .path_planner import CameraPath


_STATUS_ORDER={"PASS":0,"WARN":1,"FAIL":2}


def _distance(a,b) -> float:
    return sqrt(
        (float(a.right)-float(b.right))**2
        +(float(a.up)-float(b.up))**2
        +(float(a.forward)-float(b.forward))**2
    )


def _path_length(points) -> float:
    if len(points)<2:
        return 0.0
    return sum(_distance(points[index],points[index+1]) for index in range(len(points)-1))


def _finite_or_none(value):
    if value is None:
        return None
    try:
        value=float(value)
    except (TypeError,ValueError):
        return None
    return value if isfinite(value) else None


def _status_max(statuses: Iterable[str]) -> str:
    current="PASS"
    for status in statuses:
        normalized=str(status or "FAIL").upper()
        if normalized not in _STATUS_ORDER:
            normalized="FAIL"
        if _STATUS_ORDER[normalized]>_STATUS_ORDER[current]:
            current=normalized
    return current


def build_drone_route_diagnostics(
    plan: DroneRoutePlan | None,
    emitted_paths: tuple[CameraPath,...],
    coverage_by_path: dict[str,list[float]],
    hole_fraction_by_path: dict[str,list[float]],
    hold_reports: list[dict] | tuple[dict,...],
    *,
    route_authority: str,
    route_plan_sha256: str | None,
    scene_contract_id: str,
    source_run_id: str,
) -> dict[str,object]:
    """Build the pre-WAN artist route quality summary.

    Status semantics are deliberately conservative and deterministic:
    - FAIL: the emitted mission/frame contract no longer matches the authored plan
      or required metrics are missing.
    - WARN: the contract is valid but HOLD_AND_RESUME had to suppress one or more
      requested frames, meaning the artist-authored route intersected known P9
      geometry; an all-zero-P9-coverage mission is also WARN.
    - PASS: contract is exact and no collision hold was required.

    Coverage is otherwise descriptive. Low coverage is not treated as failure
    because WAN exists specifically to complete regions absent from P9.
    """

    authority=str(route_authority or "").strip().upper()
    scene=str(scene_contract_id or "").strip()
    run=str(source_run_id or "").strip()
    if not authority or not scene or not run:
        raise ContractError("Route diagnostics require route authority, scene contract and source run")

    emitted_by_name={path.name:path for path in emitted_paths}
    if len(emitted_by_name)!=len(emitted_paths):
        raise ContractError("Emitted drone path names must be unique")

    holds={}
    for raw in hold_reports or ():
        if not isinstance(raw,dict):
            raise ContractError("Hold reports must be JSON-like objects")
        name=str(raw.get("mission_name") or "").strip()
        if not name:
            raise ContractError("Hold report mission_name cannot be empty")
        if name in holds:
            raise ContractError(f"Duplicate hold report for {name}")
        holds[name]=raw

    if plan is None:
        mission_order=[path.name for path in emitted_paths]
        authored_by_name={}
        expected_counts={path.name:len(path.waypoints) for path in emitted_paths}
        mode_by_name={path.name:"AUTO" for path in emitted_paths}
        min_clearance=None
    else:
        active=plan.active_missions
        mission_order=[mission.name for mission in active]
        authored_by_name={mission.name:mission for mission in active}
        expected_counts={mission.name:plan.frames_per_drone for mission in active}
        mode_by_name={mission.name:mission.mode for mission in active}
        min_clearance=float(plan.min_clearance_m)

    global_order_status=(
        "PASS" if mission_order==[path.name for path in emitted_paths] else "FAIL"
    )

    missions=[]
    total_frames=0
    total_held=0
    for mission_index,name in enumerate(mission_order):
        alerts=[]
        emitted=emitted_by_name.get(name)
        expected_count=expected_counts.get(name)
        actual_count=len(emitted.waypoints) if emitted is not None else 0
        total_frames+=actual_count

        if emitted is None:
            alerts.append("EMITTED_MISSION_MISSING")
        if expected_count!=actual_count:
            alerts.append("FRAME_COUNT_MISMATCH")

        coverage=[float(value) for value in coverage_by_path.get(name,[])]
        holes=[float(value) for value in hole_fraction_by_path.get(name,[])]
        if len(coverage)!=actual_count:
            alerts.append("COVERAGE_FRAME_COUNT_MISMATCH")
        if len(holes)!=actual_count:
            alerts.append("HOLE_FRAME_COUNT_MISMATCH")

        report=holds.get(name,{})
        held=int(report.get("held_frame_count") or 0)
        resumed=int(report.get("resumed_frame_count") or 0)
        total_held+=held
        if held>0:
            alerts.append("COLLISION_HOLD_APPLIED")

        max_coverage=max(coverage) if coverage else None
        if coverage and max_coverage<=1.0e-9:
            alerts.append("NO_P9_COVERAGE")

        fail_alerts={
            "EMITTED_MISSION_MISSING",
            "FRAME_COUNT_MISMATCH",
            "COVERAGE_FRAME_COUNT_MISMATCH",
            "HOLE_FRAME_COUNT_MISMATCH",
        }
        if any(alert in fail_alerts for alert in alerts):
            status="FAIL"
        elif alerts:
            status="WARN"
        else:
            status="PASS"

        authored=authored_by_name.get(name)
        authored_length=(
            _path_length(authored.waypoints)
            if authored is not None and authored.mode=="PATH"
            else 0.0
        )
        emitted_length=_path_length(emitted.waypoints) if emitted is not None else 0.0

        missions.append({
            "mission_index":mission_index,
            "name":name,
            "mode":mode_by_name.get(name),
            "status":status,
            "alerts":alerts,
            "expected_frame_count":expected_count,
            "emitted_frame_count":actual_count,
            "authored_route_length_m":authored_length,
            "emitted_translation_length_m":emitted_length,
            "held_frame_count":held,
            "held_frame_fraction":(
                held/float(actual_count) if actual_count>0 else None
            ),
            "resumed_frame_count":resumed,
            "minimum_candidate_clearance_m":_finite_or_none(
                report.get("minimum_candidate_clearance")
            ),
            "minimum_output_clearance_m":_finite_or_none(
                report.get("minimum_output_clearance")
            ),
            "required_clearance_m":min_clearance,
            "p9_coverage":{
                "min":min(coverage) if coverage else None,
                "mean":sum(coverage)/len(coverage) if coverage else None,
                "max":max_coverage,
            },
            "hole_fraction":{
                "min":min(holes) if holes else None,
                "mean":sum(holes)/len(holes) if holes else None,
                "max":max(holes) if holes else None,
            },
        })

    global_status=_status_max(
        [global_order_status]+[mission["status"] for mission in missions]
    )
    global_alerts=[]
    if global_order_status=="FAIL":
        global_alerts.append("MISSION_ORDER_MISMATCH")
    if total_held>0:
        global_alerts.append("ONE_OR_MORE_MISSIONS_REQUIRED_COLLISION_HOLD")

    return {
        "schema":"ConceptGhost.P10DroneRouteDiagnostics.v0.1",
        "status":global_status,
        "alerts":global_alerts,
        "route_authority":authority,
        "route_plan_sha256":route_plan_sha256,
        "scene_contract_id":scene,
        "source_run_id":run,
        "mission_order":mission_order,
        "active_drone_count":len(mission_order),
        "total_emitted_frame_count":total_frames,
        "total_held_frame_count":total_held,
        "mission_order_exact":global_order_status=="PASS",
        "status_policy":{
            "PASS":"Exact mission/frame contract and no collision hold",
            "WARN":"Contract valid but collision hold or zero-P9-coverage advisory present",
            "FAIL":"Mission/frame/diagnostic contract mismatch",
            "coverage_note":"Low P9 coverage is descriptive; WAN is expected to fill missing P9 regions",
        },
        "missions":missions,
    }
