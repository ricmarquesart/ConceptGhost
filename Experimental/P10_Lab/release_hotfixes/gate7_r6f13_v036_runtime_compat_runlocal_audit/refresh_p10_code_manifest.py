from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def refresh(bundle_root: Path, source_commit: str, release: str | None = None) -> Path:
    bundle_root = bundle_root.resolve()
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("source_commit must be a 40-character lowercase SHA")
    node_root = bundle_root / "Payload" / "custom_nodes" / "ConceptGhost_P10_Lab"
    manifest_path = bundle_root / "P10_DR9_CODE_MANIFEST.json"
    if not node_root.is_dir():
        raise FileNotFoundError(node_root)
    current = json.loads(manifest_path.read_text(encoding="utf-8-sig")) if manifest_path.is_file() else {}
    files = []
    for path in sorted(node_root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix.lower() in {".pyc", ".pyo"}:
            continue
        files.append({
            "path": path.relative_to(node_root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    current.update({
        "schema": "ConceptGhost.P10Gate7R6F13BCodeManifest.v0.1",
        "release": release or current.get("release") or bundle_root.name,
        "source_commit": source_commit,
        "files": files,
        "manifest_authority": "EXACT_SHIPPED_PAYLOAD_BYTES",
    })
    manifest_path.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest_path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle_root", type=Path)
    ap.add_argument("--source-commit", required=True)
    ap.add_argument("--release")
    a = ap.parse_args()
    print(refresh(a.bundle_root, a.source_commit, a.release))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
