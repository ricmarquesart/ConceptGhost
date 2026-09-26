from __future__ import annotations

import argparse
import json
import os
import py_compile
from pathlib import Path


FILES=("gate_output_contract.py","reconstruction_runtime.py","gate7_runtime.py")


def default_comfy_root() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or "")/"Comfy-Desktop"/"ComfyUI-Installs"/"ComfyUI"/"ComfyUI"


def _production_workflows(comfy_root: Path):
    roots=(
        comfy_root/"user"/"default"/"workflows",
        Path(os.environ.get("LOCALAPPDATA") or "")/"ConceptGhost"/"internal"/"workflows",
    )
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*.json"):
            try:
                data=json.loads(path.read_text(encoding="utf-8-sig"))
            except Exception:
                continue
            nodes=data.get("nodes")
            if not isinstance(nodes,list):
                continue
            ids={node.get("id") for node in nodes if isinstance(node,dict)}
            if {2300,2400}.issubset(ids):
                yield path,data


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--comfy-root",type=Path,default=default_comfy_root())
    args=parser.parse_args()
    comfy_root=args.comfy_root.resolve()
    node_root=comfy_root/"custom_nodes"/"ConceptGhost_P10_Lab"
    for name in FILES:
        path=node_root/name
        if not path.is_file():
            raise RuntimeError("Missing installed R6K source: "+str(path))
        py_compile.compile(str(path),doraise=True)

    contract=(node_root/"gate_output_contract.py").read_text(encoding="utf-8-sig")
    for token in (
        "_MAYA_CM_PER_METER = 100.0",
        '"reconstructed_mesh_MAYA_CM.obj"',
        '"P10_ACCEPTED_FILL_MAYA_CM.obj"',
        '"P9_PLUS_P10_FILLED_CANDIDATE_MAYA_CM.obj"',
        '"P10_ACCEPTED_FILL"',\n        '"P9_PLUS_P10_FILLED_CANDIDATE"',
        "P9/P10 canonical meters -> Maya centimeters x100",
    ):
        if token not in contract:
            raise RuntimeError("R6K Maya/output token missing: "+token)

    recon=(node_root/"reconstruction_runtime.py").read_text(encoding="utf-8-sig")
    if "publish_gate6_output_tree(" not in recon:
        raise RuntimeError("Gate 6 automatic output publication is not wired")

    gate7=(node_root/"gate7_runtime.py").read_text(encoding="utf-8-sig")
    if gate7.count("publish_gate7_output_tree(") < 2:
        raise RuntimeError("Gate 7 must publish outputs on fresh and reused runs")
    if 'reused["gate_output_autopublished"] = True' not in gate7:
        raise RuntimeError("Gate 7 resumed-run autopublish marker missing")

    workflows=list(_production_workflows(comfy_root))
    if not workflows:
        raise RuntimeError("No current ConceptGhost Workflow 02 production graph found")
    verified=[]
    for path,data in workflows:
        links=data.get("links") if isinstance(data.get("links"),list) else []
        has_link=any(
            isinstance(link,list) and len(link)>=5 and link[1]==2300 and link[3]==2400
            for link in links
        )
        extra=data.get("extra") if isinstance(data.get("extra"),dict) else {}
        cg=extra.get("conceptghost") if isinstance(extra.get("conceptghost"),dict) else {}
        if has_link and cg.get("r6k_gate7_maya_autopublish") is True:
            verified.append(path)
    if not verified:
        raise RuntimeError("Workflow 02 does not contain verified Reconstruction -> Gate 7 automatic path")

    print("[PASS] R6K r2 source verified.")
    print("[PASS] Gate 6 automatic publication is wired.")
    print("[PASS] Gate 7 fresh/resumed automatic publication is wired.")
    print("[PASS] Maya meter->centimeter bridge is present.")
    print("[PASS] Workflow 02 Reconstruction -> Gate 7 path verified in:")
    for path in verified:
        print("  "+str(path))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
