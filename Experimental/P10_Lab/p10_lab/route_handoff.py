from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .contracts import ContractError
from .drone_route_plan import parse_bound_route_plan
from .p9_boundary import validate_official_run


_ENTRY_SCHEMA="ConceptGhost.P10ProductionEntry.v0.1"


def _sha256_file(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path,label: str) -> dict:
    try:
        payload=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as error:
        raise ContractError(f"Cannot read {label} {path}: {error}") from error
    if not isinstance(payload,dict):
        raise ContractError(f"{label} must contain a JSON object")
    return payload


def commit_route_setup(
    run_dir: str | Path,
    route_plan_json: str,
    output_root: str | Path,
) -> dict[str,object]:
    """Persist an artist route without running WAN/Gate6 or modifying P9."""

    boundary=validate_official_run(run_dir)
    try:
        payload=json.loads(str(route_plan_json or "").strip())
    except json.JSONDecodeError as error:
        raise ContractError(f"route_plan_json is invalid JSON: {error}") from error
    if not isinstance(payload,dict):
        raise ContractError("route_plan_json must contain a JSON object")

    plan,authority,route_hash=parse_bound_route_plan(
        payload,
        expected_scene_contract_id=boundary.scene_contract_id,
        expected_source_run_id=boundary.run_id,
        require_hash=True,
    )
    authority=str(authority or "").upper()
    output_root=Path(output_root).resolve()
    output_root.mkdir(parents=True,exist_ok=True)

    if authority!="ARTIST_AUTHORED":
        # First Route Setup execution intentionally reaches this state: P9 has
        # been solved and the editor can now be used. This is not an error and
        # must not force WAN/Gate6 to run just to obtain the route workspace.
        waiting={
            "schema":_ENTRY_SCHEMA,
            "status":"WAITING_FOR_ARTIST_ROUTE",
            "production_ready":False,
            "route_authority":authority,
            "scene_contract_id":boundary.scene_contract_id,
            "source_run_id":boundary.run_id,
            "source_p9_run_dir":str(Path(run_dir).resolve()),
            "active_mission_count":len(plan.active_missions),
            "message":"Edit/confirm the route, then Queue Prompt again to commit the production entry.",
            "p9_authority_changed":False,
        }
        waiting_path=output_root/"route_setup_status.json"
        waiting_path.write_text(json.dumps(waiting,indent=2,sort_keys=True),encoding="utf-8")
        waiting["status_path"]=str(waiting_path)
        waiting["production_entry_path"]=""
        return waiting

    route_path=output_root/"committed_route.json"
    route_path.write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8")
    route_file_sha=_sha256_file(route_path)
    entry={
        "schema":_ENTRY_SCHEMA,
        "status":"READY",
        "production_ready":True,
        "created_at_utc":datetime.now(timezone.utc).isoformat(),
        "scene_contract_id":boundary.scene_contract_id,
        "source_run_id":boundary.run_id,
        "source_p9_run_dir":str(Path(run_dir).resolve()),
        "route_authority":authority,
        "route_plan_schema":payload.get("schema"),
        "route_plan_sha256":route_hash,
        "committed_route_path":str(route_path),
        "committed_route_file_sha256":route_file_sha,
        "active_mission_count":len(plan.active_missions),
        "p9_authority_changed":False,
        "handoff_policy":"P9_IMMUTABLE_ROUTE_SETUP_THEN_P10_PRODUCTION",
    }
    entry_path=output_root/"production_entry.json"
    entry_path.write_text(json.dumps(entry,indent=2,sort_keys=True),encoding="utf-8")
    entry["production_entry_path"]=str(entry_path)
    return entry


def load_production_entry(entry_path: str | Path) -> dict[str,object]:
    entry_path=Path(entry_path).resolve()
    entry=_read_json(entry_path,"P10 production entry")
    if entry.get("schema")!=_ENTRY_SCHEMA or entry.get("status")!="READY":
        raise ContractError("P10 production entry is not READY or has an unsupported schema")

    run_dir=Path(str(entry.get("source_p9_run_dir") or "")).resolve()
    boundary=validate_official_run(run_dir)
    if str(entry.get("scene_contract_id") or "")!=boundary.scene_contract_id:
        raise ContractError("Production entry scene_contract_id no longer matches P9")
    if str(entry.get("source_run_id") or "")!=boundary.run_id:
        raise ContractError("Production entry source_run_id no longer matches P9")

    route_path=Path(str(entry.get("committed_route_path") or "")).resolve()
    if not route_path.is_file():
        raise ContractError(f"Committed route is missing: {route_path}")
    actual_file_sha=_sha256_file(route_path)
    if actual_file_sha!=str(entry.get("committed_route_file_sha256") or ""):
        raise ContractError("Committed route file bytes changed after Route Setup")

    route_payload=_read_json(route_path,"committed route")
    _plan,authority,route_hash=parse_bound_route_plan(
        route_payload,
        expected_scene_contract_id=boundary.scene_contract_id,
        expected_source_run_id=boundary.run_id,
        require_hash=True,
    )
    if str(authority or "").upper()!="ARTIST_AUTHORED":
        raise ContractError("P10 Production requires ARTIST_AUTHORED route authority")
    if route_hash!=str(entry.get("route_plan_sha256") or ""):
        raise ContractError("Production entry route hash does not match committed route")

    return {
        **entry,
        "production_entry_path":str(entry_path),
        "source_p9_run_dir":str(run_dir),
        "route_plan_json":json.dumps(route_payload,indent=2,sort_keys=True),
        "validated":True,
    }


class ConceptGhostP10RouteCommit:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required":{
                "run_dir":("STRING",{"forceInput":True}),
                "route_plan_json":("STRING",{"forceInput":True}),
            }
        }

    RETURN_TYPES=("STRING","STRING")
    RETURN_NAMES=("production_entry_path","diagnostics_json")
    FUNCTION="commit"
    CATEGORY="ConceptGhost/P10 Refined"
    OUTPUT_NODE=True

    def commit(self,run_dir,route_plan_json):
        import folder_paths
        boundary=validate_official_run(run_dir)
        root=(
            Path(folder_paths.get_output_directory())
            /"conceptghost"/"p10_route_setup"/boundary.run_id
        )
        result=commit_route_setup(run_dir,route_plan_json,root)
        rendered=json.dumps(result,indent=2,sort_keys=True)
        return {
            "ui":{"text":[rendered]},
            "result":(str(result.get("production_entry_path") or ""),rendered),
        }


class ConceptGhostP10ProductionEntryLoader:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required":{
                "production_entry_path":(
                    "STRING",
                    {"default":"","multiline":False,"dynamicPrompts":False},
                ),
            }
        }

    RETURN_TYPES=("STRING","STRING","STRING")
    RETURN_NAMES=("run_dir","route_plan_json","diagnostics_json")
    FUNCTION="load"
    CATEGORY="ConceptGhost/P10 Refined"

    @classmethod
    def IS_CHANGED(cls,production_entry_path):
        path=Path(str(production_entry_path or "")).expanduser()
        if not path.is_file():
            return str(production_entry_path or "")
        return _sha256_file(path)

    def load(self,production_entry_path):
        result=load_production_entry(production_entry_path)
        rendered=json.dumps(
            {key:value for key,value in result.items() if key!="route_plan_json"},
            indent=2,sort_keys=True,
        )
        return (
            str(result["source_p9_run_dir"]),
            str(result["route_plan_json"]),
            rendered,
        )
