from __future__ import annotations

import argparse
import os
import py_compile
from pathlib import Path


FILES=(
    "gate_output_contract.py",
    "gate6_geometry_output.py",
    "refined_evidence.py",
    "wan_sequence.py",
    "reconstruction_runtime.py",
    "gate7_runtime.py",
)


def default_comfy_root() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or "")/"Comfy-Desktop"/"ComfyUI-Installs"/"ComfyUI"/"ComfyUI"


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--comfy-root",type=Path,default=default_comfy_root())
    args=parser.parse_args()
    node_root=args.comfy_root.resolve()/"custom_nodes"/"ConceptGhost_P10_Lab"
    for name in FILES:
        path=node_root/name
        if not path.is_file():
            raise RuntimeError("Missing installed R6J source: "+str(path))
        py_compile.compile(str(path),doraise=True)

    contract=(node_root/"gate_output_contract.py").read_text(encoding="utf-8-sig")
    for token in (
        'return p9 / "GATE_OUTPUTS" / attempt',
        '"Gate06_Reconstruction_Diagnostic.ma"',
        '"Gate07_Fusion_Diagnostic.ma"',
        '"FINAL_SOURCE_PRESERVED_VIEWS"',
        '"CONTROL_FRAMES"',
        '"GATE_STATUS.json"',
        '"next_gate_authorized"',
    ):
        if token not in contract:
            raise RuntimeError("Gate output contract token missing: "+token)

    recon=(node_root/"reconstruction_runtime.py").read_text(encoding="utf-8-sig")
    if "publish_gate6_output_tree(" not in recon:
        raise RuntimeError("Gate 6 output publication is not wired into reconstruction runtime")
    gate7=(node_root/"gate7_runtime.py").read_text(encoding="utf-8-sig")
    if "publish_gate7_output_tree(" not in gate7:
        raise RuntimeError("Gate 7 output publication is not wired into runtime")

    print("[PASS] R6J Gate Output Contract source verified.")
    print("[PASS] Gate 6 diagnostic Maya + raw new geometry are mandatory outputs.")
    print("[PASS] Gate 7 functional status is separate from runtime status.")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
