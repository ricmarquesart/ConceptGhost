from __future__ import annotations

import argparse
import json
import os
import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path


def default_comfy_root() -> Path:
    return (
        Path(os.environ.get("LOCALAPPDATA") or "")
        / "Comfy-Desktop"
        / "ComfyUI-Installs"
        / "ComfyUI"
        / "ComfyUI"
    )


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError("R6F15 expected source contract not found: " + label)
    return text.replace(old, new, 1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--comfy-root", type=Path, default=default_comfy_root())
    args = parser.parse_args()

    root = args.comfy_root.resolve()
    node_root = root / "custom_nodes" / "ConceptGhost_P10_Lab"
    gate7_path = node_root / "gate7_runtime.py"
    preview_path = node_root / "preview_nodes.py"
    for path in (gate7_path, preview_path):
        if not path.is_file():
            raise RuntimeError("Required installed ConceptGhost file is missing: " + str(path))

    backup_root = (
        Path(os.environ.get("LOCALAPPDATA") or "")
        / "ConceptGhost"
        / "HotfixBackups"
        / "R6F15_COLMAP_AUTODISCOVERY"
    )
    backup_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(gate7_path, backup_root / gate7_path.name)
    shutil.copy2(preview_path, backup_root / preview_path.name)

    gate7 = gate7_path.read_text(encoding="utf-8-sig")
    import_line = "from .reconstruction_runtime import resolve_colmap_executable"
    if import_line not in gate7:
        gate7 = replace_once(
            gate7,
            "from .protected_fusion import build_protected_fusion_candidate\n",
            "from .protected_fusion import build_protected_fusion_candidate\n"
            + import_line
            + "\n",
            "Gate 7 COLMAP resolver import",
        )

    old_helper = '''def _resolve_gate7_repair_colmap(
    dataset_root: Path,
    requested: str,
) -> str:
    """Prefer the exact COLMAP executable that built the current dense workspace."""

    dense_manifest_path=dataset_root/"dense_reconstruction_manifest.json"
    if dense_manifest_path.is_file():
        try:
            dense_manifest=_read_json(dense_manifest_path,"Gate 6 dense reconstruction manifest")
        except ContractError:
            dense_manifest={}
        stored=str(dense_manifest.get("colmap_executable") or "").strip()
        if stored and Path(stored).is_file():
            return stored
    requested=str(requested or "").strip()
    return requested or "colmap"
'''
    new_helper = '''def _resolve_gate7_repair_colmap(
    dataset_root: Path,
    requested: str,
) -> str:
    """Resolve the exact installed COLMAP runtime for every Gate 7 native call."""

    dense_manifest_path = dataset_root / "dense_reconstruction_manifest.json"
    if dense_manifest_path.is_file():
        try:
            dense_manifest = _read_json(
                dense_manifest_path,
                "Gate 6 dense reconstruction manifest",
            )
        except ContractError:
            dense_manifest = {}
        stored = str(dense_manifest.get("colmap_executable") or "").strip()
        if stored and Path(stored).is_file():
            return str(Path(stored).resolve())

    requested = str(requested or "").strip()
    if requested and requested.lower() not in {"colmap", "colmap.exe"}:
        return resolve_colmap_executable(requested)

    return resolve_colmap_executable(None)
'''
    if "return resolve_colmap_executable(None)" not in gate7:
        gate7 = replace_once(gate7, old_helper, new_helper, "Gate 7 COLMAP helper")

    old_delaunay = '''                delaunay_status = run_delaunay_visibility_meshing(
                    dataset_root,
                    colmap_executable=colmap_executable,
                    overwrite_output=False,
                )
'''
    new_delaunay = '''                delaunay_executable = _resolve_gate7_repair_colmap(
                    dataset_root,
                    colmap_executable,
                )
                delaunay_status = run_delaunay_visibility_meshing(
                    dataset_root,
                    colmap_executable=delaunay_executable,
                    overwrite_output=False,
                )
'''
    if "colmap_executable=delaunay_executable" not in gate7:
        gate7 = replace_once(
            gate7,
            old_delaunay,
            new_delaunay,
            "Gate 7 Delaunay invocation",
        )
    gate7_path.write_text(gate7, encoding="utf-8")

    preview = preview_path.read_text(encoding="utf-8-sig")
    old_preview = '            colmap_executable=str(colmap_executable or "colmap"),'
    new_preview = '            colmap_executable=str(colmap_executable or ""),'
    if old_preview in preview:
        preview = preview.replace(old_preview, new_preview, 1)
    elif new_preview not in preview:
        raise RuntimeError("R6F15 could not locate Gate 7 preview COLMAP input contract")
    preview_path.write_text(preview, encoding="utf-8")

    py_compile.compile(str(gate7_path), doraise=True)
    py_compile.compile(str(preview_path), doraise=True)

    marker_root = Path(os.environ.get("LOCALAPPDATA") or "") / "ConceptGhost"
    marker_root.mkdir(parents=True, exist_ok=True)
    marker = marker_root / "R6F15_COLMAP_AUTODISCOVERY_HOTFIX.json"
    marker.write_text(
        json.dumps(
            {
                "schema": "ConceptGhost.R6F15ColmapAutodiscoveryHotfix.v0.1",
                "status": "APPLIED",
                "comfy_root": str(root),
                "gate7_path": str(gate7_path),
                "preview_path": str(preview_path),
                "backup_root": str(backup_root),
                "applied_at_utc": datetime.now(timezone.utc).isoformat(),
                "shared_comfy_python_mutated": False,
                "moge_runtime_mutated": False,
                "p9_authority_mutated": False,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print("[PASS] R6F15 COLMAP auto-discovery hotfix applied.")
    print("[PASS] No pip packages, MoGe runtime, P9 data, WAN data, or Gate 6 data changed.")
    print("[INFO] Run 02_VERIFY_HOTFIX.bat, then 03_RESUME_LAST_GATE7.bat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
