from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


R1_NAME = "ConceptGhost_v1.54_P10_GATE7_PREVIEW_r1"
R2_NAME = "ConceptGhost_v1.54_P10_GATE7_PREVIEW_r2_AUDIT"
BASE_SHA256 = "cab56065d612e7e038bcb526307047d57134262471098e56d0225b74defee3dd"
EXCLUDED = {"BUNDLE_MANIFEST.json", "P10_DR9_BUNDLE_MANIFEST.json", "SHA256SUMS.txt"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rt(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def wt(path: Path, text: str, newline: str = "\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline=newline) as stream:
        stream.write(text)


def _next_link(workflow: dict, origin_id: int, origin_slot: int, target_id: int, target_slot: int, typ: str) -> int:
    link_id = int(workflow.get("last_link_id") or 0) + 1
    workflow["last_link_id"] = link_id
    workflow.setdefault("links", []).append([link_id, origin_id, origin_slot, target_id, target_slot, typ])
    by_id = {int(node["id"]): node for node in workflow["nodes"]}
    output = by_id[origin_id]["outputs"][origin_slot]
    if output.get("links") is None:
        output["links"] = []
    output["links"].append(link_id)
    by_id[target_id]["inputs"][target_slot]["link"] = link_id
    return link_id


def patch_workflow(root: Path) -> None:
    path = root / "Payload/workflows/02_ConceptGhost_P10_PRODUCTION.json"
    workflow = json.loads(rt(path))
    by = {int(n["id"]): n for n in workflow["nodes"]}
    for required in (2400, 2410, 2412):
        if required not in by:
            raise RuntimeError(f"r1 workflow missing Gate 7 node {required}")
    if 2420 in by:
        raise RuntimeError("RUN_AUDIT_BUNDLE node already exists")

    order = max(int(n.get("order") or 0) for n in workflow["nodes"]) + 1
    audit = {
        "id": 2420,
        "type": "ConceptGhostP10RunAuditBundle",
        "pos": [16350, 10820],
        "size": [760, 330],
        "flags": {},
        "order": order,
        "mode": 0,
        "inputs": [
            {"name": "gate7_runtime_manifest_path", "type": "STRING", "link": None},
            {"name": "visual_pack_manifest_path", "type": "STRING", "link": None},
            {"name": "output_root", "type": "STRING", "widget": {"name": "output_root"}, "link": None},
        ],
        "outputs": [
            {"name": "run_audit_bundle_zip", "type": "STRING", "links": None, "slot_index": 0},
            {"name": "run_audit_bundle_manifest_path", "type": "STRING", "links": None, "slot_index": 1},
            {"name": "diagnostics_json", "type": "STRING", "links": None, "slot_index": 2},
        ],
        "properties": {"Node name for S&R": "ConceptGhostP10RunAuditBundle"},
        "widgets_values": [""],
        "title": "RUN AUDIT BUNDLE · AUTO · MANIFESTS + LOGS + PREVIEWS · TERMINAL",
    }
    workflow["nodes"].append(audit)
    workflow["last_node_id"] = 2420
    _next_link(workflow, 2400, 2, 2420, 0, "STRING")
    _next_link(workflow, 2410, 1, 2420, 1, "STRING")

    for group in workflow.setdefault("groups", []):
        if group.get("title") == "VISUAL EVIDENCE · TERMINAL BRANCHES · DOES NOT FEED GEOMETRY":
            group["bounding"] = [16280, 10090, 2320, 1150]
    workflow["groups"].append({
        "title": "RUN AUDIT BUNDLE · AUTO-GROWING DIAGNOSTIC ZIP · TERMINAL",
        "bounding": [16280, 10740, 1540, 500],
        "color": "#566b7a",
        "font_size": 24,
        "flags": {},
    })
    extra = workflow.setdefault("extra", {}).setdefault("conceptghost", {})
    extra["gate7_preview_release"] = "GATE7_PREVIEW_R2_AUDIT"
    extra["run_audit_bundle"] = True
    extra["run_audit_bundle_required_core"] = "reconstruction_runtime_manifest.json"
    extra["run_audit_growth_policy"] = "AUTO_INCLUDE_FUTURE_SAFE_EVIDENCE_FROM_P10_ATTEMPT_ROOT"

    start = by.get(2097)
    if start and start.get("widgets_values"):
        start["widgets_values"][0] = str(start["widgets_values"][0]).replace(
            "Observe especialmente o confidence BLUE=HIGH / RED=LOW e o caminho do GIF BEFORE/AFTER da mesma camera do drone.",
            "Observe especialmente o confidence BLUE=HIGH / RED=LOW e o caminho do GIF BEFORE/AFTER da mesma camera do drone.\n\n"
            "Ao final, o node RUN AUDIT BUNDLE gera automaticamente RUN_AUDIT_BUNDLE.zip com "
            "reconstruction_runtime_manifest.json + manifests/logs/previews desta tentativa. "
            "Esse ZIP cresce automaticamente quando novos gates persistem evidencias seguras."
        )
    wt(path, json.dumps(workflow, indent=2, ensure_ascii=False) + "\n")


def update_code_manifest(root: Path, source_commit: str) -> None:
    node_root = root / "Payload/custom_nodes/ConceptGhost_P10_Lab"
    manifest_path = root / "P10_DR9_CODE_MANIFEST.json"
    data = json.loads(rt(manifest_path))
    rows = []
    for path in sorted(node_root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix.lower() != ".pyc":
            rows.append({
                "path": path.relative_to(node_root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            })
    data["schema"] = "ConceptGhost.P10Gate7PreviewAuditCodeManifest.v0.2"
    data["release"] = R2_NAME
    data["source_commit"] = source_commit
    data["files"] = rows
    wt(manifest_path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def patch_runtime_verifier(root: Path, source_commit: str) -> None:
    path = root / "Installer/verify_p10_dr9.py"
    text = rt(path)
    text = re.sub(r"^SOURCE_COMMIT='[0-9a-f]{40}'", f"SOURCE_COMMIT='{source_commit}'", text, count=1, flags=re.M)
    text = text.replace(
        "'ConceptGhostP10DroneMeshComparisonReplay')",
        "'ConceptGhostP10DroneMeshComparisonReplay','ConceptGhostP10RunAuditBundle')",
        1,
    )
    old = "expected={2098:'ConceptGhostP10ProductionEntryLoader',2100:'ConceptGhostP10RefinedEvidencePreview',2207:'ConceptGhostP10WanSequentialSampler',2300:'ConceptGhostP10ReconstructionRuntime',2301:'PreviewImage',2400:'ConceptGhostP10Gate7Runtime',2401:'PreviewImage',2410:'ConceptGhostP10Gate7VisualEvidencePack',2411:'PreviewImage',2412:'ConceptGhostP10WorkflowInstructions'}"
    new = "expected={2098:'ConceptGhostP10ProductionEntryLoader',2100:'ConceptGhostP10RefinedEvidencePreview',2207:'ConceptGhostP10WanSequentialSampler',2300:'ConceptGhostP10ReconstructionRuntime',2301:'PreviewImage',2400:'ConceptGhostP10Gate7Runtime',2401:'PreviewImage',2410:'ConceptGhostP10Gate7VisualEvidencePack',2411:'PreviewImage',2412:'ConceptGhostP10WorkflowInstructions',2420:'ConceptGhostP10RunAuditBundle'}"
    if old not in text:
        raise RuntimeError("r1 verifier expected-node block changed")
    text = text.replace(old, new, 1)
    old_link = "(2410,0,2411,0,'IMAGE')):"
    new_link = "(2410,0,2411,0,'IMAGE'),(2400,2,2420,0,'STRING'),(2410,1,2420,1,'STRING')):"
    if old_link not in text:
        raise RuntimeError("r1 verifier link block changed")
    text = text.replace(old_link, new_link, 1)
    text = text.replace(
        "'schema':'ConceptGhost.P10Gate7PreviewRuntimeVerify.v0.1'",
        "'schema':'ConceptGhost.P10Gate7PreviewAuditRuntimeVerify.v0.2'",
    )
    text = text.replace(
        "CONCEPTGHOST_P10_GATE7_PREVIEW_R1_RUNTIME_VERIFY_PASS",
        "CONCEPTGHOST_P10_GATE7_PREVIEW_R2_AUDIT_RUNTIME_VERIFY_PASS",
    )
    marker = "if by.get(2410,{}).get('widgets_values')!=[False,False,'']: fail(errors,'Gate 7 visual pack approvals must default FALSE')"
    if marker in text:
        text = text.replace(
            marker,
            marker + "\n            if by.get(2420,{}).get('widgets_values')!=['']: fail(errors,'RUN_AUDIT_BUNDLE output_root default mismatch')",
            1,
        )
    wt(path, text)


def patch_entrypoints(root: Path) -> None:
    old_install = root / "Installer/install_gate7_preview_r1.ps1"
    old_verify = root / "Installer/verify_gate7_preview_r1.ps1"
    install = rt(old_install).replace("Gate 7 Preview r1", "Gate 7 Preview r2 + Audit")
    install = install.replace(R1_NAME, R2_NAME)
    install = install.replace("before_gate7_preview_r1", "before_gate7_preview_r2_audit")
    verify = rt(old_verify).replace("Gate 7 Preview r1", "Gate 7 Preview r2 + Audit")
    verify = verify.replace("P10_GATE7_PREVIEW_R1_READY_VERIFY.json", "P10_GATE7_PREVIEW_R2_AUDIT_READY_VERIFY.json")
    wt(root / "Installer/install_gate7_preview_r2_audit.ps1", install)
    wt(root / "Installer/verify_gate7_preview_r2_audit.ps1", verify)
    old_install.unlink()
    old_verify.unlink()

    bat = r"""@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo 03 - ConceptGhost P10 Gate 7 Preview r2 + RUN AUDIT BUNDLE
echo ============================================================
echo Full r15 base + Gate 7 protected-fusion preview + visual evidence.
echo Adds automatic RUN_AUDIT_BUNDLE.zip as the terminal diagnostic output.
echo Gate 8 remains blocked.
echo ============================================================
if not exist "%~dp0Installer\install_gate7_preview_r2_audit.ps1" (
  echo.
  echo [FAIL] Required Gate 7 Preview r2 Audit entrypoint is missing.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Installer\install_gate7_preview_r2_audit.ps1"
if errorlevel 1 (
  echo.
  echo [FAIL] Gate 7 Preview r2 Audit installation did not complete.
  pause
  exit /b 1
)
echo.
echo [PASS] Gate 7 Preview r2 Audit installed. Run 04_VERIFY_INSTALL.bat next.
pause
"""
    (root / "03_INSTALL_ALL.bat").write_bytes(bat.replace("\n", "\r\n").encode("utf-8"))

    verify_bat = r"""@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo 04 - VERIFY ConceptGhost P10 Gate 7 Preview r2 + Audit
echo ============================================================
if not exist "%~dp0Installer\verify_gate7_preview_r2_audit.ps1" (
  echo.
  echo [FAIL] Required Gate 7 Preview r2 Audit verifier is missing.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Installer\verify_gate7_preview_r2_audit.ps1"
if errorlevel 1 (
  echo.
  echo [FAIL] Gate 7 Preview r2 Audit verification failed.
  pause
  exit /b 1
)
echo.
echo [PASS] Gate 7 Preview r2 Audit installation verification completed.
pause
"""
    (root / "04_VERIFY_INSTALL.bat").write_bytes(verify_bat.replace("\n", "\r\n").encode("utf-8"))


def patch_docs_release(root: Path, source_commit: str, package_commit: str) -> None:
    old = root / "USER_GUIDE_GATE7_PREVIEW_R1.md"
    guide = rt(old).replace("Gate 7 Preview r1", "Gate 7 Preview r2 + Audit")
    guide += """
## RUN_AUDIT_BUNDLE.zip

Workflow 02 now ends with a terminal diagnostic node that automatically writes:

- RUN_AUDIT_BUNDLE.zip
- RUN_AUDIT_BUNDLE_manifest.json

The ZIP always requires and includes reconstruction_runtime_manifest.json.

It also collects safe JSON/TXT/LOG/MD/CSV and preview PNG/JPG/GIF/SVG evidence under the immutable P10 attempt, plus selected accepted P9 authority diagnostics. Heavy PLY/NPZ/FBX/MA/USDA payloads are excluded.

Growth invariant: this node remains the final diagnostic node. As Gate 8/9/10 are later inserted before it, their safe persisted evidence is discovered automatically and the audit ZIP becomes richer without changing the user's audit workflow.
"""
    wt(root / "USER_GUIDE_GATE7_PREVIEW_R2_AUDIT.md", guide)
    old.unlink()

    docs = root / "Payload/docs"
    wt(docs / "35_RUN_AUDIT_BUNDLE_R2.md", f"""# Gate 7 Preview r2 + RUN_AUDIT_BUNDLE

Source commit: {source_commit}
Package commit: {package_commit or 'LOCAL_BUILD'}

Required audit core:
- reconstruction_runtime_manifest.json

Auto-growth:
- all safe manifest/log/text/preview evidence under the immutable P10 attempt is collected;
- selected P9 authority diagnostics are collected;
- heavy geometry/DCC payloads remain excluded;
- the audit node is terminal and must stay after future gates.

Gate 8 remains blocked.
""")

    for name in ("RELEASE.json", "P10_DR9_RELEASE.json"):
        path = root / name
        data = json.loads(rt(path))
        data["schema"] = "ConceptGhost.P10Gate7PreviewAuditRelease.v0.2"
        data["release"] = R2_NAME
        data["source_commit"] = source_commit
        data["package_hotfix_commit"] = package_commit or "LOCAL_BUILD"
        data["run_audit_bundle"] = {
            "enabled": True,
            "terminal": True,
            "required_core": ["reconstruction_runtime_manifest.json"],
            "auto_growth": True,
            "heavy_payloads_excluded": True,
            "status": "READY_FOR_USER_RUNTIME_TEST",
        }
        features = data.setdefault("features", [])
        for feature in (
            "RUN_AUDIT_BUNDLE_ZIP",
            "RECONSTRUCTION_RUNTIME_MANIFEST_REQUIRED",
            "AUTO_GROW_FUTURE_GATE_DIAGNOSTICS",
        ):
            if feature not in features:
                features.append(feature)
        wt(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    validation = f"""ConceptGhost P10 Gate 7 Preview r2 + Audit validation

Base r15 SHA-256: {BASE_SHA256}
Source commit: {source_commit}
Gate 7 runtime/visual evidence inherited: PASS
RUN_AUDIT_BUNDLE node present: PASS
reconstruction_runtime_manifest.json hard-required by audit collector: PASS
Future safe gate evidence auto-discovery: PASS
Heavy geometry/DCC payload exclusion: PASS
Gate 8 node present: NO
P9 authority changed: NO
User runtime acceptance: PENDING
"""
    wt(root / "P10_GATE7_PREVIEW_R2_AUDIT_VALIDATION.txt", validation)


def patch_bundle_tests(root: Path, source_commit: str) -> None:
    path = root / "Installer/test_dr9_bundle.py"
    text = rt(path)
    old_source = re.search(r"EXPECTED_SOURCE='([0-9a-f]{40})'", text)
    if old_source:
        text = text.replace(old_source.group(1), source_commit)
    text = text.replace("USER_GUIDE_GATE7_PREVIEW_R1.md", "USER_GUIDE_GATE7_PREVIEW_R2_AUDIT.md")
    wt(path, text)

    test = """from pathlib import Path
import sys,json

def main(root):
 root=Path(root).resolve(); errors=[]
 wf=json.loads((root/'Payload/workflows/02_ConceptGhost_P10_PRODUCTION.json').read_text(encoding='utf-8-sig'))
 by={int(n['id']):n for n in wf.get('nodes',[])}
 if by.get(2420,{}).get('type')!='ConceptGhostP10RunAuditBundle': errors.append('missing RUN_AUDIT_BUNDLE node 2420')
 if by.get(2420,{}).get('widgets_values')!=['']: errors.append('audit output_root default mismatch')
 links={(x[1],x[2],x[3],x[4],x[5]) for x in wf.get('links',[])}
 for req in ((2400,2,2420,0,'STRING'),(2410,1,2420,1,'STRING')):
  if req not in links: errors.append('missing audit link '+repr(req))
 node_root=root/'Payload/custom_nodes/ConceptGhost_P10_Lab'
 for rel in ('run_audit_bundle.py','preview_nodes.py'):
  if not (node_root/rel).is_file(): errors.append('missing '+rel)
 source=(node_root/'run_audit_bundle.py').read_text(encoding='utf-8')
 for token in ('reconstruction_runtime_manifest_included','RUN_AUDIT_BUNDLE.zip','AUTO_INCLUDE_SAFE_JSON_LOG_TEXT_AND_PREVIEW_EVIDENCE'):
  if token not in source: errors.append('audit source missing '+token)
 if any('Gate8' in str(n.get('type')) or 'Gate 8' in str(n.get('type')) for n in wf.get('nodes',[])):
  errors.append('Gate 8 leaked into package')
 if errors:
  print('\\n'.join('[FAIL] '+e for e in errors)); return 1
 print('CONCEPTGHOST_GATE7_PREVIEW_R2_AUDIT_BUNDLE_PASS'); return 0

if __name__=='__main__':
 raise SystemExit(main(sys.argv[1]))
"""
    wt(root / "Installer/test_run_audit_bundle_package.py", test)


def rebuild_manifests(root: Path, source_commit: str) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_file() and rel not in EXCLUDED:
            rows.append({"path": rel, "sha256": sha256(path), "size_bytes": path.stat().st_size})
    for name in ("BUNDLE_MANIFEST.json", "P10_DR9_BUNDLE_MANIFEST.json"):
        path = root / name
        data = json.loads(rt(path))
        data["schema"] = "ConceptGhost.P10Gate7PreviewAuditBundle.v0.2"
        data["release"] = R2_NAME
        data["source_commit"] = source_commit
        data["file_count_excluding_manifests_and_checksums"] = len(rows)
        data["run_audit_bundle"] = {
            "enabled": True,
            "node_id": 2420,
            "required_core": "reconstruction_runtime_manifest.json",
            "auto_growth": True,
        }
        data["files"] = rows
        wt(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    lines = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            lines.append(f"{sha256(path)}  {path.relative_to(root).as_posix()}")
    wt(root / "SHA256SUMS.txt", "\n".join(lines) + "\n")


def validate(root: Path, source_commit: str) -> list[str]:
    errors = []
    manifest = json.loads(rt(root / "P10_DR9_CODE_MANIFEST.json"))
    if manifest.get("source_commit") != source_commit:
        errors.append("code manifest source commit mismatch")
    node_root = root / "Payload/custom_nodes/ConceptGhost_P10_Lab"
    for item in manifest.get("files", []):
        path = node_root / item["path"]
        if not path.is_file() or sha256(path) != item["sha256"]:
            errors.append("P10 code mismatch " + item["path"])
    for path in list(node_root.glob("*.py")) + list((root / "Installer").glob("*.py")):
        try:
            compile(rt(path), str(path), "exec")
        except Exception as error:
            errors.append(f"compile {path.name}: {error}")
    for raw in rt(root / "SHA256SUMS.txt").splitlines():
        digest, rel = raw.split("  ", 1)
        path = root / rel
        if not path.is_file() or sha256(path) != digest:
            errors.append("sha mismatch " + rel)
    return errors


def zipdet(root: Path, output: Path) -> None:
    if output.exists():
        output.unlink()
    fixed = (2026, 9, 24, 6, 45, 0)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            info = zipfile.ZipInfo(path.relative_to(root).as_posix(), date_time=fixed)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--p10-source-root", type=Path, required=True)
    parser.add_argument("--source-commit", default=os.environ.get("GITHUB_SHA", ""))
    parser.add_argument("--package-commit", default=os.environ.get("GITHUB_SHA", ""))
    parser.add_argument("--keep-extracted", type=Path)
    args = parser.parse_args()
    if sha256(args.source) != BASE_SHA256:
        raise SystemExit("wrong frozen r15 base SHA")
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_commit or ""):
        raise SystemExit("source commit must be a 40-char SHA")

    r1_builder = Path(__file__).resolve().parents[1] / "gate7_preview_r1" / "build_gate7_preview_r1_from_r15.py"
    if not r1_builder.is_file():
        raise SystemExit(f"missing r1 builder: {r1_builder}")

    with tempfile.TemporaryDirectory(prefix="cg-g7-preview-r2-audit-") as temp_dir:
        temp = Path(temp_dir)
        r1_zip = temp / (R1_NAME + ".zip")
        root = temp / R2_NAME
        cmd = [
            sys.executable, str(r1_builder),
            "--source", str(args.source),
            "--output", str(r1_zip),
            "--p10-source-root", str(args.p10_source_root),
            "--hotfix-commit", args.package_commit,
            "--keep-extracted", str(root),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.returncode:
            raise SystemExit(result.stdout + result.stderr)

        patch_workflow(root)
        update_code_manifest(root, args.source_commit)
        patch_runtime_verifier(root, args.source_commit)
        patch_entrypoints(root)
        patch_docs_release(root, args.source_commit, args.package_commit)
        patch_bundle_tests(root, args.source_commit)

        for script in ("test_dr9_bundle.py", "test_gate7_preview_bundle.py", "test_run_audit_bundle_package.py"):
            proc = subprocess.run(
                [sys.executable, str(root / "Installer" / script), str(root)],
                capture_output=True,
                text=True,
            )
            print(proc.stdout.strip())
            if proc.returncode:
                raise SystemExit(proc.stdout + proc.stderr)

        for cache in sorted(root.rglob("__pycache__"), key=lambda p: len(p.parts), reverse=True):
            shutil.rmtree(cache, ignore_errors=True)
        for pyc in root.rglob("*.pyc"):
            pyc.unlink(missing_ok=True)

        rebuild_manifests(root, args.source_commit)
        errors = validate(root, args.source_commit)
        if errors:
            raise SystemExit("\n".join("[FAIL] " + e for e in errors))

        args.output.parent.mkdir(parents=True, exist_ok=True)
        zipdet(root, args.output)
        print("G7_PREVIEW_R2_AUDIT_ZIP=" + str(args.output))
        print("G7_PREVIEW_R2_AUDIT_BYTES=" + str(args.output.stat().st_size))
        print("G7_PREVIEW_R2_AUDIT_SHA256=" + sha256(args.output))

        if args.keep_extracted:
            if args.keep_extracted.exists():
                shutil.rmtree(args.keep_extracted)
            shutil.copytree(root, args.keep_extracted)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
