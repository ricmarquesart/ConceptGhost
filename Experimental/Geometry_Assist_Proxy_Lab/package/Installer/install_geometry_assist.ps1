param()
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$PackageRoot = Split-Path -Parent $PSScriptRoot
$RuntimeRoot = Join-Path $env:LOCALAPPDATA 'ConceptGhost-GeometryAssistDiagnostic'
$PythonRoot = Join-Path $RuntimeRoot 'Python'
$PythonExe = Join-Path $PythonRoot 'python.exe'
$ModelsRoot = Join-Path $RuntimeRoot 'Models'
$CacheRoot = Join-Path $RuntimeRoot 'Cache'
$TempRoot = Join-Path $RuntimeRoot 'Temp'
$LogsRoot = Join-Path $RuntimeRoot 'Logs'
$WorkerRoot = Join-Path $RuntimeRoot 'Worker'
$OutputsRoot = Join-Path $RuntimeRoot 'Outputs'
$ManifestRoot = Join-Path $RuntimeRoot 'Manifests'
$InstallLog = Join-Path $LogsRoot 'install.log'

New-Item -ItemType Directory -Force -Path $RuntimeRoot,$PythonRoot,$ModelsRoot,$CacheRoot,$TempRoot,$LogsRoot,$WorkerRoot,$OutputsRoot,$ManifestRoot | Out-Null

function Write-Log([string]$Message) {
  $line = ('[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message)
  Write-Host $line
  Add-Content -LiteralPath $InstallLog -Value $line -Encoding UTF8
}

function Test-PrivatePip {
  $stdout = Join-Path $TempRoot 'pip_probe.out.txt'
  $stderr = Join-Path $TempRoot 'pip_probe.err.txt'
  Remove-Item -LiteralPath $stdout,$stderr -Force -ErrorAction SilentlyContinue
  $p = Start-Process -FilePath $PythonExe -ArgumentList @('-m','pip','--version') -Wait -PassThru -NoNewWindow -RedirectStandardOutput $stdout -RedirectStandardError $stderr
  $ok = ($p.ExitCode -eq 0)
  Remove-Item -LiteralPath $stdout,$stderr -Force -ErrorAction SilentlyContinue
  return $ok
}

Write-Log 'Geometry Assist Diagnostic isolated installer started.'
Write-Log "Runtime root: $RuntimeRoot"

$driveName = ([IO.Path]::GetPathRoot($RuntimeRoot)).TrimEnd('\').TrimEnd(':')
$drive = Get-PSDrive -Name $driveName
$freeGB = [math]::Round($drive.Free / 1GB, 2)
Write-Log "Free disk space: $freeGB GB"
if ($drive.Free -lt 25GB) {
  throw "At least 25 GB free is required before installation. Available: $freeGB GB"
}

$protectedPaths = @(
  (Join-Path $env:LOCALAPPDATA 'ConceptGhost-MoGeRuntime-v1'),
  (Join-Path $env:LOCALAPPDATA 'ConceptGhost-LotusDiagnostic'),
  (Join-Path $env:LOCALAPPDATA 'Comfy-Desktop\ComfyUI-Shared'),
  (Join-Path $env:LOCALAPPDATA 'Comfy-Desktop\ComfyUI-Installs')
)
$protectedBefore = foreach ($p in $protectedPaths) {
  [ordered]@{
    path = $p
    exists = (Test-Path $p)
    last_write_utc = if (Test-Path $p) { (Get-Item $p).LastWriteTimeUtc.ToString('o') } else { $null }
  }
}
$protectedBefore | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $ManifestRoot 'protected_paths_before.json') -Encoding UTF8

$env:PYTHONNOUSERSITE = '1'
$env:HF_HOME = Join-Path $CacheRoot 'huggingface'
$env:HUGGINGFACE_HUB_CACHE = Join-Path $CacheRoot 'huggingface\hub'
$env:TRANSFORMERS_CACHE = Join-Path $CacheRoot 'transformers'
$env:TORCH_HOME = Join-Path $CacheRoot 'torch'
$env:XDG_CACHE_HOME = $CacheRoot
$env:PIP_CACHE_DIR = Join-Path $CacheRoot 'pip'
$env:TEMP = $TempRoot
$env:TMP = $TempRoot
$env:HF_HUB_DISABLE_TELEMETRY = '1'
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = '1'

# Private CPython 3.10.11 embeddable.
if (-not (Test-Path $PythonExe)) {
  Write-Log 'Downloading private Python 3.10.11 embeddable runtime...'
  $zip = Join-Path $TempRoot 'python-3.10.11-embed-amd64.zip'
  Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip' -OutFile $zip -UseBasicParsing
  Expand-Archive -LiteralPath $zip -DestinationPath $PythonRoot -Force
  Remove-Item -LiteralPath $zip -Force
  $pth = Join-Path $PythonRoot 'python310._pth'
  $lines = @(Get-Content -LiteralPath $pth)
  $lines = $lines | ForEach-Object { if ($_ -eq '#import site') { 'import site' } else { $_ } }
  if ($lines -notcontains '.\Lib\site-packages') { $lines += '.\Lib\site-packages' }
  Set-Content -LiteralPath $pth -Value $lines -Encoding ASCII
  New-Item -ItemType Directory -Force -Path (Join-Path $PythonRoot 'Lib\site-packages') | Out-Null
}

if (-not (Test-PrivatePip)) {
  Write-Log 'Bootstrapping pip inside private Python...'
  $gp = Join-Path $TempRoot 'get-pip.py'
  Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile $gp -UseBasicParsing
  & $PythonExe $gp --no-warn-script-location
  if ($LASTEXITCODE -ne 0) { throw 'Private pip bootstrap failed.' }
  Remove-Item -LiteralPath $gp -Force
}
if (-not (Test-PrivatePip)) { throw 'Private pip is unavailable after bootstrap.' }

Write-Log 'Installing private Torch 2.3.1 / CUDA 12.1 stack...'
& $PythonExe -m pip install --no-cache-dir --disable-pip-version-check --index-url 'https://download.pytorch.org/whl/cu121' 'torch==2.3.1' 'torchvision==0.18.1'
if ($LASTEXITCODE -ne 0) { throw 'Private Torch installation failed.' }

Write-Log 'Installing pinned diagnostic dependencies into private Python...'
& $PythonExe -m pip install --no-cache-dir --disable-pip-version-check -r (Join-Path $PackageRoot 'Runtime\requirements_runtime.txt')
if ($LASTEXITCODE -ne 0) { throw 'Private dependency installation failed.' }

Copy-Item -LiteralPath (Join-Path $PackageRoot 'Runtime\worker\prepare_models.py') -Destination (Join-Path $WorkerRoot 'prepare_models.py') -Force
Copy-Item -LiteralPath (Join-Path $PackageRoot 'Runtime\worker\geometry_assist_worker.py') -Destination (Join-Path $WorkerRoot 'geometry_assist_worker.py') -Force
Copy-Item -LiteralPath (Join-Path $PackageRoot 'Config\geometry_assist_config.json') -Destination (Join-Path $ManifestRoot 'geometry_assist_config.json') -Force

Write-Log 'Downloading/materializing private SDXL, ControlNet and IP-Adapter models...'
& $PythonExe (Join-Path $WorkerRoot 'prepare_models.py') --runtime-root $RuntimeRoot
if ($LASTEXITCODE -ne 0) { throw 'Private model preparation failed.' }

Write-Log 'Running isolated import/CUDA/model self-test...'
& $PythonExe (Join-Path $WorkerRoot 'geometry_assist_worker.py') --runtime-root $RuntimeRoot --self-test
if ($LASTEXITCODE -ne 0) { throw 'Geometry Assist isolated self-test failed.' }

$protectedAfter = foreach ($p in $protectedPaths) {
  [ordered]@{
    path = $p
    exists = (Test-Path $p)
    last_write_utc = if (Test-Path $p) { (Get-Item $p).LastWriteTimeUtc.ToString('o') } else { $null }
  }
}
$protectedAfter | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $ManifestRoot 'protected_paths_after.json') -Encoding UTF8

$manifest = [ordered]@{
  schema = 'ConceptGhost.GeometryAssistDiagnostic.InstallManifest.v1'
  installed_utc = (Get-Date).ToUniversalTime().ToString('o')
  runtime_root = $RuntimeRoot
  python = $PythonExe
  host_pip_mutation = $false
  shared_model_mutation = $false
  official_workflow_mutation = $false
  model_root = $ModelsRoot
  output_root = $OutputsRoot
  hardware_target = 'RTX 2080 Ti 11GB'
}
$manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $ManifestRoot 'install_manifest.json') -Encoding UTF8

Write-Log 'PASS. Geometry Assist Diagnostic is installed in complete isolation.'
Write-Host ''
Write-Host 'Next: drag a PNG/JPG onto 03_RUN_GEOMETRY_ASSIST_DIAGNOSTIC.bat'
