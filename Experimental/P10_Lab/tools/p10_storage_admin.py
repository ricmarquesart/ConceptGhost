from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

LAB=Path(__file__).resolve().parents[1]
if str(LAB) not in sys.path:
    sys.path.insert(0,str(LAB))

def _print(payload):
    print(json.dumps(payload,indent=2,sort_keys=True))


def _attempts_by_status(report,statuses):
    wanted={str(value).upper() for value in statuses}
    return [
        item["path"] for item in report.get("attempts",[])
        if str(item.get("status") or "").upper() in wanted
    ]


def main(argv=None):
    parser=argparse.ArgumentParser(
        description="ConceptGhost P10 storage report / fail-closed cleanup utility."
    )
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--output-root",help="ComfyUI output directory")
    source.add_argument("--comfy-root",help="ComfyUI root; folder_paths will resolve its active output directory")
    parser.add_argument(
        "action",
        choices=(
            "report","open","clean-route-editor","clean-failed-attempts",
            "clean-all-attempts","reset-p10-state",
        ),
    )
    parser.add_argument("--confirm",default="")
    args=parser.parse_args(argv)

    if args.comfy_root:
        comfy_root=Path(args.comfy_root).expanduser().resolve()
        if str(comfy_root) not in sys.path:
            sys.path.insert(0,str(comfy_root))
        custom_nodes=comfy_root/"custom_nodes"
        if str(custom_nodes) not in sys.path:
            sys.path.insert(0,str(custom_nodes))
        import folder_paths
        from ConceptGhost_P10_Lab.storage_lifecycle import build_storage_report,cleanup_p10_owned_cache
        output=Path(folder_paths.get_output_directory()).resolve()
    else:
        if str(LAB) not in sys.path:
            sys.path.insert(0,str(LAB))
        from p10_lab.storage_lifecycle import build_storage_report,cleanup_p10_owned_cache
        output=Path(args.output_root).expanduser().resolve()
    report=build_storage_report(output)

    if args.action=="report":
        _print(report)
        return 0

    if args.action=="open":
        root=Path(report["roots"]["conceptghost_root"])
        root.mkdir(parents=True,exist_ok=True)
        if os.name=="nt":
            os.startfile(str(root))
        else:
            print(root)
        return 0

    if args.action=="clean-route-editor":
        _print(cleanup_p10_owned_cache(output,delete_route_editor_cache=True))
        return 0

    if args.action=="clean-failed-attempts":
        paths=_attempts_by_status(
            report,("ACTIVE","FAILED","FAIL","COMPLETE_GEOMETRY_FAIL","INVALID_MANIFEST")
        )
        _print(cleanup_p10_owned_cache(output,delete_attempt_paths=paths))
        return 0

    if args.confirm!="DELETE_P10":
        parser.error("destructive action requires --confirm DELETE_P10")

    if args.action=="clean-all-attempts":
        paths=[item["path"] for item in report.get("attempts",[])]
        _print(cleanup_p10_owned_cache(output,delete_attempt_paths=paths))
        return 0

    if args.action=="reset-p10-state":
        paths=[item["path"] for item in report.get("attempts",[])]
        _print(cleanup_p10_owned_cache(
            output,
            delete_attempt_paths=paths,
            delete_route_editor_cache=True,
            delete_route_setup_state=True,
        ))
        return 0

    return 2


if __name__=="__main__":
    raise SystemExit(main())
