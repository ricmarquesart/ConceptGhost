from __future__ import annotations

import argparse
import json
import os
import py_compile
import sys
import tempfile
from pathlib import Path


PLY = """ply
format ascii 1.0
element vertex 4
property float x
property float y
property float z
element face 2
property list uchar int vertex_indices
end_header
0 0 0
1 0 0
1 1 0
0 1 0
3 0 1 2
3 0 2 3
"""


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
    args = parser.parse_args()

    comfy_root = args.comfy_root.resolve()
    custom_nodes = comfy_root / "custom_nodes"
    node_root = custom_nodes / "ConceptGhost_P10_Lab"
    required = (
        "gate6_geometry_output.py",
        "reconstruction_runtime.py",
        "reconstruction_node.py",
        "preview_nodes.py",
    )
    for name in required:
        path = node_root / name
        if not path.is_file():
            raise RuntimeError("Missing installed R6I file: " + str(path))
        py_compile.compile(str(path), doraise=True)

    runtime = (node_root / "reconstruction_runtime.py").read_text(encoding="utf-8-sig")
    for token in (
        "publish_gate6_geometry_output",
        '"gate6_raw_p10_geometry_path"',
        '"gate6_geometry_generated"',
        '"geometry_output"',
    ):
        if token not in runtime:
            raise RuntimeError("Installed Gate 6 runtime missing R6I token: " + token)

    preview_nodes = (node_root / "preview_nodes.py").read_text(encoding="utf-8-sig")
    if "GATE 6 · 3D Reconstruction · RAW P10 Geometry Output" not in preview_nodes:
        raise RuntimeError("Gate 6 display label is not installed")

    sys.path.insert(0, str(comfy_root))
    sys.path.insert(0, str(custom_nodes))
    from ConceptGhost_P10_Lab.gate6_geometry_output import publish_gate6_geometry_output

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        dataset = root / "gate6" / "dataset"
        dense = dataset / "dense"
        dense.mkdir(parents=True)
        (dense / "pre_fusion_mesh.ply").write_text(PLY, encoding="ascii")
        (dense / "fused.ply").write_text(PLY, encoding="ascii")
        (dataset / "prefusion_mesh_manifest.json").write_text(
            json.dumps({"status":"PASS"}),
            encoding="utf-8",
        )
        p9 = root / "p9"
        p9.mkdir()
        result = publish_gate6_geometry_output(
            dataset,
            root / "gate6",
            p9_run_dir=p9,
            p10_attempt_id="verify",
            geometry_quality={"status":"WARN","alerts":[]},
        )
        if result.get("geometry_generated") is not True:
            raise RuntimeError("Gate 6 geometry publisher did not assert geometry_generated")
        if int(result.get("vertex_count") or 0) != 4 or int(result.get("face_count") or 0) != 2:
            raise RuntimeError("Gate 6 geometry publisher count mismatch")
        if not Path(str(result.get("raw_p10_geometry_obj"))).is_file():
            raise RuntimeError("Gate 6 OBJ output was not produced")

    workflow_roots = [
        comfy_root / "user" / "default" / "workflows",
        Path(os.environ.get("LOCALAPPDATA") or "") / "ConceptGhost" / "internal" / "workflows",
    ]
    verified_workflows = []
    for root in workflow_roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8-sig"))
            except Exception:
                continue
            nodes = data.get("nodes")
            if not isinstance(nodes, list):
                continue
            by_id = {node.get("id"):node for node in nodes if isinstance(node,dict)}
            if not {2100,2207,2300}.issubset(by_id):
                continue
            titles = [str(group.get("title") or "") for group in data.get("groups",[]) if isinstance(group,dict)]
            if all(any(title.startswith(prefix) for title in titles) for prefix in ("GATE 4","GATE 5","GATE 6")):
                verified_workflows.append(path)
    if not verified_workflows:
        raise RuntimeError("No installed Production workflow exposes Gate 4/5/6 groups")

    print("[PASS] R6I source files compile and import.")
    print("[PASS] Gate 6 publisher generated non-empty PLY/OBJ test geometry.")
    print("[PASS] Installed workflow exposes Gate 4/5/6 groups and outputs.")
    print("[INFO] You can now run 03_RESUME_LAST_GATE6.bat to reuse the existing WAN images.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
