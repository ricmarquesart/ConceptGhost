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
    # Every pip execution is anchored to the private $PythonExe variable.
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
    # The previous regression used a direct pip probe redirected into PowerShell streams.
    assert '& $PythonExe -m pip --version *> $null' not in s


def test_comfy_root_fallback_does_not_escape_function_scope():
    s=(ROOT/'Installer/install_lotus_diagnostic.ps1').read_text(encoding='utf-8')
    assert '$script:candidates' not in s
    assert 'foreach ($dir in (Get-ChildItem' in s
    assert 'explicit ComfyUI root points inside the Lotus package' in s
