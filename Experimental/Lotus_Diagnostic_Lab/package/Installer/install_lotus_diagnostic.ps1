param(
  [string]$ComfyUIRoot = ""
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$PackageRoot = Split-Path -Parent $PSScriptRoot
$RuntimeRoot = Join-Path $env:LOCALAPPDATA 'ConceptGhost-LotusDiagnostic'
$PythonRoot = Join-Path $RuntimeRoot 'Python'
$PythonExe = Join-Path $PythonRoot 'python.exe'
$ManifestDir = Join-Path $RuntimeRoot 'Manifests'
$CacheRoot = Join-Path $RuntimeRoot 'Cache'
$TempRoot = Join-Path $RuntimeRoot 'Temp'
$LogsRoot = Join-Path $RuntimeRoot 'Logs'
$BackupsRoot = Join-Path $RuntimeRoot 'Backups'
$InstallLog = Join-Path $LogsRoot 'install.log'

function Write-Log([string]$m) {
  $line = ('[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $m)
  Write-Host $line
  if (Test-Path $LogsRoot) { Add-Content -LiteralPath $InstallLog -Value $line -Encoding UTF8 }
}
function Get-Sha256([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Resolve-ComfyRoot {
  param([string]$Explicit)
  if ($Explicit) {
    $r = [IO.Path]::GetFullPath($Explicit)
    $packageResolved = [IO.Path]::GetFullPath($PackageRoot)
    if ($r.StartsWith($packageResolved, [System.StringComparison]::OrdinalIgnoreCase)) {
      throw "Safety stop: explicit ComfyUI root points inside the Lotus package: $r"
    }
    if ((Test-Path (Join-Path $r 'main.py')) -and (Test-Path (Join-Path $r 'custom_nodes')) -and (Test-Path (Join-Path $r 'user'))) { return $r }
    throw "Explicit ComfyUI root is invalid: $r"
  }
  $candidates = @(
    (Join-Path $env:LOCALAPPDATA 'Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI')
  )
  $base = Join-Path $env:LOCALAPPDATA 'Comfy-Desktop\ComfyUI-Installs'
  if (Test-Path $base) {
    foreach ($dir in (Get-ChildItem -LiteralPath $base -Directory -ErrorAction SilentlyContinue)) {
      $p1 = Join-Path $dir.FullName 'ComfyUI'
      $p2 = $dir.FullName
      if ((Test-Path (Join-Path $p1 'main.py'))) { $candidates += $p1 }
      if ((Test-Path (Join-Path $p2 'main.py'))) { $candidates += $p2 }
    }
  }
  # Always materialize an array. In Windows PowerShell a single pipeline result is a scalar
  # string; indexing $valid[0] would then return only the first character (for example 'C').
  $valid = @($candidates | Where-Object {
      $_ -and
      (Test-Path (Join-Path $_ 'main.py')) -and
      (Test-Path (Join-Path $_ 'custom_nodes')) -and
      (Test-Path (Join-Path $_ 'user'))
    } | Select-Object -Unique)
  if ($valid.Count -eq 1) {
    $resolved = [IO.Path]::GetFullPath([string]$valid[0])
    $packageResolved = [IO.Path]::GetFullPath($PackageRoot)
    if ($resolved.StartsWith($packageResolved, [System.StringComparison]::OrdinalIgnoreCase)) {
      throw "Safety stop: resolved ComfyUI root points inside the Lotus package: $resolved"
    }
    return $resolved
  }
  if ($valid.Count -gt 1) { throw "Multiple ComfyUI roots found. Re-run with -ComfyUIRoot. Candidates: $($valid -join '; ')" }
  throw 'ComfyUI root not found. Install/start ComfyUI Desktop first or pass -ComfyUIRoot.'
}

New-Item -ItemType Directory -Force -Path $RuntimeRoot,$ManifestDir,$CacheRoot,$TempRoot,$LogsRoot,$BackupsRoot,(Join-Path $RuntimeRoot 'Models'),(Join-Path $RuntimeRoot 'Outputs'),(Join-Path $RuntimeRoot 'Work'),(Join-Path $RuntimeRoot 'Source'),(Join-Path $RuntimeRoot 'Worker') | Out-Null
Write-Log 'Lotus Diagnostic isolated installer started.'
Write-Log "Runtime root: $RuntimeRoot"

# Free-space gate. Full official depth + native-normal package is intentionally conservative.
$driveName = ([IO.Path]::GetPathRoot($RuntimeRoot)).TrimEnd('\').TrimEnd(':')
$drive = Get-PSDrive -Name $driveName
$freeGB = [math]::Round($drive.Free / 1GB, 2)
Write-Log "Free disk space on $($drive.Name): $freeGB GB"
if ($drive.Free -lt 18GB) { throw "At least 18 GB free is required before the full Lotus Diagnostic installation. Available: $freeGB GB" }

$ComfyUIRoot = Resolve-ComfyRoot $ComfyUIRoot
Write-Log "Detected ComfyUI root: $ComfyUIRoot"

# Explicit protected paths audit. We do not write to any of them.
$protected = @(
  (Join-Path $env:LOCALAPPDATA 'ConceptGhost-MoGeRuntime-v1'),
  (Join-Path $env:LOCALAPPDATA 'Comfy-Desktop\ComfyUI-Shared\models'),
  (Join-Path $ComfyUIRoot 'models')
)
$protectedSnapshot = @()
foreach ($p in $protected) {
  $protectedSnapshot += [ordered]@{ path=$p; exists=(Test-Path $p); last_write_utc= if(Test-Path $p){(Get-Item $p).LastWriteTimeUtc.ToString('o')}else{$null} }
}
$protectedBefore = Join-Path $ManifestDir 'protected_paths_before.json'
$protectedSnapshot | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $protectedBefore -Encoding UTF8

# Isolated environment variables. No global/user environment variables are modified.
$env:HF_HOME = Join-Path $CacheRoot 'huggingface'
$env:HUGGINGFACE_HUB_CACHE = Join-Path $CacheRoot 'huggingface\hub'
$env:TORCH_HOME = Join-Path $CacheRoot 'torch'
$env:XDG_CACHE_HOME = $CacheRoot
$env:PIP_CACHE_DIR = Join-Path $CacheRoot 'pip'
$env:TEMP = $TempRoot
$env:TMP = $TempRoot
$env:PYTHONNOUSERSITE = '1'

# 1) Private Python 3.10.11 embeddable runtime.
if (-not (Test-Path $PythonExe)) {
  Write-Log 'Downloading private Python 3.10.11 embeddable runtime...'
  $pyZip = Join-Path $TempRoot 'python-3.10.11-embed-amd64.zip'
  Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip' -OutFile $pyZip -UseBasicParsing
  New-Item -ItemType Directory -Force -Path $PythonRoot | Out-Null
  Expand-Archive -LiteralPath $pyZip -DestinationPath $PythonRoot -Force
  Remove-Item -LiteralPath $pyZip -Force
  $pth = Join-Path $PythonRoot 'python310._pth'
  $lines = Get-Content -LiteralPath $pth
  $lines = $lines | ForEach-Object { if ($_ -eq '#import site') { 'import site' } else { $_ } }
  if ($lines -notcontains '.\Lib\site-packages') { $lines += '.\Lib\site-packages' }
  Set-Content -LiteralPath $pth -Value $lines -Encoding ASCII
  New-Item -ItemType Directory -Force -Path (Join-Path $PythonBoot 'Lib\site-packages') | Out-Null
}

# 2) pip only inside private Python.
# The official Python embeddable package intentionally ships without pip. Probe it without
# routing native stderr through PowerShell's error stream (ErrorActionPreference='Stop' would
# otherwise terminate before the bootstrap branch can run).
function Test-PrivatePip {
  $probeOut = Join-Path $TempRoot 'pip_probe.stdout.txt'
  $probeErr = Join-Path $TempRoot 'pip_probe.stderr.txt'
  Remove-Item -LiteralPath $probeOut,$probeErr -Force -ErrorAction SilentlyContinue
  $proc = Start-Process -FilePath $PythonExe -ArgumentList @('-m','pip','--version') -Wait -PassThru -NoNewWindow -RedirectStandardOutput $probeOut -RedirectStandardError $probeErr
  $ok = ($proc.ExitCode -eq 0)
  Remove-Item -LiteralPath $probeOut,$probeErr -Force -ErrorAction SilentlyContinue
  return $ok
}

if (-not (Test-PrivatePip)) {
  Write-Log 'pip is absent from the private embeddable Python. Bootstrapping it now...'
  $gp = Join-Path $TempRoot 'get-pip.py'
  Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile $gp -UseBasicParsing
  & $PythonExe $gp --no-warn-script-location
  if ($LASTEXITCODE -ne 0) { throw 'get-pip failed inside isolated Python.' }
  Remove-Item -LiteralPath $gp -Force
}
if (-not (Test-PrivatePip)) { throw 'pip bootstrap completed but private pip is still unavailable.' }
& $PythonExe -m pip install --no-cache-dir --disable-pip-version-check 'pip==24.3.1'
if ($LASTEXITCODE -ne 0) { throw 'Failed to pin pip in isolated runtime.' }

# 3) Pinned CUDA/PyTorch stack inside private Python only.
Write-Log 'Installing private Torch 2.3.1 / CUDA 12.1 wheels...'
& $PythonExe -m pip install --no-cache-dir --disable-pip-version-check --index-url 'https://download.pytorch.org/whl/cu121' 'torch==2.3.1' 'torchvision==0.18.1' 'torchaudio==2.3.1'
if ($LASTEXITCODE -ne 0) { throw 'Private Torch installation failed.' }
Write-Log 'Installing pinned Lotus inference dependencies into private Python...'
& $PythonExe -m pip install --no-cache-dir --disable-pip-version-check -r (Join-Path $PackageRoot 'Runtime\requirements_runtime.txt')
if ($LASTEXITCODE -ne 0) { throw 'Private Lotus dependency installation failed.' }

# 4) Official Lotus source is kept private, not installed into ComfyUI.
$SourceRoot = Join-Path $RuntimeRoot 'Source\Lotus'
if (-not (Test-Path (Join-Path $SourceRoot 'infer.py'))) {
  Write-Log 'Downloading official EnVision-Research/Lotus source...'
  $lotusZip = Join-Path $TempRoot 'lotus-main.zip'
  $extract = Join-Path $TempRoot 'lotus_source_extract'
  if (Test-Path $extract) { Remove-Item -LiteralPath $extract -Recurse -Force }
  Invoke-WebRequest -Uri 'https://github.com/EnVision-Research/Lotus/archive/refs/heads/main.zip' -OutFile $lotusZip -UseBasicParsing
  Expand-Archive -LiteralPath $lotusZip -DestinationPath $extract -Force
  if (Test-Path $SourceRoot) { Remove-Item -LiteralPath $SourceRoot -Recurse -Force }
  Move-Item -LiteralPath (Join-Path $extract 'Lotus-main') -Destination $SourceRoot
  Remove-Item -LiteralPath $lotusZip -Force
  Remove-Item -LiteralPath $extract -Recurse -Force
}

# 5) Install worker scripts under the isolated root.
Copy-Item -LiteralPath (Join-Path $PackageRoot 'Runtime\worker\prepare_models.py') -Destination (Join-Path $RuntimeRoot 'Worker\prepare_models.py') -Force
Copy-Item -LiteralPath (Join-Path $PackageRoot 'Runtime\worker\lotus_diagnostic_worker.py') -Destination (Join-Path $RuntimeRoot 'Worker\lotus_diagnostic_worker.py') -Force
Copy-Item -LiteralPath (Join-Path $PackageRoot 'Config\lotus_diagnostic_config.json') -Destination (Join-Path $ManifestDir 'lotus_diagnostic_config.json') -Force

# 6) Download complete official discriminative depth + native-normal checkpoints into isolated HF cache.
Write-Log 'Downloading official Lotus disparity and native-normal model snapshots...'
& $PythonExe (Join-Path $RuntimeRoot 'Worker\prepare_models.py') --runtime-root $RuntimeRoot
if ($LASTEXITCODE -ne 0) { throw 'Model snapshot preparation failed.' }

# 7) Install only the tiny host bridge and standalone workflow.
$BridgeSrc = Join-Path $PackageRoot 'Payload\custom_nodes\ConceptGhost_Lotus_Diagnostic'
$BridgeDst = Join-Path $ComfyUIRoot 'custom_nodes\ConceptGhost_Lotus_Diagnostic'
if (Test-Path $BridgeDst) {
  $owner = Join-Path $BridgeDst 'OWNERSHIP.json'
  if (-not (Test-Path $owner)) { throw "Refusing to overwrite unknown existing custom-node folder: $BridgeDst" }
  $ownerJson = Get-Content -LiteralPath $owner -Raw | ConvertFrom-Json
  if ($ownerJson.owner -ne 'ConceptGhost-LotusDiagnostic') { throw "Refusing to overwrite custom-node folder owned by another package: $BridgeDst" }
  Remove-Item -LiteralPath $BridgeDst -Recurse -Force
}
Copy-Item -LiteralPath $BridgeSrc -Destination $BridgeDst -Recurse -Force

$WorkflowDir = Join-Path $ComfyUIRoot 'user\default\workflows'
New-Item -ItemType Directory -Force -Path $WorkflowDir | Out-Null
$WorkflowSrc = Join-Path $PackageRoot 'Payload\workflows\Lotus_Depth_Diagnostic.json'
$WorkflowDst = Join-Path $WorkflowDir 'Lotus_Depth_Diagnostic.json'
$preexistingWorkflowBackup = $null
if (Test-Path $WorkflowDst) {
  $oldHash = Get-Sha256 $WorkflowDst
  $newHash = Get-Sha256 $WorkflowSrc
  if ($oldHash -ne $newHash) {
    $preexistingWorkflowBackup = Join-Path $BackupsRoot ('Lotus_Depth_Diagnostic.preexisting.' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.json')
    Copy-Item -LiteralPath $WorkflowDst -Destination $preexistingWorkflowBackup -Force
    Write-Log "Existing workflow backed up before replacement: $preexistingWorkflowBackup"
  }
}
Copy-Item -LiteralPath $WorkflowSrc -Destination $WorkflowDst -Force

# 8) Final ownership/install manifest. Nothing else outside RuntimeRoot is owned.
$runtimeCfg = Get-Content -LiteralPath (Join-Path $ManifestDir 'runtime_config.json') -Raw | ConvertFrom-Json
$installManifest = [ordered]@{
  schema='ConceptGhost.LotusDiagnostic.InstallManifest.v1'
  owner='ConceptGhost-LotusDiagnostic'
  installed_utc=(Get-Date).ToUniversalTime().ToString('o')
  runtime_root=$RuntimeRoot
  comfyui_root=$ComfyUIRoot
  host_write_policy='ONLY_UNIQUE_BRIDGE_AND_WORKFLOW'
  host_pip_mutation=$false
  shared_model_mutation=$false
  paths=[ordered]@{
    bridge=$BridgeDst
    workflow=$WorkflowDst
    preexisting_workflow_backup=$preexistingWorkflowBackup
  }
  hashes=[ordered]@{
    workflow=(Get-Sha256 $WorkflowDst)
    bridge_nodes=(Get-Sha256 (Join-Path $BridgeDst 'nodes.py'))
    bridge_init=(Get-Sha256 (Join-Path $BridgeDst '__init__.py'))
  }
  models=$runtimeCfg.models
  protected_paths=$protected
}
$installManifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $ManifestDir 'install_manifest.json') -Encoding UTF8

# Confirm protected directories were not written by this installer path.
$after = @()
foreach ($p in $protected) { $after += [ordered]@{ path=$p; exists=(Test-Path $p); last_write_utc= if(Test-Path $p){(Get-Item $p).LastWriteTimeUtc.ToString('o')}else{$null} } }
$after | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $ManifestDir 'protected_paths_after.json') -Encoding UTF8

Write-Log 'Install completed. Running isolated self-test...'
& $PythonExe (Join-Path $RuntimeRoot 'Worker\lotus_diagnostic_worker.py') --runtime-root $RuntimeRoot --self-test
if ($LASTEXITCODE -ne 0) { throw 'Isolated runtime self-test failed.' }
Write-Log 'PASS. Restart ComfyUI, then open Lotus_Depth_Diagnostic.json.'
Write-Host ''
Write-Host 'IMPORTANT: This package does not modify the official ConceptGhost workflow or shared Python/model environments.'
