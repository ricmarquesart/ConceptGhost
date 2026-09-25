from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def default_comfy_root() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or "")/"Comfy-Desktop"/"ComfyUI-Installs"/"ComfyUI"/"ComfyUI"


def output_candidates(comfy_root: Path):
    local=Path(os.environ.get("LOCALAPPDATA") or "")
    return [
        local/"Comfy-Desktop"/"ComfyUI-Shared"/"output",
        comfy_root/"output",
    ]


def latest_attempt(comfy_root: Path) -> tuple[Path,Path]:
    rows=[]
    for output in output_candidates(comfy_root):
        base=output/"conceptghost"/"p10_attempts"
        if not base.is_dir():
            continue
        for attempt_manifest in base.rglob("attempt_manifest.json"):
            attempt=attempt_manifest.parent
            wan=attempt/"gate5"/"wan_manifest.json"
            if wan.is_file() and (attempt/"gate6").is_dir():
                rows.append((max(wan.stat().st_mtime_ns,attempt_manifest.stat().st_mtime_ns),attempt,wan))
    if not rows:
        raise RuntimeError("No existing P10 attempt with Gate 5 + Gate 6 was found")
    rows.sort(key=lambda row:row[0],reverse=True)
    return rows[0][1],rows[0][2]


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--comfy-root",type=Path,default=default_comfy_root())
    parser.add_argument("--attempt-root",type=Path)
    args=parser.parse_args()
    comfy=args.comfy_root.resolve()
    custom_nodes=comfy/"custom_nodes"
    sys.path.insert(0,str(comfy))
    sys.path.insert(0,str(custom_nodes))
    from ConceptGhost_P10_Lab.gate_output_contract import (
        publish_gate1_to_gate3_snapshots,
        publish_gate4_output,
        publish_gate5_output,
        publish_gate6_output_tree,
        publish_gate7_output_tree,
    )

    if args.attempt_root:
        attempt=args.attempt_root.resolve()
        wan=attempt/"gate5"/"wan_manifest.json"
    else:
        attempt,wan=latest_attempt(comfy)
    if not wan.is_file():
        raise RuntimeError("WAN manifest missing: "+str(wan))
    payload=json.loads(wan.read_text(encoding="utf-8"))
    p9=Path(str(payload.get("source_p9_run_dir") or "")).expanduser().resolve()
    if not p9.is_dir():
        raise RuntimeError("P9 run not found from WAN manifest: "+str(p9))
    attempt_id=str(payload.get("p10_attempt_id") or attempt.name)

    print("============================================================")
    print("ConceptGhost R6J - Backfill Gate Outputs")
    print("============================================================")
    print("P9 run      : "+str(p9))
    print("P10 attempt : "+str(attempt))
    print("Output root : "+str(p9/"GATE_OUTPUTS"/attempt_id))
    print("No WAN, COLMAP, MoGe or geometry will be regenerated.")
    print("============================================================")

    rows=[]
    rows.extend(publish_gate1_to_gate3_snapshots(p9,attempt,p10_attempt_id=attempt_id))
    rows.append(publish_gate4_output(p9,attempt,p10_attempt_id=attempt_id))
    rows.append(publish_gate5_output(p9,attempt,p10_attempt_id=attempt_id))
    rows.append(publish_gate6_output_tree(p9,attempt,p10_attempt_id=attempt_id))
    if (attempt/"gate7"/"gate7_runtime_manifest.json").is_file():
        rows.append(publish_gate7_output_tree(p9,attempt,p10_attempt_id=attempt_id))

    print("")
    print("GATE STATUS")
    print("-"*78)
    for row in rows:
        print(
            f"Gate {int(row['gate']):02d}  "
            f"status={row['status']}  runtime={row['runtime_status']}  "
            f"functional={row['functional_status']}  quality={row.get('quality_status')}"
        )
        if row.get("missing_required_outputs"):
            print("  missing: "+", ".join(row["missing_required_outputs"]))
    print("")
    print("[PASS] Gate output folders were generated from the existing run.")
    print("[INFO] Open GATE_OUTPUT_INDEX.json beside RUN_AUDIT_BUNDLE.zip.")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
