from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


MODULE = Path(__file__).resolve().parents[1] / "release_hotfixes" / "gate7_r6f13_v036_runtime_compat_runlocal_audit" / "refresh_p10_code_manifest.py"


def _load():
    spec = importlib.util.spec_from_file_location("r6f13_manifest", MODULE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_manifest_hashes_exact_shipped_bytes(tmp_path: Path) -> None:
    module = _load()
    root = tmp_path / "bundle"
    nodes = root / "Payload" / "custom_nodes" / "ConceptGhost_P10_Lab"
    nodes.mkdir(parents=True)
    payload = b"line1\r\nline2\r\n"
    (nodes / "sample.py").write_bytes(payload)
    (root / "P10_DR9_CODE_MANIFEST.json").write_text("{}", encoding="utf-8")
    source = "a" * 40
    path = module.refresh(root, source, "R6F13B")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["manifest_authority"] == "EXACT_SHIPPED_PAYLOAD_BYTES"
    assert data["source_commit"] == source
    assert data["files"] == [{
        "path": "sample.py",
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }]
