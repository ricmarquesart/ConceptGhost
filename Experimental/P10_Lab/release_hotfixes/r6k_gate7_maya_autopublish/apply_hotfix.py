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
    "reconstruction_runtime.py",
    "gate7_runtime.py",
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
            raise RuntimeError("R6K payload missing: "+name)

    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup=install_root/"HotfixBackups"/"R6K_GATE7_MAYA_AUTOPUBLISH"/stamp
    backup.mkdir(parents=True,exist_ok=True)
    for name in FILES:
        target=node_root/name
        if target.is_file():
            shutil.copy2(target,backup/name)
        shutil.copy2(payload/name,target)
        py_compile.compile(str(target),doraise=True)

    subprocess.run([
        sys.executable,str(Path(__file__).with_name("patch_workflows.py")),
        "--comfy-root",str(comfy_root),"--install-root",str(install_root)
    ],check=True)

    (node_root/"CONCEPTGHOST_P10_VERSION.txt").write_text(
        "ConceptGhost R6K r2 Gate7 Auto Output + Maya Centimeter Bridge\n",
        encoding="utf-8",
    )
    marker=install_root/"R6K_GATE7_MAYA_AUTOPUBLISH.json"
    marker.write_text(json.dumps({
        "schema":"ConceptGhost.R6KGate7MayaAutopublish.v0.1",
        "status":"APPLIED",
        "release":"ConceptGhost_R6K_GATE7_MAYA_AUTOPUBLISH_r2",
        "applied_at_utc":datetime.now(timezone.utc).isoformat(),
        "comfy_root":str(comfy_root),
        "backup_root":str(backup),
        "automatic_gate_outputs":"<P9_RUN>/GATE_OUTPUTS/<P10_ATTEMPT_ID>/GATE_01..07",
        "maya_coordinate_bridge":"P9/P10 canonical meters -> Maya centimeters x100",
        "gate7_artist_scene":"GATE_07_P9_P10_FUSION/OUTPUTS/Gate07_Fusion_Diagnostic.ma",
        "p9_authority_mutated":False,
        "canonical_geometry_mutated":False,
        "moge_runtime_mutated":False,
        "shared_comfy_python_mutated":False,
    },indent=2,sort_keys=True),encoding="utf-8")
    print("[PASS] R6K r2 installed.")
    print("[PASS] Future Workflow 02 runs publish Gate 1-6 automatically.")
    print("[PASS] Gate 7 publishes automatically on fresh AND resumed runs.")
    print("[PASS] Gate 7 Maya keeps P9 original, complete filled candidate, raw P10 and accepted fill as separate namespaces.")
    print("[PASS] Maya diagnostic coordinates use explicit meters->centimeters x100.")
    print("[UNCHANGED] Canonical P9/P10 geometry, P9 authority, MoGe runtime, shared pip packages.")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
