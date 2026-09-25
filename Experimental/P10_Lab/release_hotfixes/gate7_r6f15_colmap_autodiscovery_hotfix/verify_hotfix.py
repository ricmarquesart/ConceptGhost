from __future__ import annotations

import argparse
import os
from pathlib import Path


def default_comfy_root() -> Path:
    return (
        Path(os.environ.get("LOCALAPPDATA") or "")
        / "Comfy-Desktop"
        / "ComfyUI-Installs"
        / "ComfyUI"
        / "ComfyUI"
    )


def colmap_candidates() -> tuple[Path, ...]:
    base = Path(os.environ.get("LOCALAPPDATA") or "") / "ConceptGhost" / "ThirdParty" / "COLMAP-4.2.0"
    return (
        base / "COLMAP.bat",
        base / "colmap.bat",
        base / "bin" / "colmap.exe",
        base / "COLMAP-4.2.0" / "COLMAP.bat",
        base / "COLMAP-4.2.0" / "bin" / "colmap.exe",
    )


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
            raise RuntimeError("Missing installed file: " + str(path))

    gate7 = gate7_path.read_text(encoding="utf-8-sig")
    preview = preview_path.read_text(encoding="utf-8-sig")
    required = (
        "from .reconstruction_runtime import resolve_colmap_executable",
        "delaunay_executable = _resolve_gate7_repair_colmap(",
        "colmap_executable=delaunay_executable",
        "return resolve_colmap_executable(None)",
    )
    for token in required:
        if token not in gate7:
            raise RuntimeError("Installed Gate 7 source missing token: " + token)

    if 'colmap_executable=str(colmap_executable or "")' not in preview:
        raise RuntimeError("Installed preview node still forces the bare COLMAP token")

    found = next((path for path in colmap_candidates() if path.is_file()), None)
    if found is None:
        raise RuntimeError(
            "ConceptGhost private COLMAP runtime was not found. "
            "Do not reinstall yet; preserve this verifier output."
        )

    print("[PASS] R6F15 Gate 7 COLMAP auto-discovery source is installed.")
    print("[PASS] Private COLMAP runtime found: " + str(found.resolve()))
    print("[PASS] No package/runtime reinstall is required for this blocker.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
