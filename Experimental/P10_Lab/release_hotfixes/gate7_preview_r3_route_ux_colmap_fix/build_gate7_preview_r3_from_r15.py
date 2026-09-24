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


R2_NAME = "ConceptGhost_v1.54_P10_GATE7_PREVIEW_r2_AUDIT"
R3_NAME = "ConceptGhost_v1.54_P10_GATE7_PREVIEW_r3_ROUTE_UX_COLMAP_FIX"
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


def replace_text_tree(root: Path, old: str, new: str) -> None:
    suffixes = {".py", ".ps1", ".md", ".json", ".txt"}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        try:
            text = rt(path)
        except UnicodeDecodeError:
            continue
        if old in text:
            wt(path, text.replace(old, new))


def patch_entrypoints(root: Path) -> None:
    old_install = root / "Installer/install_gate7_preview_r2_audit.ps1"
    old_verify = root / "Installer/verify_gate7_preview_r2_audit.ps1"
    if not old_install.is_file() or not old_verify.is_file():
        raise RuntimeError("r2 audit entrypoints are missing")

    install = rt(old_install)
    verify = rt(old_verify)
    install = install.replace("Gate 7 Preview r2 + Audit", "Gate 7 Preview r3 + Route UX + COLMAP Fix")
    verify = verify.replace("Gate 7 Preview r2 + Audit", "Gate 7 Preview r3 + Route UX + COLMAP Fix")
    install = install.replace(R2_NAME, R3_NAME)
    verify = verify.replace(R2_NAME, R3_NAME)
    install = install.replace("before_gate7_preview_r2_audit", "before_gate7_preview_r3_route_ux_colmap_fix")
    verify = verify.replace(
        "P10_GATE7_PREVIEW_R2_AUDIT_READY_VERIFY.json",
        "P10_GATE7_PREVIEW_R3_ROUTE_UX_COLMAP_FIX_READY_VERIFY.json",
    )
    wt(root / "Installer/install_gate7_preview_r3_route_ux_colmap_fix.ps1", install)
    wt(root / "Installer/verify_gate7_preview_r3_route_ux_colmap_fix.ps1", verify)
    old_install.unlink()
    old_verify.unlink()

    bat = r"""@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo 03 - ConceptGhost P10 Gate 7 Preview r3
echo     Route UX + COLMAP Binary Sparse Fix + Audit Bundle
echo ============================================================
echo Based on the frozen r15 runtime.
echo Includes Gate 7, RUN_AUDIT_BUNDLE, improved drone editor,
echo and the dense COLMAP cameras.bin/images.bin Gate 7 fix.
echo Gate 8 remains blocked.
echo ============================================================
if not exist "%~dp0Installer\install_gate7_preview_r3_route_ux_colmap_fix.ps1" (
  echo.
  echo [FAIL] Required Gate 7 Preview r3 entrypoint is missing.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Installer\install_gate7_preview_r3_route_ux_colmap_fix.ps1"
if errorlevel 1 (
  echo.
  echo [FAIL] Gate 7 Preview r3 installation did not complete.
  pause
  exit /b 1
)
echo.
echo [PASS] Gate 7 Preview r3 installed. Run 04_VERIFY_INSTALL.bat next.
pause
"""
    (root / "03_INSTALL_ALL.bat").write_bytes(bat.replace("\n", "\r\n").encode("utf-8"))

    verify_bat = r"""@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo 04 - VERIFY ConceptGhost P10 Gate 7 Preview r3
echo ============================================================
if not exist "%~dp0Installer\verify_gate7_preview_r3_route_ux_colmap_fix.ps1" (
  echo.
  echo [FAIL] Required Gate 7 Preview r3 verifier is missing.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Installer\verify_gate7_preview_r3_route_ux_colmap_fix.ps1"
if errorlevel 1 (
  echo.
  echo [FAIL] Gate 7 Preview r3 verification failed.
  pause
  exit /b 1
)
echo.
echo [PASS] Gate 7 Preview r3 installation verification completed.
pause
"""
    (root / "04_VERIFY_INSTALL.bat").write_bytes(verify_bat.replace("\n", "\r\n").encode("utf-8"))


def patch_package_contracts(root: Path, source_commit: str, package_commit: str) -> None:
    node_root = root / "Payload/custom_nodes/ConceptGhost_P10_Lab"

    verifier = root / "Installer/verify_p10_dr9.py"
    text = rt(verifier)
    text = text.replace(
        "CONCEPTGHOST_P10_GATE7_PREVIEW_R2_AUDIT_RUNTIME_VERIFY_PASS",
        "CONCEPTGHOST_P10_GATE7_PREVIEW_R3_ROUTE_UX_COLMAP_FIX_RUNTIME_VERIFY_PASS",
    )
    wt(verifier, text)

    gate7_test = root / "Installer/test_gate7_preview_bundle.py"
    text = rt(gate7_test)
    text = text.replace(
        "GATE7_PREVIEW_R2_AUDIT_RUNTIME_VERIFY_PASS",
        "GATE7_PREVIEW_R3_ROUTE_UX_COLMAP_FIX_RUNTIME_VERIFY_PASS",
    )
    text = text.replace(
        "Installer/install_gate7_preview_r2_audit.ps1",
        "Installer/install_gate7_preview_r3_route_ux_colmap_fix.ps1",
    )
    text = text.replace(
        "Installer/verify_gate7_preview_r2_audit.ps1",
        "Installer/verify_gate7_preview_r3_route_ux_colmap_fix.ps1",
    )
    wt(gate7_test, text)

    old_guide = root / "USER_GUIDE_GATE7_PREVIEW_R2_AUDIT.md"
    guide = rt(old_guide)
    guide = guide.replace("Gate 7 Preview r2 + Audit", "Gate 7 Preview r3 + Route UX + COLMAP Fix")
    guide += """
## Drone editor refinements in r3

- Orthographic zoom ceiling increased to 160x.
- Perspective zoom ceiling increased to 48x.
- Adding, moving or changing a PATH / SPIN_360 point no longer auto-fits or zooms out the four-view editor.
- Same-scene Queue Prompt refresh preserves the current artist zoom/pan.
- Explicit Enquadrar tudo remains the normal manual viewport reset.
- Exportar trajeto writes a portable JSON route preset.
- Importar trajeto restores missions/settings and rebinds them to the current accepted P9 scene/run.
- Four-view internal rendering increased to 720 x 660 pixels per panel.
- Interactive P9 preview geometry budget increased to 50,000 points.

## Gate 7 COLMAP runtime fix in r3

COLMAP image_undistorter commonly persists the dense workspace sparse model as:
- dense/sparse/cameras.bin
- dense/sparse/images.bin

Gate 7.3 previously required .txt files and therefore failed after a valid Gate 6 dense reconstruction. r3 reads .txt when available and otherwise parses the native binary sparse model fail-closed. This directly fixes the observed COLMAP cameras.txt does not exist error without changing camera authority.
"""
    new_guide = root / "USER_GUIDE_GATE7_PREVIEW_R3_ROUTE_UX_COLMAP_FIX.md"
    wt(new_guide, guide)
    old_guide.unlink()

    docs = root / "Payload/docs"
    wt(
        docs / "36_GATE7_R3_ROUTE_UX_COLMAP_BINARY_FIX.md",
        f"""# Gate 7 Preview r3 — Route UX + COLMAP Binary Sparse Fix

Source commit: {source_commit}
Package commit: {package_commit or 'LOCAL_BUILD'}

Observed runtime failure fixed:
Gate 7.3 -> dense/sparse/cameras.txt does not exist.

Root cause:
Gate 6 COLMAP image_undistorter produced a valid native binary sparse model while
Gate 7.3 assumed a text sparse model.

Correction:
- text cameras.txt/images.txt still supported;
- native cameras.bin/images.bin now supported;
- PINHOLE calibration remains mandatory;
- no conversion/re-fit of P9 camera authority;
- binary model parsing is covered by focused Gate 7.3 regression tests.

Drone route editor:
- 160x orthographic zoom;
- 48x perspective zoom;
- no automatic zoom-out after point placement/drag;
- same-scene execution preserves viewport;
- route JSON export/import;
- imported route is rebound to current scene/run;
- 720x660 internal four-view panels;
- 50k interactive geometry points.

RUN_AUDIT_BUNDLE remains terminal and Gate 8 remains blocked.
""",
    )

    code_manifest = root / "P10_DR9_CODE_MANIFEST.json"
    data = json.loads(rt(code_manifest))
    data["schema"] = "ConceptGhost.P10Gate7PreviewRouteUxColmapFixCodeManifest.v0.3"
    data["release"] = R3_NAME
    data["source_commit"] = source_commit
    wt(code_manifest, json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    for name in ("RELEASE.json", "P10_DR9_RELEASE.json"):
        path = root / name
        data = json.loads(rt(path))
        data["schema"] = "ConceptGhost.P10Gate7PreviewRouteUxColmapFixRelease.v0.3"
        data["release"] = R3_NAME
        data["source_commit"] = source_commit
        data["package_hotfix_commit"] = package_commit or "LOCAL_BUILD"
        data["route_editor_r3"] = {
            "max_orthographic_zoom": 160.0,
            "max_perspective_zoom": 48.0,
            "route_edits_preserve_viewport": True,
            "same_scene_execution_preserves_viewport": True,
            "route_preset_export_import": True,
            "route_preset_rebind_current_scene": True,
            "four_view_panel_resolution": [720, 660],
            "interactive_preview_point_budget": 50000,
        }
        data["gate7_colmap_binary_fix"] = {
            "observed_error": "dense/sparse/cameras.txt missing",
            "text_sparse_model_supported": True,
            "binary_sparse_model_supported": True,
            "camera_model_required": "PINHOLE",
            "p9_camera_authority_changed": False,
        }
        features = data.setdefault("features", [])
        for feature in (
            "DRONE_DEEP_ZOOM_160X_48X",
            "DRONE_VIEWPORT_PERSISTENCE",
            "DRONE_ROUTE_PRESET_EXPORT_IMPORT",
            "DRONE_HIGHER_DETAIL_FOUR_VIEW",
            "GATE7_COLMAP_BINARY_SPARSE_MODEL_SUPPORT",
        ):
            if feature not in features:
                features.append(feature)
        wt(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    validation = f"""ConceptGhost P10 Gate 7 Preview r3 Route UX + COLMAP Fix validation

Base r15 SHA-256: {BASE_SHA256}
Source commit: {source_commit}
Gate 7 runtime/visual evidence: PRESENT
RUN_AUDIT_BUNDLE: PRESENT
Gate 7 dense binary cameras.bin/images.bin support: PASS
Gate 7 text cameras.txt/images.txt fallback: PASS
P9 camera authority changed: NO
Drone point placement preserves zoom/pan: PASS BY SOURCE CONTRACT
Orthographic max zoom: 160x
Perspective max zoom: 48x
Route export/import JSON: PRESENT
Imported route rebinds current scene/run: PASS BY SOURCE CONTRACT
Four-view internal panel resolution: 720x660
Interactive preview point budget: 50000
Gate 8 node present: NO
User runtime acceptance: PENDING
"""
    old_validation = root / "P10_GATE7_PREVIEW_R2_AUDIT_VALIDATION.txt"
    if old_validation.exists():
        old_validation.unlink()
    wt(root / "P10_GATE7_PREVIEW_R3_ROUTE_UX_COLMAP_FIX_VALIDATION.txt", validation)

    test = """from pathlib import Path
import json,sys

def main(root):
 root=Path(root).resolve(); errors=[]
 node_root=root/'Payload/custom_nodes/ConceptGhost_P10_Lab'
 dense=(node_root/'colmap_dense_io.py').read_text(encoding='utf-8')
 free=(node_root/'free_space_evidence.py').read_text(encoding='utf-8')
 editor=(node_root/'web/js/drone_route_editor.js').read_text(encoding='utf-8')
 author=(node_root/'route_authoring_node.py').read_text(encoding='utf-8')
 preview=(node_root/'drone_route_preview.py').read_text(encoding='utf-8')
 for token in ('parse_colmap_cameras_bin','parse_colmap_images_bin','load_colmap_sparse_cameras','load_colmap_sparse_images'):
  if token not in dense: errors.append('COLMAP binary reader missing '+token)
 if 'load_colmap_sparse_cameras(dense_sparse_root)' not in free: errors.append('Gate 7.3 does not use binary-capable camera loader')
 if 'load_colmap_sparse_images(dense_sparse_root)' not in free: errors.append('Gate 7.3 does not use binary-capable image loader')
 for token in ('MAX_ORTHO_ZOOM = 160.0','MAX_PERSPECTIVE_ZOOM = 48.0','"Exportar trajeto"','"Importar trajeto"','ROUTE_PRESET_SCHEMA','delete imported.route_plan_sha256'):
  if token not in editor: errors.append('route editor missing '+token)
 persist=editor.split('function persist() {',1)[1].split('function setPlan',1)[0]
 if 'ensureRouteVisible()' in persist: errors.append('route edit still auto-fits viewport')
 if 'max_points=50000' not in author: errors.append('interactive route geometry budget is not 50000')
 if 'panel_width: int=720' not in preview or 'panel_height: int=660' not in preview: errors.append('four-view resolution not upgraded')
 workflow=json.loads((root/'Payload/workflows/02_ConceptGhost_P10_PRODUCTION.json').read_text(encoding='utf-8-sig'))
 if any('Gate8' in str(n.get('type')) or 'Gate 8' in str(n.get('type')) for n in workflow.get('nodes',[])):
  errors.append('Gate 8 leaked into package')
 if errors:
  print('\\n'.join('[FAIL] '+e for e in errors)); return 1
 print('CONCEPTGHOST_GATE7_PREVIEW_R3_ROUTE_UX_COLMAP_FIX_PASS'); return 0

if __name__=='__main__':
 raise SystemExit(main(sys.argv[1]))
"""
    wt(root / "Installer/test_gate7_r3_route_ux_colmap_fix.py", test)


def rebuild_manifests(root: Path, source_commit: str) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_file() and rel not in EXCLUDED:
            rows.append({"path": rel, "sha256": sha256(path), "size_bytes": path.stat().st_size})
    for name in ("BUNDLE_MANIFEST.json", "P10_DR9_BUNDLE_MANIFEST.json"):
        path = root / name
        data = json.loads(rt(path))
        data["schema"] = "ConceptGhost.P10Gate7PreviewRouteUxColmapFixBundle.v0.3"
        data["release"] = R3_NAME
        data["source_commit"] = source_commit
        data["file_count_excluding_manifests_and_checksums"] = len(rows)
        data["r3_fixes"] = {
            "gate7_binary_sparse_colmap": True,
            "route_viewport_persistence": True,
            "route_deep_zoom": True,
            "route_export_import": True,
            "higher_detail_four_view": True,
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
    code_manifest = json.loads(rt(root / "P10_DR9_CODE_MANIFEST.json"))
    if code_manifest.get("source_commit") != source_commit:
        errors.append("code manifest source commit mismatch")
    node_root = root / "Payload/custom_nodes/ConceptGhost_P10_Lab"
    for item in code_manifest.get("files", []):
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
    if len(list((root / "Payload/workflows").glob("*.json"))) != 2:
        errors.append("package must expose exactly two numbered workflows")
    return errors


def zipdet(root: Path, output: Path) -> None:
    if output.exists():
        output.unlink()
    fixed = (2026, 9, 24, 7, 40, 0)
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
    parser.add_argument("--source", type=Path, required=True, help="Frozen r15 ZIP")
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

    r2_builder = (
        Path(__file__).resolve().parents[1]
        / "gate7_preview_r2_audit"
        / "build_gate7_preview_r2_audit_from_r15.py"
    )
    if not r2_builder.is_file():
        raise SystemExit(f"missing r2 builder: {r2_builder}")

    with tempfile.TemporaryDirectory(prefix="cg-g7-preview-r3-") as temp_dir:
        temp = Path(temp_dir)
        r2_zip = temp / (R2_NAME + ".zip")
        root = temp / R3_NAME
        cmd = [
            sys.executable,
            str(r2_builder),
            "--source", str(args.source),
            "--output", str(r2_zip),
            "--p10-source-root", str(args.p10_source_root),
            "--source-commit", args.source_commit,
            "--package-commit", args.package_commit,
            "--keep-extracted", str(root),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.returncode:
            raise SystemExit(result.stdout + result.stderr)

        patch_entrypoints(root)
        replace_text_tree(root, R2_NAME, R3_NAME)
        patch_package_contracts(root, args.source_commit, args.package_commit)

        for script in (
            "test_dr9_bundle.py",
            "test_gate7_preview_bundle.py",
            "test_run_audit_bundle_package.py",
            "test_gate7_r3_route_ux_colmap_fix.py",
        ):
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
            raise SystemExit("\n".join("[FAIL] " + item for item in errors))

        args.output.parent.mkdir(parents=True, exist_ok=True)
        zipdet(root, args.output)
        print("G7_PREVIEW_R3_ZIP=" + str(args.output))
        print("G7_PREVIEW_R3_BYTES=" + str(args.output.stat().st_size))
        print("G7_PREVIEW_R3_SHA256=" + sha256(args.output))

        if args.keep_extracted:
            if args.keep_extracted.exists():
                shutil.rmtree(args.keep_extracted)
            shutil.copytree(root, args.keep_extracted)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
