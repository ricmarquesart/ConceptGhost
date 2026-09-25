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

R5="ConceptGhost_v1.54_P10_GATE7_PREVIEW_r5_GEOMETRIC_EVIDENCE_AUDIT_FIX"
R6F="ConceptGhost_v1.54_P10_GATE7_R6F11_ATLAS_DEPTH_CACHE_FIX"
BASE="cab56065d612e7e038bcb526307047d57134262471098e56d0225b74defee3dd"
EXCLUDED={"BUNDLE_MANIFEST.json","P10_DR9_BUNDLE_MANIFEST.json","SHA256SUMS.txt"}


def h(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""):
            digest.update(chunk)
    return digest.hexdigest()


def rt(path):
    return Path(path).read_text(encoding="utf-8-sig")


def wt(path,text,newline="\n"):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8",newline=newline) as stream:
        stream.write(text)


def replace_tree(root,old,new):
    for path in sorted(Path(root).rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".py",".ps1",".md",".json",".txt",".bat"}:
            continue
        try:
            text=rt(path)
        except UnicodeDecodeError:
            continue
        if old in text:
            wt(path,text.replace(old,new),"\r\n" if path.suffix.lower()==".bat" else "\n")


def patch_entrypoints(root):
    root=Path(root)
    old_install=root/"Installer/install_gate7_preview_r5_geometric_evidence_audit_fix.ps1"
    old_verify=root/"Installer/verify_gate7_preview_r5_geometric_evidence_audit_fix.ps1"
    if not old_install.is_file() or not old_verify.is_file():
        raise RuntimeError("r5 installer/verifier entrypoints missing")
    install=rt(old_install)
    verify=rt(old_verify)
    replacements=(
        ("Gate 7 Preview r5 + Geometric Evidence + Run-Local Audit","Gate 7 R6F11 + Atlas Depth Cache Fix"),
        (R5,R6F),
        ("before_gate7_preview_r5_geometric_evidence_audit_fix","before_gate7_r6f11_atlas_depth_cache_fix"),
        ("P10_GATE7_PREVIEW_R5_GEOMETRIC_EVIDENCE_AUDIT_FIX_READY_VERIFY.json","P10_GATE7_R6F11_ATLAS_DEPTH_CACHE_FIX_READY_VERIFY.json"),
        ("CONCEPTGHOST_P10_GATE7_PREVIEW_R5_GEOMETRIC_EVIDENCE_AUDIT_FIX_RUNTIME_VERIFY_PASS","CONCEPTGHOST_P10_GATE7_R6F11_ATLAS_DEPTH_CACHE_FIX_RUNTIME_VERIFY_PASS"),
    )
    for old,new in replacements:
        install=install.replace(old,new)
        verify=verify.replace(old,new)
    wt(root/"Installer/install_gate7_r6f11_atlas_depth_cache_fix.ps1",install)
    wt(root/"Installer/verify_gate7_r6f11_atlas_depth_cache_fix.ps1",verify)
    old_install.unlink()
    old_verify.unlink()

    install_bat="""@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo 03 - ConceptGhost P10 Gate 7 R6F11
echo     Route Editor Final + Geometric Evidence + Run-Local Audit
echo ============================================================
echo This is the first R6 target-PC validation package.
echo R6A-R6E were source/CI-only checkpoints.
echo Gate 8 remains blocked until this R6F runtime is accepted.
echo ============================================================
if not exist "%~dp0Installer\\install_gate7_r6f11_atlas_depth_cache_fix.ps1" (
  echo [FAIL] Required R6F installer entrypoint is missing.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Installer\\install_gate7_r6f11_atlas_depth_cache_fix.ps1"
if errorlevel 1 (
  echo [FAIL] R6F installation did not complete.
  pause
  exit /b 1
)
echo [PASS] R6F installed. Run 04_VERIFY_INSTALL.bat next.
pause
"""
    verify_bat="""@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo 04 - VERIFY ConceptGhost P10 Gate 7 R6F11
echo ============================================================
if not exist "%~dp0Installer\\verify_gate7_r6f11_atlas_depth_cache_fix.ps1" (
  echo [FAIL] Required R6F verifier entrypoint is missing.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Installer\\verify_gate7_r6f11_atlas_depth_cache_fix.ps1"
if errorlevel 1 (
  echo [FAIL] R6F installation verification failed.
  pause
  exit /b 1
)
echo [PASS] R6F installation verification completed.
pause
"""
    (root/"03_INSTALL_ALL.bat").write_bytes(install_bat.replace("\n","\r\n").encode("utf-8"))
    (root/"04_VERIFY_INSTALL.bat").write_bytes(verify_bat.replace("\n","\r\n").encode("utf-8"))


def patch_route_workflow(root):
    root=Path(root)
    path=root/"Payload/workflows/01_ConceptGhost_P10_ROUTE_SETUP.json"
    workflow=json.loads(rt(path))
    nodes=workflow.get("nodes",[])
    by={int(node["id"]):node for node in nodes}
    route=by.get(2099)
    commit=by.get(2110)
    if not route or route.get("type")!="ConceptGhostP10DroneRouteAuthoring":
        raise RuntimeError("Route Authoring node 2099 missing")
    if not commit or commit.get("type")!="ConceptGhostP10RouteCommit":
        raise RuntimeError("Route Commit node 2110 missing")

    route["title"]="01 · STEP 2 · R6 EDIT DRONES · POINT/MESH LOD + LIVE CAMERA AIM"
    route["size"]=[1180,1490]
    commit["pos"]=[12100,9600]

    instruction=by.get(2097)
    if instruction and instruction.get("widgets_values"):
        instruction["widgets_values"][0]=(
            "WORKFLOW 01 — R6F ROUTE SETUP\n\n"
            "RUN #1: resolva/carregue P9. Edite os drones no Route Editor.\n\n"
            "R6 EDITOR: Points Low/Medium/High ou Mesh Surface/Wireframe; ajuste Point Size; "
            "selecione P1/P2/P3 para Live Selected Camera View; use Aim deste ponto para orientação individual; "
            "SPIN_360 usa Yaw Start + Pitch; use o gimbal X/Right, Y/Up, Z/Forward para mover o pivot da Perspective.\n\n"
            "SELECTED CAMERA NODE: mission_index/waypoint_index são seletores manuais para a checagem dedicada de maior confiança.\n\n"
            "RUN #2: depois de editar, clique Run novamente para COMMITAR a rota. "
            "Abra Workflow 02 apenas quando production_ready=true."
        )

    preview_id=2111
    image_id=2112
    if any(node.get("type")=="ConceptGhostP10SelectedDroneCameraPreview" for node in nodes):
        raise RuntimeError("Selected camera preview node already exists unexpectedly")
    link_run=197
    link_route=198
    link_image=199
    preview_node={
        "id":preview_id,
        "type":"ConceptGhostP10SelectedDroneCameraPreview",
        "pos":[10900,11250],
        "size":[570,420],
        "flags":{},
        "order":2013,
        "mode":0,
        "inputs":[
            {"name":"run_dir","type":"STRING","link":link_run},
            {"name":"route_plan_json","type":"STRING","link":link_route},
            {"name":"mission_index","type":"INT","widget":{"name":"mission_index"},"link":None},
            {"name":"waypoint_index","type":"INT","widget":{"name":"waypoint_index"},"link":None},
            {"name":"preview_mode","type":"COMBO","widget":{"name":"preview_mode"},"link":None},
            {"name":"preview_width","type":"INT","widget":{"name":"preview_width"},"link":None},
        ],
        "outputs":[
            {"name":"selected_camera_preview","type":"IMAGE","links":[link_image],"slot_index":0},
            {"name":"diagnostics_json","type":"STRING","links":None,"slot_index":1},
        ],
        "properties":{"Node name for S&R":"ConceptGhostP10SelectedDroneCameraPreview"},
        "widgets_values":[0,0,"POINTS_HIGH",720],
        "title":"P10 · SELECTED DRONE CAMERA PREVIEW · MANUAL HIGH-CONFIDENCE CHECK",
    }
    preview_image={
        "id":image_id,
        "type":"PreviewImage",
        "pos":[11520,11250],
        "size":[900,650],
        "flags":{},
        "order":2014,
        "mode":0,
        "inputs":[{"name":"images","type":"IMAGE","link":link_image}],
        "outputs":[],
        "properties":{"Node name for S&R":"PreviewImage"},
        "widgets_values":[],
        "title":"P10 · SELECTED CAMERA · PREVIEW IMAGE",
    }
    nodes.extend([preview_node,preview_image])
    workflow.setdefault("links",[]).extend([
        [link_run,1015,0,preview_id,0,"STRING"],
        [link_route,2099,1,preview_id,1,"STRING"],
        [link_image,preview_id,0,image_id,0,"IMAGE"],
    ])
    workflow["last_node_id"]=max(int(workflow.get("last_node_id") or 0),image_id)
    workflow["last_link_id"]=max(int(workflow.get("last_link_id") or 0),link_image)
    extra=workflow.setdefault("extra",{}).setdefault("conceptghost",{})
    extra.update({
        "r6f_route_editor_final":True,
        "route_schema":"ConceptGhost.P10DroneRoutePlan.v0.3",
        "portable_route_preset_schema":"ConceptGhost.P10DroneRoutePreset.v0.2",
        "point_lods":["POINTS_LOW","POINTS_MEDIUM","POINTS_HIGH"],
        "mesh_modes":["MESH_SURFACE","MESH_WIREFRAME"],
        "selected_camera_live_preview":True,
        "selected_camera_refresh_node":True,
        "per_waypoint_camera_aim":True,
        "spin_pitch_yaw":True,
        "perspective_pivot_gimbal":True,
        "route_export":["JSON","CSV","TXT"],
    })
    wt(path,json.dumps(workflow,indent=2,ensure_ascii=False)+"\n")


def patch_production_workflow(root):
    path=Path(root)/"Payload/workflows/02_ConceptGhost_P10_PRODUCTION.json"
    workflow=json.loads(rt(path))
    extra=workflow.setdefault("extra",{}).setdefault("conceptghost",{})
    extra["gate7_preview_release"]="GATE7_R6F11_ATLAS_DEPTH_CACHE_FIX"
    extra["r6f_route_schema"]="ConceptGhost.P10DroneRoutePlan.v0.3"
    extra["r6f_user_validation_required"]=True
    wt(path,json.dumps(workflow,indent=2,ensure_ascii=False)+"\n")



def patch_moge_turing_runtime(root):
    root=Path(root)
    install_path=root/"Installer/install_moge3_runtime.ps1"
    install=rt(install_path)
    old_index='else { "https://download.pytorch.org/whl/cu130" }'
    if old_index not in install:
        raise RuntimeError("MoGe cu130 default index contract missing")
    install=install.replace(old_index,'else { "https://download.pytorch.org/whl/cu124" }')

    old_torch='Run -Exe $PythonExe -CommandArgs @("-m","pip","install","--no-warn-script-location","--index-url",$TorchIndex,"--extra-index-url","https://pypi.org/simple","torch>=2.4","torchvision>=0.19")'
    new_torch='''Run -Exe $PythonExe -CommandArgs @("-m","pip","install","--no-warn-script-location","--index-url",$TorchIndex,"--extra-index-url","https://pypi.org/simple","torch==2.6.0","torchvision==0.21.0")

Log "Pinning Triton Windows to the last Turing-supported minor (<3.3)..."
Run -Exe $PythonExe -CommandArgs @("-m","pip","install","--no-warn-script-location","--upgrade","triton-windows>=3.2,<3.3")'''
    if old_torch not in install:
        raise RuntimeError("MoGe Torch install contract missing")
    install=install.replace(old_torch,new_torch)

    old_moge='Run -Exe $PythonExe -CommandArgs @("-m","pip","install","--no-warn-script-location","-e",$Repo)'
    new_moge='''Run -Exe $PythonExe -CommandArgs @("-m","pip","install","--no-warn-script-location","-e",$Repo)
# Re-assert the target-hardware compatibility pair after transitive resolution.
Run -Exe $PythonExe -CommandArgs @("-m","pip","install","--no-warn-script-location","--upgrade","triton-windows>=3.2,<3.3")'''
    if old_moge not in install:
        raise RuntimeError("MoGe editable install contract missing")
    install=install.replace(old_moge,new_moge)

    old_verify='Run -Exe $PythonExe -CommandArgs @((Join-Path $WorkerDst "verify_moge3_runtime.py"))\n\nif (-not (Test-Path $Ready))'
    new_verify='''Run -Exe $PythonExe -CommandArgs @((Join-Path $WorkerDst "verify_moge3_runtime.py"))
Log "Running High Fidelity ViT-G + Turing compatibility gate..."
Run -Exe $PythonExe -CommandArgs @((Join-Path $WorkerDst "verify_vitg_runtime.py"))

if (-not (Test-Path $Ready))'''
    if old_verify not in install:
        raise RuntimeError("MoGe verifier tail contract missing")
    install=install.replace(old_verify,new_verify)
    old_env='''    $env:CONCEPTGHOST_MOGE_RUNTIME = $RuntimeRoot
    New-Item -ItemType Directory -Force -Path $env:HF_HOME,$env:HUGGINGFACE_HUB_CACHE,$env:TORCH_HOME | Out-Null
'''
    new_env='''    $env:CONCEPTGHOST_MOGE_RUNTIME = $RuntimeRoot
    $env:TRITON_CACHE_DIR = Join-Path $Cache "triton"
    New-Item -ItemType Directory -Force -Path $env:HF_HOME,$env:HUGGINGFACE_HUB_CACHE,$env:TORCH_HOME,$env:TRITON_CACHE_DIR | Out-Null
'''
    if old_env not in install:
        raise RuntimeError("MoGe private cache environment contract missing")
    install=install.replace(old_env,new_env)

    old_reuse='''    Set-RuntimeEnvironment
    Assert-RequiredModelCache
    $null = Run -Exe $PythonExe -CommandArgs @((Join-Path $WorkerDst "verify_moge3_runtime.py"))
'''
    new_reuse='''    Set-RuntimeEnvironment
    Assert-RequiredModelCache
    Log "Applying/verifying ConceptGhost FlexGEMM Triton 3.2 compatibility patch..."
    $null = Run -Exe $PythonExe -CommandArgs @((Join-Path $WorkerDst "patch_flexgemm_triton32.py"))
    $null = Run -Exe $PythonExe -CommandArgs @((Join-Path $WorkerDst "verify_moge3_runtime.py"))
'''
    if old_reuse not in install:
        raise RuntimeError("MoGe reuse verification contract missing")
    install=install.replace(old_reuse,new_reuse)

    old_after_triton='''# Re-assert the target-hardware compatibility pair after transitive resolution.
Run -Exe $PythonExe -CommandArgs @("-m","pip","install","--no-warn-script-location","--upgrade","triton-windows>=3.2,<3.3")

Log "Downloading/caching both production checkpoints (Low Resolution ViT-L + High Fidelity ViT-G)..."
'''
    new_after_triton='''# Re-assert the target-hardware compatibility pair after transitive resolution.
Run -Exe $PythonExe -CommandArgs @("-m","pip","install","--no-warn-script-location","--upgrade","triton-windows>=3.2,<3.3")

Log "Applying ConceptGhost compatibility bridge for pinned FlexGEMM on Triton 3.2..."
if (Test-Path $env:TRITON_CACHE_DIR) {
    Remove-Item (Join-Path $env:TRITON_CACHE_DIR "*") -Recurse -Force -ErrorAction SilentlyContinue
}
$null = Run -Exe $PythonExe -CommandArgs @((Join-Path $WorkerDst "patch_flexgemm_triton32.py"))

Log "Downloading/caching both production checkpoints (Low Resolution ViT-L + High Fidelity ViT-G)..."
'''
    if old_after_triton not in install:
        raise RuntimeError("MoGe post-install Triton reassertion contract missing")
    install=install.replace(old_after_triton,new_after_triton)

    wt(install_path,install)

    patch_script=root/"Runtime/MoGeRuntime/worker/patch_flexgemm_triton32.py"
    wt(patch_script,r'''from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import py_compile
import re
import sys
from pathlib import Path


REPORT_NAME = "FLEXGEMM_TRITON32_PATCH.json"
UPSTREAM_COMMIT = "b2fadb29d41846c7981ade6801ffc689fae119cf"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def emit(path: Path, report: dict, code: int) -> int:
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return code


def patch_hashmap_text(source: str) -> tuple[str, dict]:
    patched = source
    stats = {}

    key_tokens = (
        "keys_ptr.dtype.element_ty.itemsize",
        "(keys_ptr.dtype.element_ty.primitive_bitwidth // 8)",
    )
    key_replacements = 0
    for token in key_tokens:
        count = patched.count(token)
        if count:
            patched = patched.replace(token, "4")
            key_replacements += count
    stats["key_width_replacements"] = key_replacements

    query_tokens = (
        "query_vec.dtype.itemsize",
        "(query_vec.dtype.primitive_bitwidth // 8)",
    )
    query_replacements = 0
    for token in query_tokens:
        count = patched.count(token)
        if count:
            patched = patched.replace(token, "4")
            query_replacements += count
    stats["query_width_replacements"] = query_replacements

    legacy_lookup = "_vec_pack_little_endian_to_int32(query_vec)"
    safe_lookup = "query_vec.to(tl.int32)"
    lookup_count = patched.count(legacy_lookup)
    if lookup_count:
        patched = patched.replace(legacy_lookup, safe_lookup)
    stats["lookup_call_replacements"] = lookup_count

    d_expr = "D * 4 // 4"
    d_count = patched.count(d_expr)
    if d_count:
        patched = patched.replace(d_expr, "D")
    stats["d_expr_simplifications"] = d_count

    forbidden_active = (
        "keys_ptr.dtype.element_ty.itemsize",
        "keys_ptr.dtype.element_ty.primitive_bitwidth",
        "query_vec.dtype.itemsize",
        "query_vec.dtype.primitive_bitwidth",
        "_vec_pack_little_endian_to_int32(query_vec)",
    )
    remaining = [token for token in forbidden_active if token in patched]
    if remaining:
        raise RuntimeError("active Triton dtype introspection remains: " + ", ".join(remaining))

    if patched.count("D_32: tl.constexpr = D") != 3:
        raise RuntimeError(
            "expected exactly three active D_32=D assignments, found "
            + str(patched.count("D_32: tl.constexpr = D"))
        )
    if patched.count(safe_lookup) != 1:
        raise RuntimeError(
            "expected exactly one direct int32 lookup cast, found "
            + str(patched.count(safe_lookup))
        )

    required_host = (".view(torch.int32)", "D=D_32", "keys_i32", "queries_i32")
    missing_host = [token for token in required_host if token not in patched]
    if missing_host:
        raise RuntimeError("host int32 packing contract missing: " + ", ".join(missing_host))

    stats["safe_d_count"] = 3
    stats["safe_lookup_count"] = 1
    return patched, stats


def sanitize_triton32_annotations(source: str) -> tuple[str, dict]:
    """Remove Triton-language type annotations unsupported by Triton 3.2.

    Triton 3.2 infers runtime tensor/pointer types from actual JIT arguments.
    Explicit tl.pointer_type, tl.tensor and tl.const annotations are newer
    source-level conveniences that can fail while Triton 3.2 walks the AST.
    tl.constexpr is intentionally preserved because it controls specialization.
    """
    stats = {}
    patched = source

    parameter_patterns = {
        "pointer_optional": r":\s*tl\.pointer_type\s*\|\s*None",
        "pointer": r":\s*tl\.pointer_type\b",
        "tensor_optional": r":\s*tl\.tensor\s*\|\s*None",
        "tensor": r":\s*tl\.tensor\b",
        "const_optional": r":\s*tl\.const\s*\|\s*None",
        "const": r":\s*tl\.const\b",
    }
    for label, pattern in parameter_patterns.items():
        patched, count = re.subn(pattern, "", patched)
        stats[label] = count

    return_patterns = {
        "return_tensor": r"\s*->\s*tl\.tensor\b",
        "return_pointer": r"\s*->\s*tl\.pointer_type\b",
        "return_const": r"\s*->\s*tl\.const\b",
        "return_tuple_triton": r"\s*->\s*tuple\[[^\]\n]*tl\.[^\]\n]*\]",
    }
    for label, pattern in return_patterns.items():
        patched, count = re.subn(pattern, "", patched)
        stats[label] = count

    # Guardrail: preserve specialization authority.
    if source.count(": tl.constexpr") != patched.count(": tl.constexpr"):
        raise RuntimeError("annotation sanitizer changed tl.constexpr count")

    unsupported = re.findall(
        r":\s*tl\.(?:pointer_type|tensor|const)\b|"
        r"->\s*(?:tl\.(?:pointer_type|tensor|const)\b|tuple\[[^\]\n]*tl\.[^\]\n]*\])",
        patched,
    )
    if unsupported:
        raise RuntimeError("unsupported Triton 3.2 annotations remain: " + repr(unsupported[:10]))

    stats["total_removed"] = sum(stats.values())
    stats["constexpr_preserved"] = patched.count(": tl.constexpr")
    return patched, stats


def patch_reduce_or_compat(source: str) -> tuple[str, dict]:
    """Bridge tl.reduce_or (newer Triton) to generic tl.reduce available in Triton 3.2."""
    stats = {"reduce_or_replacements": 0, "helper_inserted": 0}
    call = "tl.reduce_or(gray_code, axis=0)"
    safe = "tl.reduce(gray_code, axis=0, combine_fn=_conceptghost_or_combine)"
    if call in source:
        source = source.replace(call, safe)
        stats["reduce_or_replacements"] = 1
    helper = "@triton.jit\ndef _conceptghost_or_combine(a, b):\n    return a | b\n\n"
    if safe in source and "def _conceptghost_or_combine(" not in source:
        marker = "__all__ = ["
        pos = source.find(marker)
        if pos < 0:
            raise RuntimeError("cannot locate insertion point for Triton 3.2 OR reducer helper")
        source = source[:pos] + helper + source[pos:]
        stats["helper_inserted"] = 1
    if "tl.reduce_or(" in source:
        raise RuntimeError("unsupported tl.reduce_or remains after compatibility patch")
    if safe in source and "def _conceptghost_or_combine(" not in source:
        raise RuntimeError("generic reduce OR helper missing")
    return source, stats


def self_test() -> int:
    fixture = (
        "@triton.jit\\n"
        "def helper(a: tl.pointer_type, b: tl.tensor, c: tl.tensor | None, "
        "d: tl.const, e: tl.const | None, maybe: tl.pointer_type | None, "
        "BLOCK: tl.constexpr) -> tuple[tl.tensor, tl.tensor]:\\n"
        "    return b, c\\n"
        "@triton.jit\\n"
        "def helper2(x: tl.tensor) -> tl.tensor:\\n"
        "    return x\\n"
    )
    patched, stats = sanitize_triton32_annotations(fixture)
    for token in ("tl.pointer_type", ": tl.tensor", ": tl.const,", ": tl.const |", "-> tl.tensor", "-> tuple["):
        if token in patched:
            raise RuntimeError("annotation sanitizer self-test left " + token)
    if patched.count(": tl.constexpr") != 1:
        raise RuntimeError("annotation sanitizer self-test lost constexpr")
    if stats["total_removed"] < 8:
        raise RuntimeError("annotation sanitizer self-test removed too few annotations")
    patched2, stats2 = sanitize_triton32_annotations(patched)
    if patched2 != patched or stats2["total_removed"] != 0:
        raise RuntimeError("annotation sanitizer is not idempotent")

    hashmap_fixture = (
        "def host(keys, queries, D_32):\\n"
        "    keys_i32 = keys.view(torch.int32)\\n"
        "    queries_i32 = queries.view(torch.int32)\\n"
        "    call(keys_i32, D=D_32)\\n"
        "    call(queries_i32, D=D_32)\\n"
        "def a():\\n"
        "    D_32: tl.constexpr = D * keys_ptr.dtype.element_ty.itemsize // 4\\n"
        "def b():\\n"
        "    D_32: tl.constexpr = D * keys_ptr.dtype.element_ty.itemsize // 4\\n"
        "def c():\\n"
        "    query_vec_32 = _vec_pack_little_endian_to_int32(query_vec)\\n"
        "    D_32: tl.constexpr = D * query_vec.dtype.itemsize // 4\\n"
    )
    for payload in (hashmap_fixture, hashmap_fixture.replace("\\n", "\\r\\n")):
        patched_hashmap, _ = patch_hashmap_text(payload)
        if patched_hashmap.count("D_32: tl.constexpr = D") != 3:
            raise RuntimeError("hashmap token self-test failed")

    reduce_fixture = (
        "import triton\n"
        "import triton.language as tl\n\n"
        "__all__ = []\n\n"
        "@triton.jit\n"
        "def kernel(gray_code):\n"
        "    reduced_code = tl.reduce_or(gray_code, axis=0)\n"
    )
    reduced, reduce_stats = patch_reduce_or_compat(reduce_fixture)
    if "tl.reduce_or(" in reduced or "combine_fn=_conceptghost_or_combine" not in reduced:
        raise RuntimeError("reduce_or compatibility self-test failed")
    if reduce_stats["reduce_or_replacements"] != 1 or reduce_stats["helper_inserted"] != 1:
        raise RuntimeError("reduce_or compatibility self-test stats mismatch")
    reduced2, reduce_stats2 = patch_reduce_or_compat(reduced)
    if reduced2 != reduced or reduce_stats2["reduce_or_replacements"] != 0:
        raise RuntimeError("reduce_or compatibility patch is not idempotent")

    print("CONCEPTGHOST_FLEXGEMM_TRITON32_R6F11_SELFTEST_PASS")
    return 0


def main() -> int:
    if "--self-test" in sys.argv[1:]:
        return self_test()

    runtime_root = Path(os.environ.get("CONCEPTGHOST_MOGE_RUNTIME") or Path(__file__).resolve().parents[1]).resolve()
    report_path = runtime_root / REPORT_NAME
    report = {
        "schema": "ConceptGhost.FlexGEMMTriton32Compatibility.v0.7",
        "status": "FAIL",
        "runtime_root": str(runtime_root),
        "scope": "CONCEPTGHOST_PRIVATE_MOGE_RUNTIME_ONLY",
        "upstream_flexgemm_commit": UPSTREAM_COMMIT,
        "policy": "R6F7_HASHMAP_TOKENPATCH_PLUS_SANITIZE_NON_CONSTEXPR_TRITON_ANNOTATIONS",
        "geometry_contract_changed": False,
        "model_weights_changed": False,
    }

    spec = importlib.util.find_spec("flex_gemm")
    if spec is None or not spec.submodule_search_locations:
        report["error"] = "flex_gemm package not found"
        return emit(report_path, report, 2)

    package_root = Path(next(iter(spec.submodule_search_locations))).resolve()
    triton_root = package_root / "kernels" / "triton"
    hashmap = triton_root / "hashmap.py"
    report["package_root"] = str(package_root)
    report["triton_root"] = str(triton_root)
    if not hashmap.is_file():
        report["error"] = "FlexGEMM Triton hashmap.py not found"
        return emit(report_path, report, 3)

    touched = []
    backups = []
    try:
        original_hashmap = hashmap.read_text(encoding="utf-8")
        patched_hashmap, hashmap_stats = patch_hashmap_text(original_hashmap)
        if patched_hashmap != original_hashmap:
            backup = hashmap.with_suffix(hashmap.suffix + ".conceptghost_pre_r6f9")
            if not backup.exists():
                backup.write_text(original_hashmap, encoding="utf-8")
            hashmap.write_text(patched_hashmap, encoding="utf-8")
            backups.append(str(backup))
            touched.append(str(hashmap))

        annotation_stats = {}
        reduce_or_stats = {}
        for path in sorted(triton_root.rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            patched, stats = sanitize_triton32_annotations(source)
            patched, reduce_stats = patch_reduce_or_compat(patched)
            annotation_stats[str(path.relative_to(package_root))] = stats
            reduce_or_stats[str(path.relative_to(package_root))] = reduce_stats
            if patched != source:
                backup = path.with_suffix(path.suffix + ".conceptghost_pre_r6f9")
                if not backup.exists():
                    backup.write_text(source, encoding="utf-8")
                path.write_text(patched, encoding="utf-8")
                backups.append(str(backup))
                touched.append(str(path))

        remaining = {}
        for path in sorted(triton_root.rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            hits = re.findall(
                r":\s*tl\.(?:pointer_type|tensor|const)\b|"
                r"->\s*(?:tl\.(?:pointer_type|tensor|const)\b|tuple\[[^\]\n]*tl\.[^\]\n]*\])",
                text,
            )
            if hits:
                remaining[str(path)] = hits[:10]
        if remaining:
            raise RuntimeError("unsupported Triton annotations remain: " + repr(remaining))

        for path in sorted(set(Path(item) for item in touched)):
            py_compile.compile(str(path), doraise=True)

        report["hashmap_stats"] = hashmap_stats
        report["annotation_stats"] = annotation_stats
        report["reduce_or_stats"] = reduce_or_stats
        report["reduce_or_total_replacements"] = sum(
            stats["reduce_or_replacements"] for stats in reduce_or_stats.values()
        )
        report["annotation_total_removed"] = sum(
            stats["total_removed"] for stats in annotation_stats.values()
        )
        report["touched_files"] = sorted(set(touched))
        report["backups"] = sorted(set(backups))
        report["triton32_signature_fix"] = {
            "removed_runtime_annotations": ["tl.pointer_type", "tl.tensor", "tl.const"],
            "preserved_specialization_annotation": "tl.constexpr",
            "expected_failures_removed": [
                "KeyError('ier_type')",
                "ValueError('_builder argument must be provided outside of JIT functions')",
                "AttributeError(module triton.language has no attribute reduce_or)",
            ],
            "reduce_or_bridge": "tl.reduce(..., combine_fn=_conceptghost_or_combine)",
        }
        report["status"] = "PASS"
        return emit(report_path, report, 0)
    except Exception as exc:
        report["error"] = repr(exc)
        return emit(report_path, report, 4)


if __name__ == "__main__":
    raise SystemExit(main())
''')

    verify_path=root/"Runtime/MoGeRuntime/worker/verify_vitg_runtime.py"
    verify=rt(verify_path)
    verify=verify.replace("import time\nfrom pathlib","import time\nimport importlib.metadata as importlib_metadata\nfrom pathlib")
    verify=verify.replace(
        '"schema": "ConceptGhost.MoGe3ViTGVerification.v0.30",',
        '"schema": "ConceptGhost.MoGe3ViTGVerification.v0.31-turing",',
    )
    verify=verify.replace(
        '"note": "Small smoke test verifies model loading and CUDA compatibility; production High Fidelity uses resolution_level=9/refine_steps=7.",',
        '"note": "Small smoke test plus deterministic Turing compatibility gate; production High Fidelity remains resolution_level=9/refine_steps=7.",',
    )
    old_device='''    device = torch.device("cuda")
    report["gpu"] = torch.cuda.get_device_name(device)
    report["total_vram_bytes"] = int(torch.cuda.get_device_properties(device).total_memory)
'''
    new_device='''    device = torch.device("cuda")
    report["gpu"] = torch.cuda.get_device_name(device)
    report["compute_capability"] = list(torch.cuda.get_device_capability(device))
    report["total_vram_bytes"] = int(torch.cuda.get_device_properties(device).total_memory)
    report["torch_version"] = torch.__version__
    report["cuda_runtime"] = torch.version.cuda
    try:
        report["triton_distribution"] = "triton-windows"
        report["triton_version"] = importlib_metadata.version("triton-windows")
    except importlib_metadata.PackageNotFoundError:
        try:
            import triton
            report["triton_distribution"] = "triton"
            report["triton_version"] = getattr(triton, "__version__", "unknown")
        except Exception as exc:
            report.update(status="FAIL", reason=f"Triton unavailable: {exc!r}")
            print(json.dumps(report, indent=2))
            return 5

    cc = tuple(report["compute_capability"])
    def _minor(text):
        import re
        match=re.match(r"^(\d+)\.(\d+)",str(text))
        return (int(match.group(1)),int(match.group(2))) if match else None
    torch_minor=_minor(report["torch_version"])
    triton_minor=_minor(report["triton_version"])
    report["turing_compatibility_required"] = cc < (8,0)
    if cc < (8,0):
        if torch_minor != (2,6) or triton_minor != (3,2):
            report.update(
                status="FAIL",
                reason=(
                    "Turing/RTX20 compatibility requires the private ConceptGhost runtime "
                    f"to use torch 2.6.x + Triton 3.2.x; got torch={report['torch_version']} "
                    f"triton={report['triton_version']} cc={cc[0]}.{cc[1]}"
                ),
            )
            print(json.dumps(report,indent=2))
            return 6
'''
    if old_device not in verify:
        raise RuntimeError("ViT-G verifier device block missing")
    verify=verify.replace(old_device,new_device)
    verify=verify.replace(
        'report["production_capacity_note"] = "11 GB-class GPUs may still OOM at ViT-G resolution_level=9/refine_steps=7; ConceptGhost never silently downgrades High Fidelity."',
        'report["production_capacity_note"] = "Compatibility is verified; full resolution_level=9/refine_steps=7 remains a separate runtime workload and is never silently downgraded."',
    )
    verify=verify.replace(
        '''    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 3
''',
        '''    report_path = runtime_root / "VITG_READY.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 3
''',
    )
    wt(verify_path,verify)

    worker_path=root/"Runtime/MoGeRuntime/worker/moge_worker.py"
    worker=rt(worker_path)
    worker=worker.replace(
        "import threading\nfrom pathlib",
        "import threading\nimport importlib.metadata as importlib_metadata\nimport re\nfrom pathlib",
    )
    worker=worker.replace(
        '''    torch_cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(hf))''',
        '''    torch_cache.mkdir(parents=True, exist_ok=True)
    triton_cache = cache / "triton"
    triton_cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("TRITON_CACHE_DIR", str(triton_cache))
    os.environ.setdefault("HF_HOME", str(hf))''',
    )
    old_worker='''    if not torch.cuda.is_available():
        raise RuntimeError("MoGe-3 ConceptGhost runtime requires CUDA for the target production path")
    device = torch.device("cuda")

    reporter.set("MODEL_LOAD_START", model_name)
'''
    new_worker='''    if not torch.cuda.is_available():
        raise RuntimeError("MoGe-3 ConceptGhost runtime requires CUDA for the target production path")
    device = torch.device("cuda")
    cc=tuple(torch.cuda.get_device_capability(device))
    try:
        triton_version=importlib_metadata.version("triton-windows")
    except importlib_metadata.PackageNotFoundError:
        try:
            import triton
            triton_version=getattr(triton,"__version__","unknown")
        except Exception:
            triton_version="missing"
    reporter.set(
        "RUNTIME_CAPABILITY",
        f"gpu={torch.cuda.get_device_name(device)}; cc={cc[0]}.{cc[1]}; "
        f"torch={torch.__version__}; cuda={torch.version.cuda}; triton={triton_version}",
    )
    def _minor(text):
        match=re.match(r"^(\d+)\.(\d+)",str(text))
        return (int(match.group(1)),int(match.group(2))) if match else None
    if cc < (8,0):
        if _minor(torch.__version__) != (2,6) or _minor(triton_version) != (3,2):
            raise RuntimeError(
                "ConceptGhost MoGe-3 Turing runtime incompatibility: RTX 20xx/sm75 requires "
                "the private runtime torch 2.6.x + Triton 3.2.x. Re-run the R6F11 installer. "
                f"Detected torch={torch.__version__}, triton={triton_version}, cc={cc[0]}.{cc[1]}."
            )

    reporter.set("MODEL_LOAD_START", model_name)
'''
    if old_worker not in worker:
        raise RuntimeError("MoGe worker CUDA block missing")
    worker=worker.replace(old_worker,new_worker)
    wt(worker_path,worker)

    lock_path=root/"Runtime/MoGeRuntime/SOURCE_LOCK.json"
    lock=json.loads(rt(lock_path))
    lock["runtime_compatibility"]={
        "target_gpu_arch":"Turing sm75 / RTX 20xx",
        "python":"3.11.9 embedded",
        "torch":"2.6.x",
        "torchvision":"0.21.x",
        "cuda_wheel":"cu124",
        "triton_windows":"3.2.x (<3.3)",
        "flexgemm_triton32_bridge":"remove Triton JIT dtype introspection; preserve FlexGEMM host int32 packing contract",
        "geometry_contract_changed":False,
    }
    lock["release"]="ConceptGhost v1.54 R6F11 MoGe3 Turing Runtime Fix"
    wt(lock_path,json.dumps(lock,indent=2,ensure_ascii=False)+"\n")

    for name in ("RELEASE.json","P10_DR9_RELEASE.json"):
        path=root/name
        data=json.loads(rt(path))
        data["moge3_turing_runtime_fix"]={
            "private_runtime_only":True,
            "torch":"2.6.0",
            "torchvision":"0.21.0",
            "cuda_index":"cu124",
            "triton_windows":"3.2.x (<3.3)",
            "flexgemm_triton32_bridge":True,
            "high_fidelity_model":"Ruicheng/moge-3-vitg",
            "resolution_level":9,
            "refine_steps":7,
            "geometry_contract_changed":False,
            "target_pc_runtime_acceptance":"PENDING",
        }
        wt(path,json.dumps(data,indent=2,ensure_ascii=False)+"\n")

    guide=root/"USER_GUIDE_GATE7_R6F11_ATLAS_DEPTH_CACHE_FIX.md"
    wt(guide,rt(guide)+"""
## R6F11 MoGe-3 Turing runtime correction
This package repairs only the isolated ConceptGhost MoGe runtime compatibility path for RTX 20xx/Turing.
It pins the private runtime to PyTorch 2.6 / CUDA 12.4 wheels and Triton Windows 3.2.x, preserving ViT-G, resolution_level=9 and refine_steps=7.
No P9 geometry algorithm/profile parameter was reduced or silently downgraded. Existing accepted P9 outputs are not rewritten.
The worker reports GPU compute capability, Torch/CUDA/Triton versions before inference and fails fast on an incompatible Turing matrix instead of waiting for the 1500-second hard timeout.
R6F11 applies a bounded compatibility bridge to the ConceptGhost-private FlexGEMM hashmap kernels. FlexGEMM's Python wrappers already serialize keys and queries into padded torch.int32 tensors and pass D as the number of int32 words, so R6F11 removes Triton-JIT dtype-width introspection from those kernels and consumes that existing host-side packing contract directly. Model weights, resolution, refine steps and geometry authority are unchanged.
""")

    validation=root/"P10_GATE7_R6F11_ATLAS_DEPTH_CACHE_FIX_VALIDATION.txt"
    wt(validation,rt(validation)+"""
R6F11 MoGe-3 Turing runtime compatibility:
- target: RTX 20xx / sm75
- private Torch: 2.6.0
- private torchvision: 0.21.0
- private CUDA wheel index: cu124
- private Triton Windows: >=3.2,<3.3
- ViT-G / resolution 9 / refine 7 geometry contract changed: NO
- worker capability telemetry + fail-fast: YES
- FlexGEMM/Triton 3.2 host-int32-pack compatibility bridge: INCLUDED
- private Triton cache isolated and cleared before smoke verification: YES
- user runtime acceptance: PENDING
""")

    test=root/"Installer/test_r6f11_atlas_depth_cache_fix.py"
    wt(test,r'''from pathlib import Path
import json,subprocess,sys

def main(root):
    root=Path(root).resolve(); errors=[]
    install=(root/"Installer/install_moge3_runtime.ps1").read_text(encoding="utf-8-sig")
    for token in ("cu124","torch==2.6.0","torchvision==0.21.0","triton-windows>=3.2,<3.3","verify_vitg_runtime.py","patch_flexgemm_triton32.py","TRITON_CACHE_DIR"):
        if token not in install: errors.append("installer missing "+token)
    patch_path=root/"Runtime/MoGeRuntime/worker/patch_flexgemm_triton32.py"
    patch=patch_path.read_text(encoding="utf-8-sig")
    for token in ("SANITIZE_NON_CONSTEXPR_TRITON_ANNOTATIONS","sanitize_triton32_annotations","patch_reduce_or_compat","_conceptghost_or_combine","combine_fn=_conceptghost_or_combine","--self-test"):
        if token not in patch: errors.append("R6F11 annotation sanitizer missing "+token)
    try:
        compile(patch, str(patch_path), "exec")
    except SyntaxError as exc:
        errors.append("R6F11 bridge syntax error "+repr(exc))
    probe=subprocess.run([sys.executable,str(patch_path),"--self-test"],capture_output=True,text=True)
    if probe.returncode != 0 or "CONCEPTGHOST_FLEXGEMM_TRITON32_R6F11_SELFTEST_PASS" not in probe.stdout:
        errors.append("R6F11 bridge self-test failed: "+probe.stdout+" "+probe.stderr)
    lock=json.loads((root/"Runtime/MoGeRuntime/SOURCE_LOCK.json").read_text(encoding="utf-8-sig"))
    if lock.get("high_fidelity_refine_steps") != 7 or lock.get("high_fidelity_resolution_level") != 9:
        errors.append("High Fidelity geometry contract changed")
    contracts=(root/"Payload/custom_nodes/ConceptGhost_Stage68/conceptghost_contracts.py").read_text(encoding="utf-8-sig")
    if '"refine_steps": 7' not in contracts or '"resolution_level": 9' not in contracts or "Ruicheng/moge-3-vitg" not in contracts:
        errors.append("Stage68 High Fidelity profile changed unexpectedly")
    if errors:
        print("\\n".join("[FAIL] "+item for item in errors)); return 1
    print("CONCEPTGHOST_R6F11_ATLAS_DEPTH_CACHE_FIX_PASS"); return 0

if __name__=="__main__":
    raise SystemExit(main(sys.argv[1]))
''')

def patch_contracts(root,source_commit,package_commit):
    root=Path(root)
    p=root/"Installer/verify_p10_dr9.py"
    wt(p,rt(p).replace(
        "CONCEPTGHOST_P10_GATE7_PREVIEW_R5_GEOMETRIC_EVIDENCE_AUDIT_FIX_RUNTIME_VERIFY_PASS",
        "CONCEPTGHOST_P10_GATE7_R6F11_ATLAS_DEPTH_CACHE_FIX_RUNTIME_VERIFY_PASS",
    ))

    p=root/"Installer/test_gate7_preview_bundle.py"
    text=rt(p).replace(
        "GATE7_PREVIEW_R5_GEOMETRIC_EVIDENCE_AUDIT_FIX_RUNTIME_VERIFY_PASS",
        "GATE7_R6F11_ATLAS_DEPTH_CACHE_FIX_RUNTIME_VERIFY_PASS",
    ).replace(
        "Installer/install_gate7_preview_r5_geometric_evidence_audit_fix.ps1",
        "Installer/install_gate7_r6f11_atlas_depth_cache_fix.ps1",
    ).replace(
        "Installer/verify_gate7_preview_r5_geometric_evidence_audit_fix.ps1",
        "Installer/verify_gate7_r6f11_atlas_depth_cache_fix.ps1",
    )
    wt(p,text)

    p=root/"Installer/test_dr9_bundle.py"
    wt(p,rt(p).replace(
        "USER_GUIDE_GATE7_PREVIEW_R5_GEOMETRIC_EVIDENCE_AUDIT_FIX.md",
        "USER_GUIDE_GATE7_R6F11_ATLAS_DEPTH_CACHE_FIX.md",
    ))

    old_guide=root/"USER_GUIDE_GATE7_PREVIEW_R5_GEOMETRIC_EVIDENCE_AUDIT_FIX.md"
    if not old_guide.is_file():
        raise RuntimeError("r5 user guide missing")
    guide=rt(old_guide).replace(
        "Gate 7 Preview r5 + Geometric Evidence + Run-Local Audit",
        "Gate 7 R6F11 + Atlas Depth Cache Fix",
    )
    guide += """
## R6F Route Editor final validation
R6A-R6E were developed and CI-validated without target-PC acceptance. R6F is the first runtime validation package.

Route Editor includes Points Low/Medium/High, Mesh Surface/Wireframe, Point Size, live Selected Camera View, selected-camera frustum, explicit per-waypoint camera aim, SPIN_360 pitch/yaw-start controls, Perspective RUF pivot/gimbal, conventional horizontal orbit direction, and JSON + CSV/TXT route export.

The dedicated node P10 · Selected Drone Camera Preview is present in Workflow 01 for a higher-confidence manual check. Its mission_index and waypoint_index widgets select the control camera to inspect.

Route authority schema is v0.3. Legacy v0.1/v0.2 route bindings remain readable. Portable preset schema is v0.2 and v0.1 remains import-compatible.

Gate 8 remains blocked until this R6F target-PC run is accepted.
"""
    wt(root/"USER_GUIDE_GATE7_R6F11_ATLAS_DEPTH_CACHE_FIX.md",guide)
    old_guide.unlink()

    wt(root/"Payload/docs/40_R6F_ROUTE_EDITOR_FINAL.md",f"""# ConceptGhost P10 Gate 7 R6F11 — Route Editor Final

Source commit: {source_commit}
Package commit: {package_commit or 'LOCAL_BUILD'}

## Included R6 gates
- R6A Point/Mesh display LOD and Point Size.
- R6B Live Selected Camera View + frustum + dedicated selected-camera preview node.
- R6C Per-waypoint aim interpolation + SPIN_360 pitch/yaw start.
- R6D Perspective pivot/gimbal + conventional horizontal orbit.
- R6E portable preset v0.2 + authority JSON and readable CSV/TXT export.
- R6F aggregate package/regression gate.

P9 remains immutable. Gate 8 remains blocked until user runtime acceptance.
""")

    code_manifest=root/"P10_DR9_CODE_MANIFEST.json"
    data=json.loads(rt(code_manifest))
    data.update({
        "schema":"ConceptGhost.P10Gate7R6F11CodeManifest.v0.1",
        "release":R6F,
        "source_commit":source_commit,
    })
    wt(code_manifest,json.dumps(data,indent=2,ensure_ascii=False)+"\n")

    for name in ("RELEASE.json","P10_DR9_RELEASE.json"):
        p=root/name
        data=json.loads(rt(p))
        data.update({
            "schema":"ConceptGhost.P10Gate7R6F11Release.v0.1",
            "release":R6F,
            "source_commit":source_commit,
            "package_hotfix_commit":package_commit or "LOCAL_BUILD",
        })
        data["r6f"]={
            "r6a_point_mesh_lod":True,
            "r6b_selected_camera_preview":True,
            "r6c_per_waypoint_camera_pose":True,
            "r6c_spin_pitch_yaw":True,
            "r6d_pivot_gimbal":True,
            "r6d_conventional_orbit":True,
            "r6e_route_schema":"ConceptGhost.P10DroneRoutePlan.v0.3",
            "r6e_portable_preset_schema":"ConceptGhost.P10DroneRoutePreset.v0.2",
            "r6e_readable_exports":["CSV","TXT"],
            "user_runtime_acceptance":"PENDING",
            "gate8_present":False,
        }
        wt(p,json.dumps(data,indent=2,ensure_ascii=False)+"\n")

    old_validation=root/"P10_GATE7_PREVIEW_R5_GEOMETRIC_EVIDENCE_AUDIT_FIX_VALIDATION.txt"
    if old_validation.exists():
        old_validation.unlink()
    wt(root/"P10_GATE7_R6F11_ATLAS_DEPTH_CACHE_FIX_VALIDATION.txt",f"""ConceptGhost P10 Gate 7 R6F11 Route Editor Final

Base r15 SHA-256: {BASE}
Source commit: {source_commit}
R6A point/mesh LOD: PASS SOURCE/CI
R6B selected camera live + node: PASS SOURCE/CI
R6C per-waypoint aim + 360 pitch/yaw: PASS SOURCE/CI
R6D pivot/gimbal + orbit correction: PASS SOURCE/CI
R6E JSON + CSV/TXT route export: PASS SOURCE/CI
Gate 7 geometric consistency evidence fix: INCLUDED
Run-local automatic audit fix: INCLUDED
Accepted P9 run mutated: NO
Gate 8 node present: NO
User runtime acceptance: PENDING — THIS R6F PACKAGE IS THE VALIDATION POINT
""")

    test="""from pathlib import Path
import json,sys

def main(root):
 root=Path(root).resolve(); errors=[]; n=root/'Payload/custom_nodes/ConceptGhost_P10_Lab'
 required={
  'drone_route_preview.py':('P10RoutePreviewGeometry.v0.2','POINTS_HIGH','DISPLAY_ONLY_P9_PRIMARYMESH_LOD'),
  'route_authoring_node.py':('selected_camera_live_preview','perspective_pivot_gimbal','camera_preview_contract'),
  'selected_camera_preview.py':('ConceptGhostP10SelectedDroneCameraPreview','preview_authority','P9_ACCEPTED_PRIMARYMESH'),
  'drone_route_plan.py':('P10DroneRoutePlan.v0.3','look_direction','spin_pitch_deg','spin_yaw_start_deg','_legacy_v02_route_hash'),
 }
 for name,tokens in required.items():
  p=n/name
  if not p.is_file(): errors.append('missing source '+name); continue
  source=p.read_text(encoding='utf-8')
  for token in tokens:
   if token not in source: errors.append(name+' missing '+token)
 js=(n/'web/js/drone_route_editor.js').read_text(encoding='utf-8')
 for token in ('Points Low','Mesh Surface','Selected Camera View','Aim deste ponto','Reset Pivot','Pivot to Selected Camera','state.orbitYaw -= dx * 0.008','P10DroneRoutePreset.v0.2','readableRouteExports'):
  if token not in js: errors.append('frontend missing '+token)
 w=json.loads((root/'Payload/workflows/01_ConceptGhost_P10_ROUTE_SETUP.json').read_text(encoding='utf-8-sig')); by={int(x['id']):x for x in w.get('nodes',[])}
 if by.get(2111,{}).get('type')!='ConceptGhostP10SelectedDroneCameraPreview': errors.append('workflow selected-camera node missing')
 if by.get(2112,{}).get('type')!='PreviewImage': errors.append('workflow selected-camera PreviewImage missing')
 links={int(x[0]):x for x in w.get('links',[])}
 for lid in (197,198,199):
  if lid not in links: errors.append('workflow link missing '+str(lid))
 if any('Gate8' in str(x.get('type')) or 'Gate 8' in str(x.get('title')) for x in w.get('nodes',[])): errors.append('Gate 8 leaked into Route Setup')
 p=json.loads((root/'Payload/workflows/02_ConceptGhost_P10_PRODUCTION.json').read_text(encoding='utf-8-sig'))
 if any('Gate8' in str(x.get('type')) or 'Gate 8' in str(x.get('title')) for x in p.get('nodes',[])): errors.append('Gate 8 leaked into Production')
 if errors:
  print('\\n'.join('[FAIL] '+x for x in errors)); return 1
 print('CONCEPTGHOST_GATE7_R6F11_ATLAS_DEPTH_CACHE_FIX_PASS'); return 0

if __name__=='__main__': raise SystemExit(main(sys.argv[1]))
"""
    wt(root/"Installer/test_gate7_r6f_route_editor_final.py",test)


def rebuild(root,source_commit):
    root=Path(root)
    rows=[]
    for path in sorted(root.rglob("*")):
        rel=path.relative_to(root).as_posix()
        if path.is_file() and rel not in EXCLUDED:
            rows.append({"path":rel,"sha256":h(path),"size_bytes":path.stat().st_size})
    for name in ("BUNDLE_MANIFEST.json","P10_DR9_BUNDLE_MANIFEST.json"):
        path=root/name
        data=json.loads(rt(path))
        data.update({
            "schema":"ConceptGhost.P10Gate7R6F11Bundle.v0.1",
            "release":R6F,
            "source_commit":source_commit,
            "file_count_excluding_manifests_and_checksums":len(rows),
            "r6f":{
                "route_editor_final":True,
                "point_mesh_lod":True,
                "selected_camera_preview":True,
                "per_waypoint_camera_pose":True,
                "spin_pitch_yaw":True,
                "pivot_gimbal":True,
                "route_export_json_csv_txt":True,
                "gate7_geometric_evidence_fix":True,
                "run_local_audit_fix":True,
                "gate8_present":False,
                "user_runtime_acceptance":"PENDING",
            },
            "files":rows,
        })
        wt(path,json.dumps(data,indent=2,ensure_ascii=False)+"\n")
    lines=[
        f"{h(path)}  {path.relative_to(root).as_posix()}"
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name!="SHA256SUMS.txt"
    ]
    wt(root/"SHA256SUMS.txt","\n".join(lines)+"\n")


def validate(root,source_commit):
    root=Path(root)
    errors=[]
    cm=json.loads(rt(root/"P10_DR9_CODE_MANIFEST.json"))
    node_root=root/"Payload/custom_nodes/ConceptGhost_P10_Lab"
    if cm.get("source_commit")!=source_commit:
        errors.append("code manifest source mismatch")
    for item in cm.get("files",[]):
        path=node_root/item["path"]
        if not path.is_file() or h(path)!=item["sha256"]:
            errors.append("P10 code mismatch "+item["path"])
    for path in list(node_root.glob("*.py"))+list((root/"Installer").glob("*.py")):
        try:
            compile(rt(path),str(path),"exec")
        except Exception as error:
            errors.append(f"compile {path.name}: {error}")
    for raw in rt(root/"SHA256SUMS.txt").splitlines():
        digest,rel=raw.split("  ",1)
        path=root/rel
        if not path.is_file() or h(path)!=digest:
            errors.append("sha mismatch "+rel)
    if len(list((root/"Payload/workflows").glob("*.json")))!=2:
        errors.append("not exactly two workflows")
    return errors


def zipdet(root,out):
    root=Path(root)
    out=Path(out)
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            info=zipfile.ZipInfo(path.relative_to(root).as_posix(),date_time=(2026,9,24,20,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o644<<16
            archive.writestr(info,path.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--p10-source-root",type=Path,required=True)
    parser.add_argument("--source-commit",default=os.environ.get("GITHUB_SHA",""))
    parser.add_argument("--package-commit",default=os.environ.get("GITHUB_SHA",""))
    parser.add_argument("--keep-extracted",type=Path)
    args=parser.parse_args()

    if h(args.source)!=BASE:
        raise SystemExit("wrong frozen r15 base SHA")
    if not re.fullmatch(r"[0-9a-f]{40}",args.source_commit or ""):
        raise SystemExit("source commit must be 40-char SHA")

    r5_builder=Path(__file__).resolve().parents[1]/"gate7_preview_r5_geometric_evidence_audit_fix"/"build_gate7_preview_r5_from_r15.py"
    with tempfile.TemporaryDirectory(prefix="cg-r6f-") as temp:
        temp=Path(temp)
        r5_zip=temp/(R5+".zip")
        root=temp/R6F
        result=subprocess.run([
            sys.executable,str(r5_builder),
            "--source",str(args.source),
            "--output",str(r5_zip),
            "--p10-source-root",str(args.p10_source_root),
            "--source-commit",args.source_commit,
            "--package-commit",args.package_commit,
            "--keep-extracted",str(root),
        ],capture_output=True,text=True)
        print(result.stdout)
        if result.returncode:
            raise SystemExit(result.stdout+result.stderr)

        patch_entrypoints(root)
        replace_tree(root,R5,R6F)
        patch_route_workflow(root)
        patch_production_workflow(root)
        patch_contracts(root,args.source_commit,args.package_commit)
        patch_moge_turing_runtime(root)

        tests=(
            "test_dr9_bundle.py",
            "test_gate7_preview_bundle.py",
            "test_run_audit_bundle_package.py",
            "test_gate7_r3_route_ux_colmap_fix.py",
            "test_gate7_r5_geometric_evidence_audit_fix.py",
            "test_gate7_r6f_route_editor_final.py",
            "test_r6f11_atlas_depth_cache_fix.py",
        )
        for name in tests:
            result=subprocess.run([sys.executable,str(root/"Installer"/name),str(root)],capture_output=True,text=True)
            print(result.stdout.strip())
            if result.returncode:
                raise SystemExit(result.stdout+result.stderr)

        js=root/"Payload/custom_nodes/ConceptGhost_P10_Lab/web/js/drone_route_editor.js"
        if shutil.which("node"):
            result=subprocess.run(["node","--check",str(js)],capture_output=True,text=True)
            if result.returncode:
                raise SystemExit(result.stdout+result.stderr)

        for cache in sorted(root.rglob("__pycache__"),key=lambda item:len(item.parts),reverse=True):
            shutil.rmtree(cache,ignore_errors=True)
        rebuild(root,args.source_commit)
        errors=validate(root,args.source_commit)
        if errors:
            raise SystemExit("\n".join("[FAIL] "+item for item in errors))

        args.output.parent.mkdir(parents=True,exist_ok=True)
        zipdet(root,args.output)
        print("R6F_ZIP="+str(args.output))
        print("R6F_BYTES="+str(args.output.stat().st_size))
        print("R6F_SHA256="+h(args.output))
        if args.keep_extracted:
            if args.keep_extracted.exists():
                shutil.rmtree(args.keep_extracted)
            shutil.copytree(root,args.keep_extracted)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
