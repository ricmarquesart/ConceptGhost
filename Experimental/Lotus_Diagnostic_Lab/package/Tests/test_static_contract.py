import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_workflow_name_unversioned():
    assert (ROOT/'Payload/workflows/Lotus_Depth_Diagnostic.json').is_file()

def test_five_required_groups_and_notes():
    wf=json.loads((ROOT/'Payload/workflows/Lotus_Depth_Diagnostic.json').read_text(encoding='utf-8'))
    assert [g['title'] for g in wf['groups']] == ['Lotus Input','Lotus Depth Inference','Lotus Depth Diagnostics','Lotus 3D Preview','Lotus Output Bundle']
    notes=[n['widgets_values'][0].lower() for n in wf['nodes'] if n['type']=='Note']
    assert len(notes)==5
    required=['purpose','inputs','what it does','outputs','authority','geometry impact','default state','failure/fallback','temp/retention','next stage']
    for note in notes:
        for heading in required:
            assert heading in note

def test_bridge_has_no_lotus_ml_imports():
    s=(ROOT/'Payload/custom_nodes/ConceptGhost_Lotus_Diagnostic/nodes.py').read_text(encoding='utf-8').lower()
    for forbidden in ['import diffusers','import transformers','from diffusers','from transformers','pip install']:
        assert forbidden not in s

def test_installer_never_targets_shared_model_or_host_python_for_pip():
    s=(ROOT/'Installer/install_lotus_diagnostic.ps1').read_text(encoding='utf-8')
    assert "ConceptGhost-LotusDiagnostic" in s
    assert "ComfyUI-Shared\\models" in s
    assert "Join-Path $ComfyUIRoot 'models'" in s
    pip_exec=[line.strip() for line in s.splitlines() if '-m pip' in line.lower()]
    assert pip_exec
    assert all('$PythonExe' in line for line in pip_exec)
    assert 'pip.exe' not in s.lower()

def test_model_contracts():
    cfg=json.loads((ROOT/'Config/lotus_diagnostic_config.json').read_text(encoding='utf-8'))
    assert cfg['models']['depth']['repo_id']=='jingheya/lotus-depth-d-v2-0-disparity'
    assert cfg['models']['normal']['repo_id']=='jingheya/lotus-normal-d-v1-1'
    assert cfg['models']['depth']['authority']=='LOTUS_NATIVE_DISPARITY_RELATIVE_NON_METRIC'

def test_installer_single_comfy_root_is_array_not_scalar_character():
    s=(ROOT/'Installer/install_lotus_diagnostic.ps1').read_text(encoding='utf-8')
    assert '$valid = @($candidates | Where-Object' in s
    assert "Test-Path (Join-Path $_ 'user')" in s
    assert 'resolved ComfyUI root points inside the Lotus package' in s

def test_embeddable_python_pip_probe_cannot_abort_before_bootstrap():
    s=(ROOT/'Installer/install_lotus_diagnostic.ps1').read_text(encoding='utf-8')
    assert 'function Test-PrivatePip' in s
    assert 'Start-Process -FilePath $PythonExe' in s
    assert "if (-not (Test-PrivatePip)) {" in s
    assert 'Bootstrapping it now' in s
    assert '& $PythonExe -m pip --version *> $null' not in s

def test_comfy_root_fallback_does_not_escape_function_scope():
    s=(ROOT/'Installer/install_lotus_diagnostic.ps1').read_text(encoding='utf-8')
    assert '$script:candidates' not in s
    assert 'foreach ($dir in (Get-ChildItem' in s
    assert 'explicit ComfyUI root points inside the Lotus package' in s

def test_model_downloader_forbids_snapshot_symlink_cache_path():
    s=(ROOT/'Runtime/worker/prepare_models.py').read_text(encoding='utf-8')
    assert 'snapshot_download' not in s
    assert 'os.symlink' not in s
    assert 'DIRECT_HTTP_NO_SYMLINKS' in s
    assert '.part' in s
    assert '_reuse_legacy_blob' in s

def test_installer_sets_no_symlink_runtime_policy():
    s=(ROOT/'Installer/install_lotus_diagnostic.ps1').read_text(encoding='utf-8')
    assert "HF_HUB_DISABLE_SYMLINKS_WARNING" in s
    assert 'direct no-symlink downloader' in s

def test_direct_downloader_resume_and_legacy_reuse(tmp_path):
    import importlib.util
    mod_path=ROOT/'Runtime/worker/prepare_models.py'
    spec=importlib.util.spec_from_file_location('prepare_models_under_test', mod_path)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    legacy=tmp_path/'legacy'; (legacy/'blobs').mkdir(parents=True)
    payload=b'legacy-complete-data'
    import hashlib
    sha=hashlib.sha256(payload).hexdigest()
    (legacy/'blobs'/sha).write_bytes(payload)
    dest=tmp_path/'model'/'file.bin'
    assert m._reuse_legacy_blob(legacy, {'name':'file.bin','size':len(payload),'sha256':sha,'blob_id':None}, dest)
    assert dest.read_bytes()==payload
    full=b'0123456789abcdef'
    class Resp:
        def __init__(self, body, status): self.body=body; self.status_code=status
        def __enter__(self): return self
        def __exit__(self,*a): return False
        def raise_for_status(self):
            if self.status_code >= 400: raise RuntimeError(self.status_code)
        def iter_content(self, chunk_size):
            for i in range(0,len(self.body),3): yield self.body[i:i+3]
    class Session:
        def get(self,url,headers=None,**kwargs):
            h=headers or {}; r=h.get('Range')
            if r:
                start=int(r.split('=')[1].split('-')[0]); return Resp(full[start:],206)
            return Resp(full,200)
    old=m.hf_hub_url; m.hf_hub_url=lambda **kwargs:'https://example.invalid/file'
    try:
        out=tmp_path/'resume.bin'; Path(str(out)+'.part').write_bytes(full[:5])
        m._download_direct('owner/repo','deadbeef',{'name':'resume.bin','size':len(full),'sha256':hashlib.sha256(full).hexdigest()},out,Session())
        assert out.read_bytes()==full
        assert not Path(str(out)+'.part').exists()
    finally:
        m.hf_hub_url=old

def test_r4_inference_adapter_uses_official_pipeline_and_low_vram_offload():
    s=(ROOT/'Runtime/worker/lotus_infer_adapter.py').read_text(encoding='utf-8')
    assert 'from pipeline import LotusDPipeline' in s
    assert 'local_files_only=True' in s
    assert 'enable_model_cpu_offload' in s
    assert 'total_gb <= 13.0' in s
    assert "timesteps=[999]" in s
    assert "task_emb=task_emb" in s

def test_r4_worker_surfaces_child_log_tail_to_comfyui():
    s=(ROOT/'Runtime/worker/lotus_diagnostic_worker.py').read_text(encoding='utf-8')
    assert "lotus_infer_adapter.py" in s
    assert 'def _tail_text' in s
    assert '--- inference log tail ---' in s
    assert "--memory-mode', 'auto'" in s

def test_r4_installer_copies_adapter_and_selftest_imports_torch():
    inst=(ROOT/'Installer/install_lotus_diagnostic.ps1').read_text(encoding='utf-8')
    worker=(ROOT/'Runtime/worker/lotus_diagnostic_worker.py').read_text(encoding='utf-8')
    assert 'lotus_infer_adapter.py' in inst
    assert 'import numpy, cv2, PIL, matplotlib, torch, diffusers, transformers, safetensors' in worker
