from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil


GROUPS = [
    {
        "title":"HANDOFF · EXISTING P9 + COMMITTED DRONE ROUTE",
        "bounding":[8580,9200,2350,830],
        "color":"#455a64",
        "font_size":26,
        "flags":{},
    },
    {
        "title":"GATE 4 · DRONE/CAMERA EVIDENCE · OUTPUT = CONTROL + CAMERA MANIFESTS",
        "bounding":[10040,9430,2060,1110],
        "color":"#3f51b5",
        "font_size":28,
        "flags":{},
    },
    {
        "title":"GATE 5 · NEW VIEW GENERATION · OUTPUT = WAN MULTIVIEW IMAGES",
        "bounding":[12380,9400,2360,1510],
        "color":"#6a1b9a",
        "font_size":28,
        "flags":{},
    },
    {
        "title":"GATE 6 · 3D RECONSTRUCTION · OUTPUT = RAW P10 GEOMETRY (.PLY/.OBJ)",
        "bounding":[14720,9400,1680,1080],
        "color":"#2e7d32",
        "font_size":28,
        "flags":{},
    },
]


def patch_workflow(path: Path, backup_root: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return False
    nodes = data.get("nodes")
    if not isinstance(nodes, list):
        return False
    by_id = {node.get("id"): node for node in nodes if isinstance(node, dict)}
    if not {2100, 2207, 2300}.issubset(by_id):
        return False

    rel = path.name
    backup = backup_root / rel
    suffix = 1
    while backup.exists():
        backup = backup_root / f"{path.stem}_{suffix}{path.suffix}"
        suffix += 1
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup)

    by_id[2100]["title"] = "GATE 4 OUTPUT · DRONE EVIDENCE · CONTROL + CAMERA MANIFESTS"
    by_id[2207]["title"] = "GATE 5 OUTPUT · GENERATED MULTIVIEW IMAGES + WAN MANIFEST"
    if 2208 in by_id:
        by_id[2208]["title"] = "GATE 5 OUTPUT PREVIEW · WAN FILLED + P9 PRESERVED"
    by_id[2300]["title"] = "GATE 6 · RECONSTRUCT 3D FROM DRONE VIEWS · RAW P10 GEOMETRY"
    if 2301 in by_id:
        by_id[2301]["title"] = "GATE 6 OUTPUT · RAW P10 GEOMETRY PREVIEW · BEFORE GATE 7"

    groups = data.get("groups")
    if not isinstance(groups, list):
        groups = []
    prefixes = ("HANDOFF ·", "GATE 4 ·", "GATE 5 ·", "GATE 6 ·")
    groups = [
        group for group in groups
        if not (
            isinstance(group, dict)
            and str(group.get("title") or "").startswith(prefixes)
        )
    ]
    groups.extend(GROUPS)
    data["groups"] = groups

    extra = data.get("extra")
    if not isinstance(extra, dict):
        extra = {}
    conceptghost = extra.get("conceptghost")
    if not isinstance(conceptghost, dict):
        conceptghost = {}
    conceptghost.update({
        "r6i_gate6_geometry_functional_proof": True,
        "gate6_contract": "RAW_P10_GEOMETRY_REQUIRED_BEFORE_GATE7",
    })
    extra["conceptghost"] = conceptghost
    data["extra"] = extra

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--comfy-root", type=Path, required=True)
    parser.add_argument("--install-root", type=Path, required=True)
    args = parser.parse_args()

    backup_root = args.install_root / "HotfixBackups" / "R6I_GATE6_GEOMETRY_PROOF" / "workflows"
    roots = [
        args.comfy_root / "user" / "default" / "workflows",
        args.install_root / "internal" / "workflows",
    ]
    patched = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*.json"):
            if patch_workflow(path, backup_root):
                patched.append(path)

    if not patched:
        raise RuntimeError("No current ConceptGhost P10 Production workflow with Gate 4/5/6 nodes was found")

    print("[PASS] Patched Gate labels/groups in:")
    for path in patched:
        print("  " + str(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
