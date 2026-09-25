from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil


def _rect(nodes):
    xs=[]; ys=[]; xe=[]; ye=[]
    for node in nodes:
        pos=node.get("pos") or [0,0]
        size=node.get("size") or [500,300]
        x=float(pos[0]); y=float(pos[1]); w=float(size[0]); h=float(size[1])
        xs.append(x); ys.append(y); xe.append(x+w); ye.append(y+h)
    if not xs:
        return None
    pad=100
    return [min(xs)-pad,min(ys)-pad,max(xe)-min(xs)+2*pad,max(ye)-min(ys)+2*pad]


def patch_workflow(path: Path, backup_root: Path) -> bool:
    try:
        data=json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return False
    nodes=data.get("nodes")
    if not isinstance(nodes,list):
        return False
    by_id={node.get("id"):node for node in nodes if isinstance(node,dict)}
    if not {2100,2207,2300}.issubset(by_id):
        return False

    backup=backup_root/path.name
    suffix=1
    while backup.exists():
        backup=backup_root/f"{path.stem}_{suffix}{path.suffix}"
        suffix+=1
    backup.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(path,backup)

    titles={
        2100:"GATE 4 OUTPUT · DRONE/CAMERA · CONTROL FRAMES + MASKS + CAMERAS",
        2207:"GATE 5 OUTPUT · NEW VIEWS · WAN RAW + SOURCE-PRESERVED COMPOSITES",
        2208:"GATE 5 OUTPUT PREVIEW · GENERATED VS P9-PRESERVED",
        2300:"GATE 6 · RECONSTRUCT 3D · MUST OUTPUT NEW P10 GEOMETRY",
        2301:"GATE 6 OUTPUT · RAW P10 3D · PLY/OBJ/POINTS/DIAGNOSTIC MAYA",
        2400:"GATE 7 · P9 + P10 FUSION · PROVENANCE/CONFIDENCE/REJECTION OUTPUT",
    }
    for node_id,title in titles.items():
        if node_id in by_id:
            by_id[node_id]["title"]=title

    for node in nodes:
        node_type=str(node.get("type") or "")
        if "Gate7Runtime" in node_type:
            node["title"]="GATE 7 · P9 + P10 FUSION · OUTPUT = ACCEPT/REJECT + DIAGNOSTIC MAYA"

    groups=data.get("groups")
    if not isinstance(groups,list):
        groups=[]
    prefixes=("HANDOFF ·","GATE 4 ·","GATE 5 ·","GATE 6 ·","GATE 7 ·")
    groups=[
        g for g in groups
        if not (isinstance(g,dict) and str(g.get("title") or "").startswith(prefixes))
    ]
    fixed=[
        {
            "title":"HANDOFF · EXISTING P9 + COMMITTED DRONE ROUTE",
            "bounding":[8580,9200,2350,830],"color":"#455a64","font_size":26,"flags":{},
        },
        {
            "title":"GATE 4 · DRONES/CAMERAS · OUTPUT = ROUTE + CONTROL PNGs + MASKS + CAMERAS",
            "bounding":[10040,9430,2060,1110],"color":"#3f51b5","font_size":28,"flags":{},
        },
        {
            "title":"GATE 5 · NEW VIEWS · OUTPUT = RAW WAN + SOURCE-PRESERVED PNGs",
            "bounding":[12380,9400,2360,1510],"color":"#6a1b9a","font_size":28,"flags":{},
        },
        {
            "title":"GATE 6 · 3D RECONSTRUCTION · OUTPUT = POINTS + NEW MESH + DIAGNOSTIC .MA",
            "bounding":[14720,9400,1680,1080],"color":"#2e7d32","font_size":28,"flags":{},
        },
    ]
    groups.extend(fixed)

    gate7_nodes=[
        node for node in nodes
        if node.get("id")==2400 or "Gate7Runtime" in str(node.get("type") or "")
    ]
    rect=_rect(gate7_nodes)
    if rect:
        groups.append({
            "title":"GATE 7 · P9 + P10 FUSION · OUTPUT = P9/P10/ACCEPT/REJECT + DIAGNOSTIC .MA",
            "bounding":rect,"color":"#ef6c00","font_size":28,"flags":{},
        })
    data["groups"]=groups

    extra=data.get("extra") if isinstance(data.get("extra"),dict) else {}
    cg=extra.get("conceptghost") if isinstance(extra.get("conceptghost"),dict) else {}
    cg.update({
        "r6j_gate_output_contract":True,
        "gate_output_root":"<P9_RUN>/GATE_OUTPUTS/<P10_ATTEMPT_ID>",
        "runtime_pass_is_not_functional_pass":True,
        "gate6_required_product":"NONEMPTY_RAW_P10_3D_PLUS_DIAGNOSTIC_MAYA",
    })
    extra["conceptghost"]=cg
    data["extra"]=extra
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return True


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--comfy-root",type=Path,required=True)
    parser.add_argument("--install-root",type=Path,required=True)
    args=parser.parse_args()
    backup=args.install_root/"HotfixBackups"/"R6J_GATE_OUTPUT_CONTRACT"/"workflows"
    roots=[
        args.comfy_root/"user"/"default"/"workflows",
        args.install_root/"internal"/"workflows",
    ]
    patched=[]
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*.json"):
            if patch_workflow(path,backup):
                patched.append(path)
    if not patched:
        raise RuntimeError("No current ConceptGhost P10 Production workflow was found")
    print("[PASS] Patched Gate 4/5/6/7 labels in:")
    for path in patched:
        print("  "+str(path))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
