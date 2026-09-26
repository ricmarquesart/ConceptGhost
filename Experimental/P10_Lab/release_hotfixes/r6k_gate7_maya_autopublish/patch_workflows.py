from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil


def patch_workflow(path: Path, backup_root: Path) -> bool:
    try:
        data=json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return False
    nodes=data.get("nodes")
    if not isinstance(nodes,list):
        return False
    by_id={node.get("id"):node for node in nodes if isinstance(node,dict)}
    if not {2097,2300,2400}.issubset(by_id):
        return False
    links=data.get("links") if isinstance(data.get("links"),list) else []
    if not any(
        isinstance(link,list) and len(link)>=5 and link[1]==2300 and link[3]==2400
        for link in links
    ):
        raise RuntimeError(
            "ConceptGhost Workflow 02 found but Reconstruction -> Gate 7 link is missing: "
            + str(path)
        )

    backup=backup_root/path.name
    suffix=1
    while backup.exists():
        backup=backup_root/f"{path.stem}_{suffix}{path.suffix}"
        suffix+=1
    backup.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(path,backup)

    by_id[2300]["title"]="GATE 6 · AUTO OUTPUT · RAW P10 3D + MAYA-CM DIAGNOSTIC"
    by_id[2400]["title"]="GATE 7 · AUTO OUTPUT · P9 ORIGINAL + P10 FILL · MAYA COMPARISON"
    instruction=by_id[2097]
    values=instruction.get("widgets_values")
    if isinstance(values,list) and values:
        values[0]=(
            "WORKFLOW 02 — P10 PRODUCTION + GATE 7 AUTO OUTPUT\n\n"
            "RUN #3: clique Run UMA VEZ. Evidence → WAN → Gate 6 Reconstruction → Gate 7.\n\n"
            "AUTOMATIC OUTPUT CONTRACT: nenhum BAT de backfill e necessario em novas execucoes. "
            "Gate 1-7 sao publicados automaticamente em "
            "<P9_RUN>/GATE_OUTPUTS/<P10_ATTEMPT_ID>/GATE_XX_*.\n\n"
            "GATE 7 MAYA: abra GATE_07_P9_P10_FUSION/OUTPUTS/Gate07_Fusion_Diagnostic.ma. "
            "P9_ORIGINAL = mesh original; P10_RAW_RECONSTRUCTION = reconstrucao bruta; "
            "P10_ACCEPTED_FILL = somente faces aceitas para preencher/completar.\n\n"
            "A geometria canonica permanece em metros. O Maya usa centimetros; R6K aplica x100 "
            "somente nas representacoes diagnosticas e nas translacoes das cameras.\n\n"
            "Gate 8 continua bloqueado ate revisao visual."
        )

    extra=data.get("extra") if isinstance(data.get("extra"),dict) else {}
    cg=extra.get("conceptghost") if isinstance(extra.get("conceptghost"),dict) else {}
    cg.update({
        "r6k_gate7_maya_autopublish":True,
        "automatic_gate_output_root":"<P9_RUN>/GATE_OUTPUTS/<P10_ATTEMPT_ID>",
        "automatic_gate_output_range":"GATE_01..GATE_07",
        "gate7_maya_comparison":"GATE_07_P9_P10_FUSION/OUTPUTS/Gate07_Fusion_Diagnostic.ma",
        "maya_coordinate_bridge":"CANONICAL_METERS_TO_MAYA_CENTIMETERS_X100_DIAGNOSTIC_ONLY",
        "manual_backfill_required_for_future_runs":False,
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
    backup=args.install_root/"HotfixBackups"/"R6K_GATE7_MAYA_AUTOPUBLISH"/"workflows"
    roots=(
        args.comfy_root/"user"/"default"/"workflows",
        args.install_root/"internal"/"workflows",
    )
    patched=[]
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*.json"):
            if patch_workflow(path,backup):
                patched.append(path)
    if not patched:
        raise RuntimeError("No current ConceptGhost Workflow 02 production graph was found")
    print("[PASS] R6K patched Workflow 02 automatic Gate 7 output path in:")
    for path in patched:
        print("  "+str(path))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
