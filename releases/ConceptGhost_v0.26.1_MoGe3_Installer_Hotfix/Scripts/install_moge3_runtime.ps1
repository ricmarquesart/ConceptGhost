param(
    [string]$RuntimeRoot = "$env:LOCALAPPDATA\ConceptGhost-MoGeRuntime-v1"
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$BundleRoot = Split-Path -Parent $PSScriptRoot
$ToolRoot = Join-Path $BundleRoot "Tools\MoGeRuntime"
$VendorZip = Join-Path $ToolRoot "vendor\MoGe-main.zip"
$WorkerSrc = Join-Path $ToolRoot "worker"
$PythonRoot = Join-Path $RuntimeRoot "python"
$PythonExe = Join-Path $PythonRoot "python.exe"
$RepoRoot = Join-Path $RuntimeRoot "repo"
$Repo = Join-Path $RepoRoot "MoGe"
$WorkerDst = Join-Path $RuntimeRoot "worker"
$Cache = Join-Path $RuntimeRoot "cache"
$Logs = Join-Path $RuntimeRoot "logs"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Log = Join-Path $Logs ("install_" + $Stamp + ".log")
$TorchIndex = if ($env:CONCEPTGHOST_MOGE_TORCH_INDEX) { $env:CONCEPTGHOST_MOGE_TORCH_INDEX } else { "https://download.pytorch.org/whl/cu130" }

New-Item -ItemType Directory -Force -Path $RuntimeRoot,$PythonRoot,$RepoRoot,$WorkerDst,$Cache,$Logs | Out-Null
"ConceptGhost MoGe Runtime v1 - owned isolated runtime" | Set-Content (Join-Path $RuntimeRoot "OWNED_BY_CONCEPTGHOST_MOGE_RUNTIME_V1.txt") -Encoding UTF8
if (Test-Path (Join-Path $RuntimeRoot "READY.json")) { Remove-Item (Join-Path $RuntimeRoot "READY.json") -Force }

function Log([string]$Text) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Text"
    Write-Host $line
    Add-Content -Path $Log -Value $line -Encoding UTF8
}
function Run([string]$Exe, [string[]]$CommandArgs) {
    Log ("RUN: `"$Exe`" " + ($CommandArgs -join ' '))

    # Windows PowerShell 5.1 promotes native stderr records to NativeCommandError
    # when $ErrorActionPreference is Stop. Many healthy CLI tools legitimately
    # write informational text to stderr, so run native commands with Continue
    # and decide success strictly from the process exit code.
    $PreviousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & $Exe @CommandArgs 2>&1 | Tee-Object -FilePath $Log -Append
        $ExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $PreviousErrorActionPreference
    }

    if ($ExitCode -ne 0) { throw "Command failed with exit code ${ExitCode}: $Exe" }
}

Log "ConceptGhost MoGe-3 isolated installation spike (Stage A1)."
Log "Runtime root: $RuntimeRoot"
Log "Torch index: $TorchIndex"
Log "Protected ComfyUI path (read-only / never modified): C:\Users\rmarq\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI"

if (-not (Test-Path $VendorZip)) { throw "Bundled MoGe source ZIP missing: $VendorZip" }

$Git = Get-Command git.exe -ErrorAction SilentlyContinue
if (-not $Git) { throw "Git for Windows is required by MoGe's official git-pinned dependencies. Install Git, then rerun this BAT. No protected Python environment was modified." }
Log ("Git: " + (& git --version))

if (-not (Test-Path $PythonExe)) {
    $PyInstaller = Join-Path $env:TEMP "python-3.11.9-amd64.exe"
    $PyUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    Log "Downloading private Python 3.11.9 from python.org..."
    Invoke-WebRequest -Uri $PyUrl -OutFile $PyInstaller -UseBasicParsing
    Log "Installing private Python under runtime root (no PATH, no launcher, no associations)..."
    $PyArgs = @(
        "/quiet", "InstallAllUsers=0", "TargetDir=$PythonRoot", "PrependPath=0",
        "Include_launcher=0", "InstallLauncherAllUsers=0", "AssociateFiles=0",
        "Shortcuts=0", "Include_doc=0", "Include_test=0", "Include_pip=1"
    )
    $proc = Start-Process -FilePath $PyInstaller -ArgumentList $PyArgs -Wait -PassThru
    if ($proc.ExitCode -ne 0) { throw "Private Python installer failed: $($proc.ExitCode)" }
}
if (-not (Test-Path $PythonExe)) { throw "Private Python not found after installation: $PythonExe" }
Run -Exe $PythonExe -CommandArgs @("-m","pip","install","--upgrade","pip","setuptools","wheel")

if (Test-Path $Repo) { Remove-Item $Repo -Recurse -Force }
$ExtractTmp = Join-Path $RepoRoot "_extract"
if (Test-Path $ExtractTmp) { Remove-Item $ExtractTmp -Recurse -Force }
New-Item -ItemType Directory -Force -Path $ExtractTmp | Out-Null
Expand-Archive -Path $VendorZip -DestinationPath $ExtractTmp -Force
$Extracted = Join-Path $ExtractTmp "MoGe-main"
if (-not (Test-Path (Join-Path $Extracted "pyproject.toml"))) { throw "Unexpected MoGe source ZIP layout" }
Move-Item $Extracted $Repo
Remove-Item $ExtractTmp -Recurse -Force
Copy-Item (Join-Path $WorkerSrc "*") $WorkerDst -Recurse -Force

$env:HF_HOME = Join-Path $Cache "hf"
$env:HUGGINGFACE_HUB_CACHE = Join-Path $Cache "hf\hub"
$env:TORCH_HOME = Join-Path $Cache "torch"
$env:CONCEPTGHOST_MOGE_RUNTIME = $RuntimeRoot
New-Item -ItemType Directory -Force -Path $env:HF_HOME,$env:HUGGINGFACE_HUB_CACHE,$env:TORCH_HOME | Out-Null

Log "Installing isolated PyTorch/torchvision..."
Run -Exe $PythonExe -CommandArgs @("-m","pip","install","--index-url",$TorchIndex,"torch>=2.4","torchvision>=0.19")

Log "Installing official MoGe source and its pinned dependencies into the private runtime..."
Run -Exe $PythonExe -CommandArgs @("-m","pip","install","-e",$Repo)

Log "Running import + checkpoint + one-image CUDA inference gate..."
Run -Exe $PythonExe -CommandArgs @((Join-Path $WorkerDst "verify_moge3_runtime.py"))

$Ready = Join-Path $RuntimeRoot "READY.json"
if (-not (Test-Path $Ready)) { throw "Verification did not create READY.json" }
$readyJson = Get-Content $Ready -Raw | ConvertFrom-Json
if ($readyJson.status -ne "PASS") { throw "MoGe-3 runtime gate did not pass" }
Log "PASS - MoGe-3 isolated runtime is ready."
Log "READY: $Ready"
Log "Next roadmap gate: A2 normalized evidence contract, then A3 selector. MoGe-2 remains untouched."
