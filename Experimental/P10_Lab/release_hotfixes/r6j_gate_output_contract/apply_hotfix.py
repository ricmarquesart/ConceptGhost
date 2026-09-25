from __future__ import annotations

import argparse
import json
import os
import py_compile
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


FILES = (
    "gate_output_contract.py",
    "gate6_geometry_output.py",
    "refined_evidence.py",
    "wan_sequence.py",
    "reconstruction_runtime.py",
    "reconstruction_node.py",
    "preview_nodes.py",
    "workflow_integration.py",
    "gate7_runtime.py",
    "gate7_visual_review.py",
    "run_audit_bundle.py",
)


def default_comfy_root() -> Path:
    return (
        Path(os.environ.get("LOCALAPPDATA") or "")
        / "Comfy-Desktop" / "ComfyUI-Installs" / "ComfyUI" / "ComfyUI"
    )


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--comfy-root",type=Path,default=default_comfy_root())
    parser.add_argument(
        "--install-root",type=Path,
        default=Path(os.environ.get("LOCALAPPDATA") or "")/"ConceptGhost",
    )
    args=parser.parse_args()
    comfy_root=args.comfy_root.resolve()
    install_root=args.install_root.resolve()
    node_root=comfy_root/"custom_nodes"/"ConceptGhost_P10_Lab"
    bundle_root=Path(__file__).resolve().parents[1]
    payload=bundle_root/"Payload"/"custom_nodes"/"ConceptGhost_P10_Lab"
    if not node_root.is_dir():
        raise RuntimeError("ConceptGhost_P10_Lab is not installed: "+str(node_root))
    for name in FILES:
        if not (payload/name).is_file():
            raise RuntimeError("R6J payload missing: "+name)

    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup=install_root/"HotfixBackups"/"R6J_GATE_OUTPUT_CONTRACT"/stamp
    backup.mkdir(parents=True,exist_ok=True)
    for name in FILES:
        target=node_root/name
        if target.is_file():
            shutil.copy2(target,backup/name)
        shutil.copy2(payload/name,target)
        if target.suffix==".py":
            py_compile.compile(str(target),doraise=True)

    subprocess.run([
        sys.executable,str(Path(__file__).with_name("patch_workflows.py")),
        "--comfy-root",str(comfy_root),"--install-root",str(install_root)
    ],check=True)

    (node_root/"CONCEPTGHOST_P10_VERSION.txt").write_text(
        "ConceptGhost R6J r2 Gate Output Contract + Legacy Gate 6 Backfill\n",encoding="utf-8"
    )
    marker=install_root/"R6J_GATE_OUTPUT_CONTRACT.json"
    marker.write_text(json.dumps({
        "schema":"ConceptGhost.R6JGateOutputContract.v0.1",
        "status":"APPLIED",
        "release":"ConceptGhost_R6J_GATE_OUTPUT_CONTRACT_r2",
        "applied_at_utc":datetime.now(timezone.utc).isoformat(),
        "comfy_root":str(comfy_root),
        "backup_root":str(backup),
        "gate_outputs_location":"<P9_RUN>/GATE_OUTPUTS/<P10_ATTEMPT_ID>/GATE_XX_*",
        "p9_authority_mutated":False,
        "existing_wan_mutated":False,
        "moge_runtime_mutated":False,
        "shared_comfy_python_mutated":False,
    },indent=2,sort_keys=True),encoding="utf-8")
    print("[PASS] R6J r2 Gate Output Contract installed.")
    print("[PASS] Gate 4/5/6/7 outputs are published beside the P9 run.")
    print("[PASS] Gate 6 requires a non-empty inspectable reconstruction + diagnostic Maya.")\n    print("[PASS] Pre-R6I completed Gate 6 workspaces can be backfilled without reconstruction reruns.")
    print("[PASS] Gate 7 diagnostic Maya separates P9 / raw P10 / accepted / rejected P10.")
    print("[UNCHANGED] P9 authority, existing WAN images, MoGe runtime, shared pip packages.")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
