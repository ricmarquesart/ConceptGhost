from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


BASE_NAME = "ConceptGhost_v1.54_P10_DR9R_MOGE_DIAGNOSTICS_TWO_STAGE_INSTALLER_r15"
BASE_SHA256 = "cab56065d612e7e038bcb526307047d57134262471098e56d0225b74defee3dd"
PREVIEW_NAME = "ConceptGhost_v1.54_P10_GATE7_PREVIEW_r1"
P10_SOURCE_COMMIT = "ebf41821177b384d18565f5c7bcb813901bbc7b6"
OLD_SOURCE_COMMIT = "98059287678e96280990dbf9c1888789f515213e"
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
    workflow.setdefault("links", []).append(
        [link_id, origin_id, origin_slot, target_id, target_slot, typ]
    )
    by_id = {int(node["id"]): node for node in workflow["nodes"]}
    output = by_id[origin_id]["outputs"][origin_slot]
    if output.get("links") is None:
        output["links"] = []
    output["links"].append(link_id)
    by_id[target_id]["inputs"][target_slot]["link"] = link_id
    return link_id


def patch_production_workflow(root: Path) -> None:
    path = root / "Payload/workflows/02_ConceptGhost_P10_PRODUCTION.json"
    workflow = json.loads(rt(path))
    by_id = {int(node["id"]): node for node in workflow.get("nodes", [])}
    for required in (2097, 2098, 2300, 2301):
        if required not in by_id:
            raise RuntimeError(f"r15 Production workflow missing node {required}")
    for forbidden in (2400, 2401, 2410, 2411, 2412):
        if forbidden in by_id:
            raise RuntimeError(f"Gate 7 Preview node id already exists: {forbidden}")

    max_order = max(int(node.get("order") or 0) for node in workflow["nodes"])

    gate7 = {
        "id": 2400,
        "type": "ConceptGhostP10Gate7Runtime",
        "pos": [16350, 9520],
        "size": [760, 520],
        "flags": {},
        "order": max_order + 1,
        "mode": 0,
        "inputs": [
            {"name": "p9_run_dir", "type": "STRING", "link": None},
            {"name": "reconstruction_runtime_manifest_path", "type": "STRING", "link": None},
            {"name": "resume_existing", "type": "BOOLEAN", "widget": {"name": "resume_existing"}, "link": None},
            {"name": "run_delaunay", "type": "BOOLEAN", "widget": {"name": "run_delaunay"}, "link": None},
            {"name": "colmap_executable", "type": "STRING", "widget": {"name": "colmap_executable"}, "link": None},
            {"name": "output_root", "type": "STRING", "widget": {"name": "output_root"}, "link": None},
        ],
        "outputs": [
            {"name": "gate7_review_image", "type": "IMAGE", "links": None, "slot_index": 0},
            {"name": "protected_fusion_candidate_ply", "type": "STRING", "links": None, "slot_index": 1},
            {"name": "gate7_runtime_manifest_path", "type": "STRING", "links": None, "slot_index": 2},
            {"name": "registration_manifest_path", "type": "STRING", "links": None, "slot_index": 3},
            {"name": "confidence_manifest_path", "type": "STRING", "links": None, "slot_index": 4},
            {"name": "confidence_free_space_overlay_manifest_path", "type": "STRING", "links": None, "slot_index": 5},
            {"name": "dataset_manifest_path", "type": "STRING", "links": None, "slot_index": 6},
            {"name": "pre_fusion_mesh_path", "type": "STRING", "links": None, "slot_index": 7},
            {"name": "protected_fusion_manifest_path", "type": "STRING", "links": None, "slot_index": 8},
            {"name": "visual_review_manifest_path", "type": "STRING", "links": None, "slot_index": 9},
            {"name": "diagnostics_json", "type": "STRING", "links": None, "slot_index": 10},
        ],
        "properties": {"Node name for S&R": "ConceptGhostP10Gate7Runtime"},
        "widgets_values": [True, True, "", ""],
        "title": "02 · STEP 5 · GATE 7 · REGISTRATION → PROTECTED FUSION",
    }
    gate7_preview = {
        "id": 2401,
        "type": "PreviewImage",
        "pos": [17180, 9520],
        "size": [570, 430],
        "flags": {},
        "order": max_order + 2,
        "mode": 0,
        "inputs": [{"name": "images", "type": "IMAGE", "link": None}],
        "outputs": [],
        "properties": {"Node name for S&R": "PreviewImage"},
        "widgets_values": [],
        "title": "GATE 7 · RESULT · P9 + ACCEPTED P10 + FREE/CONFLICT REVIEW",
    }
    visual_pack = {
        "id": 2410,
        "type": "ConceptGhostP10Gate7VisualEvidencePack",
        "pos": [16350, 10180],
        "size": [760, 420],
        "flags": {},
        "order": max_order + 3,
        "mode": 0,
        "inputs": [
            {"name": "gate7_runtime_manifest_path", "type": "STRING", "link": None},
            {"name": "dr9r_runtime_accepted", "type": "BOOLEAN", "widget": {"name": "dr9r_runtime_accepted"}, "link": None},
            {"name": "artist_visual_review_approved", "type": "BOOLEAN", "widget": {"name": "artist_visual_review_approved"}, "link": None},
            {"name": "output_root", "type": "STRING", "widget": {"name": "output_root"}, "link": None},
        ],
        "outputs": [
            {"name": "visual_evidence_index", "type": "IMAGE", "links": None, "slot_index": 0},
            {"name": "visual_pack_manifest_path", "type": "STRING", "links": None, "slot_index": 1},
            {"name": "confidence_before_after_png", "type": "STRING", "links": None, "slot_index": 2},
            {"name": "drone_before_after_gif", "type": "STRING", "links": None, "slot_index": 3},
            {"name": "gate7_closeout_manifest_path", "type": "STRING", "links": None, "slot_index": 4},
            {"name": "diagnostics_json", "type": "STRING", "links": None, "slot_index": 5},
        ],
        "properties": {"Node name for S&R": "ConceptGhostP10Gate7VisualEvidencePack"},
        "widgets_values": [False, False, ""],
        "title": "VISUAL BRANCH · G7.1→G7.6 · PREVIEWS + BEFORE/AFTER · TERMINAL",
    }
    visual_preview = {
        "id": 2411,
        "type": "PreviewImage",
        "pos": [17180, 10180],
        "size": [570, 430],
        "flags": {},
        "order": max_order + 4,
        "mode": 0,
        "inputs": [{"name": "images", "type": "IMAGE", "link": None}],
        "outputs": [],
        "properties": {"Node name for S&R": "PreviewImage"},
        "widgets_values": [],
        "title": "VISUAL EVIDENCE INDEX · EVERY GATE · DIAGNOSTIC ONLY",
    }
    note = {
        "id": 2412,
        "type": "ConceptGhostP10WorkflowInstructions",
        "pos": [17820, 10180],
        "size": [720, 430],
        "flags": {},
        "order": max_order + 5,
        "mode": 0,
        "inputs": [
            {
                "name": "instructions",
                "type": "STRING",
                "widget": {"name": "instructions"},
                "link": None,
            }
        ],
        "outputs": [
            {"name": "instructions", "type": "STRING", "links": None, "slot_index": 0}
        ],
        "properties": {"Node name for S&R": "ConceptGhostP10WorkflowInstructions"},
        "widgets_values": [
            "GATE 7 VISUAL EVIDENCE\n\n"
            "Este branch termina aqui e NAO alimenta geometria.\n\n"
            "Ele gera previews por gate, confidence BLUE=HIGH / RED=LOW, "
            "comparacoes BEFORE/AFTER e um GIF usando exatamente as mesmas cameras do drone.\n\n"
            "dr9r_runtime_accepted e artist_visual_review_approved permanecem FALSE. "
            "Nao altere para TRUE antes do teste real e da revisao visual.\n\n"
            "Mesmo com CI PASS, Gate 8 continua bloqueado."
        ],
        "title": "GATE 7 · COMO JULGAR OS OUTPUTS VISUAIS",
    }
    workflow["nodes"].extend([gate7, gate7_preview, visual_pack, visual_preview, note])
    workflow["last_node_id"] = 2412

    _next_link(workflow, 2098, 0, 2400, 0, "STRING")
    _next_link(workflow, 2300, 3, 2400, 1, "STRING")
    _next_link(workflow, 2400, 0, 2401, 0, "IMAGE")
    _next_link(workflow, 2400, 2, 2410, 0, "STRING")
    _next_link(workflow, 2410, 0, 2411, 0, "IMAGE")

    start = by_id[2097]
    start["widgets_values"] = [
        "WORKFLOW 02 — P10 PRODUCTION + GATE 7 PREVIEW\n\n"
        "Pre-requisito: Workflow 01 terminou o RUN #2 com READY / production_ready=true.\n\n"
        "Deixe production_entry_path = AUTO_LATEST para o fluxo normal.\n\n"
        "RUN #3: clique Run UMA VEZ. O fluxo executa Evidence → WAN → Reconstruction "
        "→ Gate 7 Registration/Provenance/Confidence/Free-Space/Protected Fusion.\n\n"
        "O branch VISUAL EVIDENCE termina em previews: ele NAO modifica P9/P10, "
        "nao alimenta a geometria e nao libera Gate 8.\n\n"
        "Observe especialmente o confidence BLUE=HIGH / RED=LOW e o caminho do "
        "GIF BEFORE/AFTER da mesma camera do drone."
    ]
    start["title"] = "02 · START HERE · RUN #3 · P10 + GATE 7 PREVIEW"

    workflow.setdefault("groups", []).extend([
        {
            "title": "GATE 7 · REGISTRATION / PROVENANCE / FREE-SPACE / PROTECTED FUSION",
            "bounding": [16280, 9280, 1540, 730],
            "color": "#5a4778",
            "font_size": 24,
            "flags": {},
        },
        {
            "title": "VISUAL EVIDENCE · TERMINAL BRANCHES · DOES NOT FEED GEOMETRY",
            "bounding": [16280, 10090, 2320, 600],
            "color": "#3f6d63",
            "font_size": 24,
            "flags": {},
        },
    ])
    extra = workflow.setdefault("extra", {}).setdefault("conceptghost", {})
    extra["gate7_preview"] = True
    extra["gate7_preview_release"] = "GATE7_PREVIEW_R1"
    extra["visual_evidence_terminal"] = True
    extra["gate8_promotion_default"] = False
    extra["queue_sequence"] = ["RUN_3_P10_PRODUCTION_AND_GATE7_PREVIEW"]
    wt(path, json.dumps(workflow, indent=2, ensure_ascii=False) + "\n")


def overlay_p10_source(root: Path, source_root: Path) -> None:
    target = root / "Payload/custom_nodes/ConceptGhost_P10_Lab"
    if not target.is_dir():
        raise RuntimeError("r15 P10 payload root is missing")
    source_root = source_root.resolve()
    required = [
        "gate7_registration.py",
        "gate7_provenance.py",
        "geometry_confidence.py",
        "colmap_dense_io.py",
        "free_space_evidence.py",
        "free_space_constraints.py",
        "free_space_confidence.py",
        "protected_fusion.py",
        "gate7_visual_review.py",
        "visual_evidence_contract.py",
        "visual_comparisons.py",
        "gate7_closeout.py",
        "gate7_runtime.py",
        "gate7_visual_pack.py",
        "preview_nodes.py",
        "prefusion_mesh.py",
    ]
    for name in required:
        if not (source_root / name).is_file():
            raise RuntimeError(f"Gate 7 source file missing: {name}")
    # Copy the complete Python module set from the frozen Gate-7 source checkpoint.
    # Keep the already runtime-tested r15 web/js route editor unchanged.
    for src in sorted(source_root.glob("*.py")):
        shutil.copy2(src, target / src.name)


def update_code_manifest(root: Path) -> None:
    node_root = root / "Payload/custom_nodes/ConceptGhost_P10_Lab"
    manifest_path = root / "P10_DR9_CODE_MANIFEST.json"
    old = json.loads(rt(manifest_path))
    rows = []
    for path in sorted(node_root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix.lower() != ".pyc":
            rows.append(
                {
                    "path": path.relative_to(node_root).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    old["schema"] = "ConceptGhost.P10Gate7PreviewCodeManifest.v0.1"
    old["release"] = PREVIEW_NAME
    old["source_commit"] = P10_SOURCE_COMMIT
    old["files"] = rows
    wt(manifest_path, json.dumps(old, indent=2, ensure_ascii=False) + "\n")


def patch_runtime_verifier(root: Path) -> None:
    path = root / "Installer/verify_p10_dr9.py"
    text = rt(path)
    text = re.sub(
        r"^SOURCE_COMMIT='[0-9a-f]{40}'",
        f"SOURCE_COMMIT='{P10_SOURCE_COMMIT}'",
        text,
        count=1,
        flags=re.M,
    )
    text = text.replace(
        "'ConceptGhostP10ReconstructionRuntime')",
        "'ConceptGhostP10ReconstructionRuntime','ConceptGhostP10Gate7Runtime','ConceptGhostP10Gate7VisualEvidencePack','ConceptGhostP10ConfidenceComparison','ConceptGhostP10DroneMeshComparisonReplay')",
        1,
    )
    old_expected = "expected={2098:'ConceptGhostP10ProductionEntryLoader',2100:'ConceptGhostP10RefinedEvidencePreview',2207:'ConceptGhostP10WanSequentialSampler',2300:'ConceptGhostP10ReconstructionRuntime',2301:'PreviewImage'}"
    new_expected = "expected={2098:'ConceptGhostP10ProductionEntryLoader',2100:'ConceptGhostP10RefinedEvidencePreview',2207:'ConceptGhostP10WanSequentialSampler',2300:'ConceptGhostP10ReconstructionRuntime',2301:'PreviewImage',2400:'ConceptGhostP10Gate7Runtime',2401:'PreviewImage',2410:'ConceptGhostP10Gate7VisualEvidencePack',2411:'PreviewImage',2412:'ConceptGhostP10WorkflowInstructions'}"
    if old_expected not in text:
        raise RuntimeError("r15 runtime verifier Production expected-node block changed")
    text = text.replace(old_expected, new_expected, 1)

    old_links = "for req in ((2098,0,2100,0,'STRING'),(2098,1,2100,4,'STRING'),(2098,2,2100,5,'STRING'),(2100,3,2207,4,'IMAGE'),(2100,4,2207,5,'MASK'),(2100,7,2207,6,'STRING'),(2207,2,2300,0,'STRING'),(2100,8,2300,1,'STRING'),(2300,0,2301,0,'IMAGE')):"
    new_links = "for req in ((2098,0,2100,0,'STRING'),(2098,1,2100,4,'STRING'),(2098,2,2100,5,'STRING'),(2100,3,2207,4,'IMAGE'),(2100,4,2207,5,'MASK'),(2100,7,2207,6,'STRING'),(2207,2,2300,0,'STRING'),(2100,8,2300,1,'STRING'),(2300,0,2301,0,'IMAGE'),(2098,0,2400,0,'STRING'),(2300,3,2400,1,'STRING'),(2400,0,2401,0,'IMAGE'),(2400,2,2410,0,'STRING'),(2410,0,2411,0,'IMAGE')):"
    if old_links not in text:
        raise RuntimeError("r15 runtime verifier Production link block changed")
    text = text.replace(old_links, new_links, 1)

    marker = "checks['production']={'nodes':len(w.get('nodes',[])),'links':len(w.get('links',[])),'auto_latest':True,'p9_solver_present':False}"
    replacement = (
        "if by.get(2400,{}).get('widgets_values')!=[True,True,'','']: fail(errors,'Gate 7 runtime defaults mismatch')\n"
        "            if by.get(2410,{}).get('widgets_values')!=[False,False,'']: fail(errors,'Gate 7 visual pack approvals must default FALSE')\n"
        "            if any('Gate8' in str(t) or 'Gate 8' in str(t) for t in types): fail(errors,'Gate 8 node must not be present in Gate 7 Preview')\n"
        "            " + marker[:-1] + ",'gate7_preview':True,'gate8_default_blocked':True}"
    )
    if marker not in text:
        raise RuntimeError("r15 runtime verifier Production check marker changed")
    text = text.replace(marker, replacement, 1)
    text = text.replace(
        "'schema':'ConceptGhost.P10DR9RRuntimeVerify.v0.15'",
        "'schema':'ConceptGhost.P10Gate7PreviewRuntimeVerify.v0.1'",
        1,
    )
    text = text.replace(
        "CONCEPTGHOST_P10_DR9R_R15_RUNTIME_VERIFY_PASS",
        "CONCEPTGHOST_P10_GATE7_PREVIEW_R1_RUNTIME_VERIFY_PASS",
    )
    wt(path, text)


def patch_entrypoints(root: Path) -> None:
    install_old = root / "Installer/install_dr15.ps1"
    verify_old = root / "Installer/verify_dr15.ps1"
    if not install_old.is_file() or not verify_old.is_file():
        raise RuntimeError("r15 entrypoints are missing")

    install = rt(install_old)
    install = install.replace(
        "ConceptGhost_v1.54_P10_DR9R_MOGE_DIAGNOSTICS_TWO_STAGE_INSTALLER_r15",
        PREVIEW_NAME,
    )
    install = install.replace(OLD_SOURCE_COMMIT, P10_SOURCE_COMMIT)
    install = install.replace("before_dr9r_r15", "before_gate7_preview_r1")
    install = install.replace("DR9R + OPTIONAL MOGE DIAGNOSTICS r15", "GATE 7 PREVIEW r1")
    install = install.replace("DR9R r15", "Gate 7 Preview r1")
    install = install.replace(
        'Write-Host "Workflow 02 is Run once after that commit and defaults to AUTO_LATEST." -ForegroundColor Yellow',
        'Write-Host "Workflow 02 continues through Gate 7 Preview and terminal visual evidence." -ForegroundColor Yellow',
    )
    install = install.replace(
        '$Marker | Add-Member -NotePropertyName p10_dr9_user_runtime_acceptance -NotePropertyValue "PENDING" -Force',
        '$Marker | Add-Member -NotePropertyName p10_dr9_user_runtime_acceptance -NotePropertyValue "PENDING" -Force\n'
        '$Marker | Add-Member -NotePropertyName p10_gate7_preview_status -NotePropertyValue "PENDING_ARTIST_VISUAL_REVIEW" -Force\n'
        '$Marker | Add-Member -NotePropertyName p10_gate8_promotion -NotePropertyValue "BLOCKED" -Force',
    )
    install_new = root / "Installer/install_gate7_preview_r1.ps1"
    wt(install_new, install)

    verify = rt(verify_old)
    verify = verify.replace("final DR9R two-stage contracts", "Gate 7 Preview + visual evidence contracts")
    verify = verify.replace("P10_DR9R_R15_READY_VERIFY.json", "P10_GATE7_PREVIEW_R1_READY_VERIFY.json")
    verify = verify.replace("ConceptGhost P10 DR9R r15 installation verified.", "ConceptGhost P10 Gate 7 Preview r1 installation verified.")
    verify = verify.replace(
        "[PENDING] One real ComfyUI acceptance pass remains.",
        "[PENDING] Gate 7 runtime + artist visual review remain; Gate 8 is blocked.",
    )
    verify_new = root / "Installer/verify_gate7_preview_r1.ps1"
    wt(verify_new, verify)

    install_old.unlink()
    verify_old.unlink()

    bat = r"""@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo 03 - ConceptGhost P10 Gate 7 Preview r1
echo ============================================================
echo Full r15 base + Gate 7 protected-fusion preview + visual branches.
echo Visual evidence is diagnostic-only and Gate 8 remains blocked.
echo Existing WAN/COLMAP assets are reused when already valid.
echo ============================================================
if not exist "%~dp0Installer\install_gate7_preview_r1.ps1" (
  echo.
  echo [FAIL] Required Gate 7 Preview entrypoint is missing.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Installer\install_gate7_preview_r1.ps1"
if errorlevel 1 (
  echo.
  echo [FAIL] Gate 7 Preview r1 installation did not complete.
  pause
  exit /b 1
)
echo.
echo [PASS] Gate 7 Preview r1 installed. Run 04_VERIFY_INSTALL.bat next.
pause
"""
    (root / "03_INSTALL_ALL.bat").write_bytes(bat.replace("\n", "\r\n").encode("utf-8"))

    verify_bat = r"""@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo 04 - VERIFY ConceptGhost P10 Gate 7 Preview r1
echo ============================================================
if not exist "%~dp0Installer\verify_gate7_preview_r1.ps1" (
  echo.
  echo [FAIL] Required Gate 7 Preview verifier is missing.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Installer\verify_gate7_preview_r1.ps1"
if errorlevel 1 (
  echo.
  echo [FAIL] Gate 7 Preview r1 verification failed.
  pause
  exit /b 1
)
echo.
echo [PASS] Gate 7 Preview r1 installation verification completed.
pause
"""
    (root / "04_VERIFY_INSTALL.bat").write_bytes(verify_bat.replace("\n", "\r\n").encode("utf-8"))


def patch_bundle_test(root: Path) -> None:
    path = root / "Installer/test_dr9_bundle.py"
    text = rt(path)
    text = text.replace(
        "root/'USER_GUIDE_DR9R_R15.md'",
        "root/'USER_GUIDE_GATE7_PREVIEW_R1.md'",
    )
    text = text.replace(OLD_SOURCE_COMMIT, P10_SOURCE_COMMIT)
    wt(path, text)

    test = f'''from pathlib import Path
import hashlib,json,py_compile,sys

EXPECTED_SOURCE={P10_SOURCE_COMMIT!r}

def sha256(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def main(root):
 root=Path(root).resolve();e=[]
 wf=root/'Payload/workflows/02_ConceptGhost_P10_PRODUCTION.json'
 node_root=root/'Payload/custom_nodes/ConceptGhost_P10_Lab'
 manifest=json.loads((root/'P10_DR9_CODE_MANIFEST.json').read_text(encoding='utf-8-sig'))
 if manifest.get('source_commit')!=EXPECTED_SOURCE:e.append('source commit mismatch')
 for rel in ['gate7_runtime.py','gate7_visual_pack.py','gate7_closeout.py','visual_evidence_contract.py','visual_comparisons.py','protected_fusion.py','free_space_constraints.py','colmap_dense_io.py']:
  if not (node_root/rel).is_file():e.append('missing Gate7 source '+rel)
 w=json.loads(wf.read_text(encoding='utf-8-sig'));by={{int(n['id']):n for n in w.get('nodes',[])}};types={{n.get('type') for n in w.get('nodes',[])}}
 expected={{2400:'ConceptGhostP10Gate7Runtime',2401:'PreviewImage',2410:'ConceptGhostP10Gate7VisualEvidencePack',2411:'PreviewImage',2412:'ConceptGhostP10WorkflowInstructions'}}
 for nid,typ in expected.items():
  if by.get(nid,{{}}).get('type')!=typ:e.append(f'Gate7 workflow node {{nid}} != {{typ}}')
 if by.get(2400,{{}}).get('widgets_values')!=[True,True,'','']:e.append('Gate7 runtime defaults mismatch')
 if by.get(2410,{{}}).get('widgets_values')!=[False,False,'']:e.append('Gate7 visual approvals must default FALSE')
 links={{(x[1],x[2],x[3],x[4],x[5]) for x in w.get('links',[]) if isinstance(x,list) and len(x)>=6}}
 for req in ((2098,0,2400,0,'STRING'),(2300,3,2400,1,'STRING'),(2400,0,2401,0,'IMAGE'),(2400,2,2410,0,'STRING'),(2410,0,2411,0,'IMAGE')):
  if req not in links:e.append('missing Gate7 link '+repr(req))
 if any('Gate8' in str(t) or 'Gate 8' in str(t) for t in types):e.append('Gate8 node present')
 if len(list((root/'Payload/workflows').glob('*.json')))!=2:e.append('package must keep exactly two user workflows')
 verifier=(root/'Installer/verify_p10_dr9.py').read_text(encoding='utf-8-sig')
 for token in ['ConceptGhostP10Gate7Runtime','ConceptGhostP10Gate7VisualEvidencePack','GATE7_PREVIEW_R1_RUNTIME_VERIFY_PASS']:
  if token not in verifier:e.append('verifier missing '+token)
 for rel in ['Installer/install_gate7_preview_r1.ps1','Installer/verify_gate7_preview_r1.ps1']:
  if not (root/rel).is_file():e.append('missing '+rel)
 for p in node_root.glob('*.py'):
  try:py_compile.compile(str(p),doraise=True)
  except Exception as exc:e.append(f'compile {{p.name}}: {{exc}}')
 if e:
  print('\n'.join('[FAIL] '+x for x in e));return 1
 print('CONCEPTGHOST_GATE7_PREVIEW_R1_BUNDLE_PASS');return 0
if __name__=='__main__':raise SystemExit(main(sys.argv[1] if len(sys.argv)>1 else '.'))
'''
    wt(root / "Installer/test_gate7_preview_bundle.py", test)


def update_docs_and_release(root: Path, hotfix_commit: str) -> None:
    old_guide = root / "USER_GUIDE_DR9R_R15.md"
    guide = rt(old_guide)
    guide += """
    
## Gate 7 Preview r1

Workflow 02 now continues after Gate 6 into a protected Gate 7 candidate and a terminal visual-evidence branch.

New visible stages:
- STEP 5 Gate 7 registration/provenance/confidence/free-space/protected fusion;
- Gate 7 review image;
- Visual Evidence Pack with one preview + one comparison per Gate 7 subgate;
- confidence comparison: BLUE=HIGH / RED=LOW;
- same-camera drone BEFORE/AFTER GIF;
- G7.6 visual-evidence index.

The visual branch never feeds geometry back into the production chain. Both approval switches default FALSE. Gate 8 remains blocked.
"""
    wt(root / "USER_GUIDE_GATE7_PREVIEW_R1.md", guide)
    old_guide.unlink()

    payload_docs = root / "Payload/docs"
    payload_docs.mkdir(parents=True, exist_ok=True)
    summary = f"""# ConceptGhost Gate 7 Preview r1

Base package: {BASE_NAME}
Base SHA-256: {BASE_SHA256}
Gate 7 source commit: {P10_SOURCE_COMMIT}
Package build commit: {hotfix_commit or 'LOCAL_BUILD'}

This candidate adds G7.1→G7.6 runtime/visual-preview source to Workflow 02 while retaining the r15 Route Setup workflow unchanged.

Gate 8 is intentionally absent and blocked.
"""
    wt(payload_docs / "34_GATE7_PREVIEW_R1_PACKAGE.md", summary)

    features = [
        "GATE7_RUNTIME_G7_1_TO_G7_5",
        "TERMINAL_VISUAL_EVIDENCE_PACK",
        "CONFIDENCE_BLUE_HIGH_RED_LOW",
        "SAME_CAMERA_DRONE_BEFORE_AFTER_GIF",
        "G7_6_VISUAL_INDEX",
        "GATE8_BLOCKED_BY_DEFAULT",
    ]
    for name in ("RELEASE.json", "P10_DR9_RELEASE.json"):
        path = root / name
        data = json.loads(rt(path))
        data["schema"] = "ConceptGhost.P10Gate7PreviewRelease.v0.1"
        data["release"] = PREVIEW_NAME
        data["status"] = "CANDIDATE_READY_FOR_LATER_USER_RUNTIME_TEST"
        data["source_commit"] = P10_SOURCE_COMMIT
        data["package_hotfix_commit"] = hotfix_commit or "LOCAL_BUILD"
        data["base_package"] = {"release": BASE_NAME, "sha256": BASE_SHA256}
        data["gate7_preview"] = {
            "source_complete": True,
            "runtime_acceptance": "PENDING",
            "artist_visual_review": "PENDING",
            "gate8_promotion": "BLOCKED",
            "features": features,
        }
        data.setdefault("features", [])
        for feature in features:
            if feature not in data["features"]:
                data["features"].append(feature)
        data["runtime_acceptance_gates"] = [
            "03_INSTALL_ALL PASS",
            "04_VERIFY_INSTALL PASS",
            "r15 Route Setup UX accepted",
            "Workflow 02 Gate 7 runtime PASS",
            "confidence BEFORE/AFTER visually reviewed",
            "same-camera drone BEFORE/AFTER visually reviewed",
            "Gate 7 review visually approved",
            "P9 Maya unchanged",
        ]
        wt(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    validation = f"""ConceptGhost P10 Gate 7 Preview r1 validation

Package build status: PASS
Base r15 SHA-256: {BASE_SHA256}
Gate 7 source commit: {P10_SOURCE_COMMIT}
Two numbered user workflows only: PASS
Workflow 01 route editor inherited unchanged from r15: PASS
Workflow 02 Gate 7 runtime node: PASS
Terminal visual evidence branch: PASS
Confidence BLUE=HIGH / RED=LOW branch: PASS
Same-camera drone BEFORE/AFTER GIF branch: PASS
Visual approvals default FALSE: PASS
Gate 8 node present: NO
P9 authority changed: NO
User runtime acceptance: PENDING
Artist visual review: PENDING
"""
    wt(root / "P10_GATE7_PREVIEW_R1_VALIDATION.txt", validation)


def manifests(root: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.relative_to(root).as_posix() not in EXCLUDED:
            rows.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "sha256": sha256(path),
                    "size_bytes": path.stat().st_size,
                }
            )
    for name in ("BUNDLE_MANIFEST.json", "P10_DR9_BUNDLE_MANIFEST.json"):
        data = json.loads(rt(root / name))
        data["schema"] = "ConceptGhost.P10Gate7PreviewBundle.v0.1"
        data["release"] = PREVIEW_NAME
        data["status"] = "CANDIDATE_READY_FOR_LATER_USER_RUNTIME_TEST"
        data["source_commit"] = P10_SOURCE_COMMIT
        data["file_count_excluding_manifests_and_checksums"] = len(rows)
        data["gate7_preview"] = {
            "workflow02_extended": True,
            "visual_evidence_terminal": True,
            "gate8_default_blocked": True,
            "approvals_default_false": True,
        }
        data["files"] = rows
        wt(root / name, json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    checksum_lines = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            checksum_lines.append(f"{sha256(path)}  {path.relative_to(root).as_posix()}")
    wt(root / "SHA256SUMS.txt", "\n".join(checksum_lines) + "\n")


def validate(root: Path) -> list[str]:
    errors = []
    node_root = root / "Payload/custom_nodes/ConceptGhost_P10_Lab"
    manifest = json.loads(rt(root / "P10_DR9_CODE_MANIFEST.json"))
    if manifest.get("source_commit") != P10_SOURCE_COMMIT:
        errors.append("code manifest source commit mismatch")
    for item in manifest.get("files", []):
        path = node_root / item["path"]
        if not path.is_file():
            errors.append("P10 code missing " + item["path"])
        elif sha256(path) != item["sha256"]:
            errors.append("P10 code hash mismatch " + item["path"])
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
    fixed = (2026, 9, 24, 5, 40, 0)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            info = zipfile.ZipInfo(path.relative_to(root).as_posix(), date_time=fixed)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(
                info,
                path.read_bytes(),
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--p10-source-root", type=Path, required=True)
    parser.add_argument("--hotfix-commit", default=os.environ.get("GITHUB_SHA", ""))
    parser.add_argument("--keep-extracted", type=Path)
    args = parser.parse_args()

    actual = sha256(args.source)
    if actual != BASE_SHA256:
        raise SystemExit(f"wrong r15 SHA: {actual}")

    with tempfile.TemporaryDirectory(prefix="cg-g7-preview-r1-") as temp:
        root = Path(temp) / PREVIEW_NAME
        root.mkdir()
        with zipfile.ZipFile(args.source) as archive:
            archive.extractall(root)

        overlay_p10_source(root, args.p10_source_root)
        patch_production_workflow(root)
        update_code_manifest(root)
        patch_runtime_verifier(root)
        patch_entrypoints(root)
        patch_bundle_test(root)
        update_docs_and_release(root, args.hotfix_commit)

        for script in ("test_dr9_bundle.py", "test_gate7_preview_bundle.py"):
            result = subprocess.run(
                [os.sys.executable, str(root / "Installer" / script), str(root)],
                capture_output=True,
                text=True,
            )
            print(result.stdout.strip())
            if result.returncode:
                raise SystemExit(result.stdout + result.stderr)

        for cache in sorted(root.rglob("__pycache__"), key=lambda x: len(x.parts), reverse=True):
            shutil.rmtree(cache, ignore_errors=True)
        for pyc in root.rglob("*.pyc"):
            pyc.unlink(missing_ok=True)

        manifests(root)
        errors = validate(root)
        if errors:
            raise SystemExit("\n".join("[FAIL] " + item for item in errors))

        args.output.parent.mkdir(parents=True, exist_ok=True)
        zipdet(root, args.output)
        print("G7_PREVIEW_ZIP=" + str(args.output))
        print("G7_PREVIEW_BYTES=" + str(args.output.stat().st_size))
        print("G7_PREVIEW_SHA256=" + sha256(args.output))

        if args.keep_extracted:
            if args.keep_extracted.exists():
                shutil.rmtree(args.keep_extracted)
            shutil.copytree(root, args.keep_extracted)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
