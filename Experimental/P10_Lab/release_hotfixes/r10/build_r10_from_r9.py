from __future__ import annotations

import argparse
import hashlib
import json
import os
import py_compile
import shutil
import tempfile
import zipfile
from pathlib import Path

R9_SHA256 = "1143e94e0fcbfcf25809efa0a21fae162fa79079c3223b8ea2eec677069609bf"
P10_SOURCE_COMMIT = "f9ca7c6070a10c9c39a241ef9ebe8c4822988f66"
R9_NAME = "ConceptGhost_v1.54_P10_DR9R_MOGE_DIAGNOSTICS_TWO_STAGE_INSTALLER_r9"
R10_NAME = "ConceptGhost_v1.54_P10_DR9R_MOGE_DIAGNOSTICS_TWO_STAGE_INSTALLER_r10"
EXCLUDED_FROM_BUNDLE_MANIFEST = {"BUNDLE_MANIFEST.json", "P10_DR9_BUNDLE_MANIFEST.json", "SHA256SUMS.txt"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str, *, newline: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline=newline) as f:
        f.write(text)


def replace_required(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"required replacement missing ({label}): {old}")
    return text.replace(old, new)


def patch_versions(root: Path) -> None:
    # Preserve BAT CRLF while changing only release labels.
    for rel in ("03_INSTALL_ALL.bat", "04_VERIFY_INSTALL.bat"):
        p = root / rel
        raw = p.read_bytes()
        if b"r9" not in raw:
            raise RuntimeError(f"expected r9 label missing in {rel}")
        p.write_bytes(raw.replace(b"r9", b"r10"))

    p = root / "Installer" / "install_dr9.ps1"
    s = read_text(p)
    replacements = {
        "OPTIONAL MOGE DIAGNOSTICS r9": "OPTIONAL MOGE DIAGNOSTICS r10",
        "ConceptGhost_P10_Lab_before_dr9r_r9": "ConceptGhost_P10_Lab_before_dr9r_r10",
        R9_NAME: R10_NAME,
        "P10_DR9R_R9_READY.json": "P10_DR9R_R10_READY.json",
        "DR9R r9 runtime verification failed.": "DR9R r10 runtime verification failed.",
        "[PASS] DR9R r9 installed and statically verified.": "[PASS] DR9R r10 installed and statically verified.",
    }
    for old, new in replacements.items():
        s = replace_required(s, old, new, f"install_dr9 {old}")
    write_text(p, s)

    p = root / "Installer" / "verify_dr9.ps1"
    s = read_text(p)
    s = replace_required(s, "P10_DR9R_R9_READY_VERIFY.json", "P10_DR9R_R10_READY_VERIFY.json", "verify report")
    s = replace_required(s, "DR9R r9 installation verified.", "DR9R r10 installation verified.", "verify label")
    write_text(p, s)

    p = root / "Installer" / "verify_p10_dr9.py"
    s = read_text(p)
    s = replace_required(s, "ConceptGhost.P10DR9RRuntimeVerify.v0.9", "ConceptGhost.P10DR9RRuntimeVerify.v0.10", "runtime schema")
    s = replace_required(s, "CONCEPTGHOST_P10_DR9R_R9_INSTALLER_HOTFIX_RUNTIME_VERIFY_PASS", "CONCEPTGHOST_P10_DR9R_R10_NESTED_INSTALLER_RUNTIME_VERIFY_PASS", "runtime pass marker")
    write_text(p, s)


def overlay_hotfix(root: Path, hotfix_dir: Path) -> None:
    for name in ("install_gate5.ps1", "install_gate6.ps1"):
        src = hotfix_dir / "Installer" / name
        if not src.is_file():
            raise RuntimeError(f"missing hotfix source: {src}")
        shutil.copy2(src, root / "Installer" / name)


def update_bundle_test(root: Path) -> None:
    p = root / "Installer" / "test_dr9_bundle.py"
    s = read_text(p)
    s = replace_required(s, "root/'USER_GUIDE_DR9R_R9.md'", "root/'USER_GUIDE_DR9R_R10.md'", "r10 user guide")
    # Preserve the P10 payload source commit authority; package hotfix is installer-only.
    write_text(p, s)

    test = r'''from pathlib import Path
import json
import sys


def main(root):
    root = Path(root).resolve()
    errors = []
    gate5 = (root / "Installer" / "install_gate5.ps1").read_text(encoding="utf-8-sig")
    gate6 = (root / "Installer" / "install_gate6.ps1").read_text(encoding="utf-8-sig")
    prod = root / "Payload" / "workflows" / "02_ConceptGhost_P10_PRODUCTION.json"
    route = root / "Payload" / "workflows" / "01_ConceptGhost_P10_ROUTE_SETUP.json"
    workflow_names = sorted(p.name for p in (root / "Payload" / "workflows").glob("*.json"))

    for label, source, private_name in (
        ("Gate5", gate5, "02_ConceptGhost_P10_PRODUCTION_GATE5_VERIFY.json"),
        ("Gate6", gate6, "02_ConceptGhost_P10_PRODUCTION_GATE6_VERIFY.json"),
    ):
        if "CONCEPTGHOST_INTERNAL_BASE_WORKFLOW_ONLY" not in source:
            errors.append(f"{label}: internal compatibility flag missing")
        if "workflows\\02_ConceptGhost_P10_PRODUCTION.json" not in source:
            errors.append(f"{label}: current Production verifier fixture missing")
        if private_name not in source:
            errors.append(f"{label}: private verifier destination missing")
        if "internal\\workflows" not in source:
            errors.append(f"{label}: private workflow root missing")

    if workflow_names != ["01_ConceptGhost_P10_ROUTE_SETUP.json", "02_ConceptGhost_P10_PRODUCTION.json"]:
        errors.append(f"public workflow payload is not current-only: {workflow_names}")
    if not route.is_file() or not prod.is_file():
        errors.append("numbered workflow payload missing")
    else:
        w = json.loads(prod.read_text(encoding="utf-8-sig"))
        by = {n["id"]: n for n in w["nodes"]}
        expected = {
            2100: "ConceptGhostP10RefinedEvidencePreview",
            2207: "ConceptGhostP10WanSequentialSampler",
            2300: "ConceptGhostP10ReconstructionRuntime",
            2301: "PreviewImage",
        }
        for node_id, node_type in expected.items():
            if by.get(node_id, {}).get("type") != node_type:
                errors.append(f"Production node {node_id} != {node_type}")

    release = json.loads((root / "RELEASE.json").read_text(encoding="utf-8-sig"))
    if release.get("release") != "ConceptGhost_v1.54_P10_DR9R_MOGE_DIAGNOSTICS_TWO_STAGE_INSTALLER_r10":
        errors.append("r10 release metadata missing")
    if release.get("schema") != "ConceptGhost.P10DR9RRelease.v0.10":
        errors.append("r10 release schema missing")

    if errors:
        print("\n".join("[FAIL] " + e for e in errors))
        return 1
    print("CONCEPTGHOST_DR9R_R10_NESTED_INSTALLER_BUNDLE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
'''
    write_text(root / "Installer" / "test_r10_bundle.py", test)


def update_docs_and_release(root: Path, hotfix_commit: str) -> None:
    old_guide = root / "USER_GUIDE_DR9R_R9.md"
    new_guide = root / "USER_GUIDE_DR9R_R10.md"
    guide = read_text(old_guide)
    guide = guide.replace("DR9R R9", "DR9R R10").replace("DR9R r9", "DR9R r10")
    guide += """

## r10 nested installer compatibility hotfix

The r10 package fixes the target-machine failure discovered after the r9 base stack had already passed. The inherited Gate5 and Gate6 installers no longer require removed historical preview workflows while DR9R runs in private/internal verifier mode. Both stages reuse the current `02_ConceptGhost_P10_PRODUCTION.json` only as a private verifier fixture below `%LOCALAPPDATA%\\ConceptGhost\\internal\\workflows`; no legacy Gate5/Gate6 preview workflow is installed for the artist.

This change is installer compatibility only. P9 authority, current P10 code, MoGe diagnostics, route authoring, WAN, COLMAP reconstruction, immutable P10 attempts, storage policy and the dual-Maya non-overwrite contract are unchanged.
"""
    write_text(new_guide, guide)
    old_guide.unlink()

    readme = read_text(root / "README.md")
    readme = readme.replace("# ConceptGhost P10 — DR9R r9 Two-Stage Installer", "# ConceptGhost P10 — DR9R r10 Two-Stage Installer")
    readme += """

## r10 nested Gate5/Gate6 installer compatibility

r10 supersedes r9 for runtime acceptance. The protected two-stage package still exposes only `01_ConceptGhost_P10_ROUTE_SETUP.json` and `02_ConceptGhost_P10_PRODUCTION.json`. During the inherited Gate5/Gate6 bootstrap, the current Production workflow is reused privately under `%LOCALAPPDATA%\\ConceptGhost\\internal\\workflows` for verifier compatibility, so removed historical Gate5/Gate6 preview workflows are no longer required or installed.
"""
    write_text(root / "README.md", readme)

    hotfix_doc = f"""# ConceptGhost P10 DR9R — r10 Nested Installer Compatibility Hotfix

Date: 2026-09-23

## Trigger

The target-machine r9 installation passed the protected shared-Python fingerprint, MoGe runtime verification, Maya verification and the complete v1.53 base verification, then stopped inside inherited Gate5 because that legacy installer still required a removed Gate5 preview workflow. Gate6 contained the same latent dependency.

## Correction

When `CONCEPTGHOST_INTERNAL_BASE_WORKFLOW_ONLY=1` is set by DR9R:

- Gate5 uses `02_ConceptGhost_P10_PRODUCTION.json` as a private verifier fixture.
- Gate6 uses the same current Production workflow as a private verifier fixture.
- Private verifier copies live only below `%LOCALAPPDATA%\\ConceptGhost\\internal\\workflows`.
- Historical Gate5/Gate6 preview JSON files are not required and are not installed in the artist workflow folder.
- Standalone legacy Gate5/Gate6 behavior remains unchanged outside the explicit internal DR9R mode.

The public workflow contract remains exactly two numbered workflows: Route Setup and Production.

## Authority

Installer compatibility only. P9 accepted authority and P10 geometry/runtime code are unchanged. MoGe diagnostics remain optional/OFF by default. Gate 7 stays blocked until target-machine runtime acceptance succeeds.

## Provenance

- Base package: `{R9_NAME}.zip`
- Base package SHA-256: `{R9_SHA256}`
- P10 payload source commit: `{P10_SOURCE_COMMIT}`
- r10 hotfix/build commit: `{hotfix_commit or 'LOCAL_BUILD'}`
"""
    write_text(root / "Payload" / "docs" / "23_DR9R_R10_NESTED_INSTALLER_COMPATIBILITY.md", hotfix_doc)

    for name in ("RELEASE.json", "P10_DR9_RELEASE.json"):
        p = root / name
        d = json.loads(read_text(p))
        d["schema"] = "ConceptGhost.P10DR9RRelease.v0.10"
        d["release"] = R10_NAME
        d["status"] = "READY_FOR_USER_RUNTIME_ACCEPTANCE_AFTER_R10_NESTED_INSTALLER_HOTFIX"
        d["source_commit"] = P10_SOURCE_COMMIT
        d["package_hotfix_commit"] = hotfix_commit or "LOCAL_BUILD"
        d["base_package"] = {"release": R9_NAME, "sha256": R9_SHA256}
        features = list(d.get("features", []))
        for feat in (
            "PRIVATE_GATE5_CURRENT_PRODUCTION_VERIFIER_FIXTURE",
            "PRIVATE_GATE6_CURRENT_PRODUCTION_VERIFIER_FIXTURE",
            "NO_LEGACY_GATE5_GATE6_PREVIEW_REQUIRED_IN_DR9R_MODE",
        ):
            if feat not in features:
                features.append(feat)
        d["features"] = features
        write_text(p, json.dumps(d, indent=2, ensure_ascii=False) + "\n")

    validation = f"""ConceptGhost P10 DR9R r10 validation

Package build status: PASS
Base package: {R9_NAME}.zip
Base package SHA-256: {R9_SHA256}
P10 payload source commit: {P10_SOURCE_COMMIT}
r10 hotfix/build commit: {hotfix_commit or 'LOCAL_BUILD'}
Bundle static contract: PASS
Installer Python compile: PASS
P10 code manifest/hash validation: PASS
Current-only workflow policy: PASS
Gate5 private current-Production verifier fixture: INCLUDED
Gate6 private current-Production verifier fixture: INCLUDED
Legacy Gate5/Gate6 preview requirement in DR9R mode: REMOVED
Shared-Python canonical package fingerprint protection: RETAINED
Private legacy Master verifier fixture: RETAINED / NOT USER-VISIBLE
Optional MoGe diagnostics: INCLUDED / OFF BY DEFAULT / DIAGNOSTIC ONLY
User runtime acceptance: PENDING

Required target-machine runtime acceptance:
- 03_INSTALL_ALL.bat completes Gate5 + Gate6 bootstrap without requiring legacy preview JSON
- canonical shared-Python integrity remains PASS
- only workflows 01/02 are visible in ComfyUI
- Workflow 01 Run #1 -> edit -> Run #2
- Workflow 02 Run #3 with visible AUTO_LATEST resolution
- route reset / Enquadrar tudo / zoom / pan runtime check
- attempt-scoped Gate4/Gate5/Gate6 outputs
- optional MoGe diagnostics ON test separately
- P9 Maya remains unchanged
"""
    write_text(root / "P10_DR9_VALIDATION.txt", validation)


def regenerate_manifests(root: Path) -> None:
    # Bundle manifests intentionally exclude themselves and SHA256SUMS to avoid cycles.
    files = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if rel in EXCLUDED_FROM_BUNDLE_MANIFEST:
            continue
        files.append({"path": rel, "sha256": sha256(p), "size_bytes": p.stat().st_size})

    template = json.loads(read_text(root / "BUNDLE_MANIFEST.json"))
    template["schema"] = "ConceptGhost.P10DR9RBundle.v0.10"
    template["release"] = R10_NAME
    template["status"] = "READY_FOR_USER_RUNTIME_ACCEPTANCE_AFTER_R10_NESTED_INSTALLER_HOTFIX"
    template["source_commit"] = P10_SOURCE_COMMIT
    template["file_count_excluding_manifests_and_checksums"] = len(files)
    template["nested_installer_compatibility"] = {
        "gate5_private_current_production_fixture": True,
        "gate6_private_current_production_fixture": True,
        "legacy_preview_workflows_required_in_dr9r_mode": False,
    }
    template["files"] = files
    payload = json.dumps(template, indent=2, ensure_ascii=False) + "\n"
    write_text(root / "BUNDLE_MANIFEST.json", payload)
    write_text(root / "P10_DR9_BUNDLE_MANIFEST.json", payload)

    # SHA256SUMS includes both generated manifests, but not itself.
    lines = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if rel == "SHA256SUMS.txt":
            continue
        lines.append(f"{sha256(p)}  {rel}")
    write_text(root / "SHA256SUMS.txt", "\n".join(lines) + "\n")


def static_validate(root: Path) -> list[str]:
    errors = []
    workflows = sorted(p.name for p in (root / "Payload" / "workflows").glob("*.json"))
    if workflows != ["01_ConceptGhost_P10_ROUTE_SETUP.json", "02_ConceptGhost_P10_PRODUCTION.json"]:
        errors.append(f"wrong workflow payload: {workflows}")

    for label, name, private_name in (
        ("Gate5", "install_gate5.ps1", "02_ConceptGhost_P10_PRODUCTION_GATE5_VERIFY.json"),
        ("Gate6", "install_gate6.ps1", "02_ConceptGhost_P10_PRODUCTION_GATE6_VERIFY.json"),
    ):
        s = read_text(root / "Installer" / name)
        for required in (
            "CONCEPTGHOST_INTERNAL_BASE_WORKFLOW_ONLY",
            "workflows\\02_ConceptGhost_P10_PRODUCTION.json",
            "internal\\workflows",
            private_name,
        ):
            if required not in s:
                errors.append(f"{label} missing {required}")

    # Verify code manifest stays byte-identical against packaged P10 payload.
    manifest = json.loads(read_text(root / "P10_DR9_CODE_MANIFEST.json"))
    if manifest.get("source_commit") != P10_SOURCE_COMMIT:
        errors.append("P10 code manifest source commit changed")
    p10 = root / "Payload" / "custom_nodes" / "ConceptGhost_P10_Lab"
    for item in manifest.get("files", []):
        p = p10 / item["path"]
        if not p.is_file():
            errors.append(f"P10 code missing: {item['path']}")
        elif sha256(p) != item["sha256"]:
            errors.append(f"P10 code hash mismatch: {item['path']}")

    for p in list((root / "Installer").glob("*.py")) + list(p10.glob("*.py")):
        try:
            py_compile.compile(str(p), doraise=True)
        except Exception as exc:
            errors.append(f"python compile failed {p.name}: {exc}")

    # SHA256SUMS recheck.
    for raw in read_text(root / "SHA256SUMS.txt").splitlines():
        if not raw.strip():
            continue
        digest, rel = raw.split("  ", 1)
        p = root / rel
        if not p.is_file() or sha256(p) != digest:
            errors.append(f"SHA256SUMS mismatch: {rel}")
    return errors


def deterministic_zip(root: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    # Fixed timestamp permits byte-identical rebuilds from same inputs.
    fixed = (2026, 9, 23, 20, 30, 0)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(root.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            info = zipfile.ZipInfo(rel, date_time=fixed)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, type=Path, help="validated r9 ZIP")
    ap.add_argument("--output", required=True, type=Path, help="r10 ZIP path")
    ap.add_argument("--hotfix-dir", type=Path, default=Path(__file__).resolve().parent)
    ap.add_argument("--hotfix-commit", default=os.environ.get("GITHUB_SHA", ""))
    ap.add_argument("--keep-extracted", type=Path)
    args = ap.parse_args()

    if sha256(args.source) != R9_SHA256:
        raise SystemExit(f"wrong r9 source SHA-256: {sha256(args.source)}")

    with tempfile.TemporaryDirectory(prefix="conceptghost-r10-") as td:
        root = Path(td) / R10_NAME
        root.mkdir()
        with zipfile.ZipFile(args.source, "r") as zf:
            zf.extractall(root)

        overlay_hotfix(root, args.hotfix_dir)
        patch_versions(root)
        update_bundle_test(root)
        update_docs_and_release(root, args.hotfix_commit)
        regenerate_manifests(root)

        errors = static_validate(root)
        if errors:
            raise SystemExit("\n".join("[FAIL] " + e for e in errors))

        # Imported bundle verifier catches the broader r9 contract with the r10 guide path.
        import subprocess
        for script in ("test_dr9_bundle.py", "test_r10_bundle.py"):
            proc = subprocess.run(
                [os.sys.executable, str(root / "Installer" / script), str(root)],
                text=True,
                capture_output=True,
            )
            if proc.returncode:
                raise SystemExit(proc.stdout + proc.stderr)
            print(proc.stdout.strip())

        deterministic_zip(root, args.output)
        digest = sha256(args.output)
        print(f"R10_ZIP={args.output}")
        print(f"R10_BYTES={args.output.stat().st_size}")
        print(f"R10_SHA256={digest}")
        if args.keep_extracted:
            if args.keep_extracted.exists():
                shutil.rmtree(args.keep_extracted)
            shutil.copytree(root, args.keep_extracted)
            print(f"R10_EXTRACTED={args.keep_extracted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())