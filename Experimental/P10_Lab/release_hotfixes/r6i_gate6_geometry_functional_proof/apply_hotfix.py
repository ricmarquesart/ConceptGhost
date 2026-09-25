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
    "gate6_geometry_output.py",
    "reconstruction_runtime.py",
    "reconstruction_node.py",
    "preview_nodes.py",
    "workflow_integration.py",
)


def default_comfy_root() -> Path:
    return (
        Path(os.environ.get("LOCALAPPDATA") or "")
        / "Comfy-Desktop"
        / "ComfyUI-Installs"
        / "ComfyUI"
        / "ComfyUI"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--comfy-root", type=Path, default=default_comfy_root())
    parser.add_argument(
        "--install-root",
        type=Path,
        default=Path(os.environ.get("LOCALAPPDATA") or "") / "ConceptGhost",
    )
    args = parser.parse_args()

    comfy_root = args.comfy_root.resolve()
    install_root = args.install_root.resolve()
    node_root = comfy_root / "custom_nodes" / "ConceptGhost_P10_Lab"
    bundle_root = Path(__file__).resolve().parents[1]
    payload = bundle_root / "Payload" / "custom_nodes" / "ConceptGhost_P10_Lab"

    if not node_root.is_dir():
        raise RuntimeError("ConceptGhost_P10_Lab is not installed: " + str(node_root))
    for name in FILES:
        if not (payload / name).is_file():
            raise RuntimeError("Hotfix payload missing: " + name)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = install_root / "HotfixBackups" / "R6I_GATE6_GEOMETRY_PROOF" / stamp
    backup_root.mkdir(parents=True, exist_ok=True)

    for name in FILES:
        target = node_root / name
        if target.is_file():
            shutil.copy2(target, backup_root / name)
        shutil.copy2(payload / name, target)
        py_compile.compile(str(target), doraise=True)

    patcher = Path(__file__).with_name("patch_workflows.py")
    subprocess.run(
        [
            sys.executable,
            str(patcher),
            "--comfy-root", str(comfy_root),
            "--install-root", str(install_root),
        ],
        check=True,
    )

    (node_root / "CONCEPTGHOST_P10_VERSION.txt").write_text(
        "ConceptGhost R6I Gate 6 Geometry Functional Proof r1\n",
        encoding="utf-8",
    )

    marker = install_root / "R6I_GATE6_GEOMETRY_FUNCTIONAL_PROOF.json"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        json.dumps(
            {
                "schema": "ConceptGhost.R6IGate6GeometryFunctionalProof.v0.1",
                "status": "APPLIED",
                "release": "ConceptGhost_R6I_GATE6_GEOMETRY_FUNCTIONAL_PROOF_r1",
                "comfy_root": str(comfy_root),
                "node_root": str(node_root),
                "backup_root": str(backup_root),
                "applied_at_utc": datetime.now(timezone.utc).isoformat(),
                "p9_authority_mutated": False,
                "wan_data_mutated": False,
                "shared_comfy_python_mutated": False,
                "moge_runtime_mutated": False,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print("[PASS] R6I Gate 6 geometry functional proof installed.")
    print("[PASS] Gate 6 now publishes raw P10 PLY + OBJ + dense points before Gate 7.")
    print("[PASS] Gate 4/5/6 workflow groups were labeled.")
    print("[PASS] No P9 authority, WAN data, MoGe runtime or shared pip packages were changed.")
    print("[INFO] Run 02_VERIFY_GATE6_GEOMETRY_PROOF.bat next.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
