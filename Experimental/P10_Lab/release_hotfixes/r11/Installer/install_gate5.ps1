param(
    [string]$InstallRoot = $(Join-Path $env:LOCALAPPDATA "ConceptGhost"),
    [switch]$SkipComfyDownload,
    [switch]$ForcePortable,
    [switch]$SkipWanDownload
)

$ErrorActionPreference = "Stop"
$BundleRoot = Split-Path -Parent $PSScriptRoot
$PayloadRoot = Join-Path $BundleRoot "Payload"
$BaseInstaller = Join-Path $PSScriptRoot "install_all.ps1"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " ConceptGhost v1.54 P10 Gate 5 - REFINED WAN COMPLETE INSTALLER r1" -ForegroundColor Cyan
Write-Host " Base: full proven v1.53.0 + Gate4 runtime + Gate5 WAN first pass" -ForegroundColor Cyan
Write-Host " Target: RTX 2080 Ti 11 GB / sequential 832x480 / 33-frame windows" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[1/3] Running the complete v1.53.0 installer/verification path..." -ForegroundColor Yellow

$baseParams = @{ InstallRoot = $InstallRoot }
if ($SkipComfyDownload) { $baseParams["SkipComfyDownload"] = $true }
if ($ForcePortable) { $baseParams["ForcePortable"] = $true }
& $BaseInstaller @baseParams
if ($LASTEXITCODE -ne 0) { throw "Base v1.53 installer returned exit code $LASTEXITCODE" }

$MarkerPath = Join-Path $InstallRoot "INSTALL_READY.json"
if (-not (Test-Path $MarkerPath)) { throw "Base installation did not create INSTALL_READY.json" }
$Marker = Get-Content $MarkerPath -Raw | ConvertFrom-Json
$ComfyRoot = [string]$Marker.comfy_root
$ComfyPython = [string]$Marker.comfy_python
if (-not (Test-Path $ComfyRoot)) { throw "ComfyUI root from v1.53 marker is missing: $ComfyRoot" }
if (-not (Test-Path $ComfyPython)) { throw "ComfyUI Python from v1.53 marker is missing: $ComfyPython" }

Write-Host ""
Write-Host "[2/3] Installing integrated P10 Gate 5 Refined overlay..." -ForegroundColor Yellow
$CustomNodes = Join-Path $ComfyRoot "custom_nodes"
$P10Dst = Join-Path $CustomNodes "ConceptGhost_P10_Lab"
$P10Src = Join-Path $PayloadRoot "custom_nodes\ConceptGhost_P10_Lab"
if (-not (Test-Path $P10Src)) { throw "P10 payload missing from bundle: $P10Src" }
$BackupRoot = Join-Path $InstallRoot "backups"
$P10Backup = Join-Path $BackupRoot "ConceptGhost_P10_Lab_before_gate5"
New-Item -ItemType Directory -Force -Path $CustomNodes,$BackupRoot | Out-Null
if (Test-Path $P10Backup) { Remove-Item $P10Backup -Recurse -Force }
if (Test-Path $P10Dst) {
    Copy-Item $P10Dst $P10Backup -Recurse -Force
    Remove-Item $P10Dst -Recurse -Force
}
Copy-Item $P10Src $P10Dst -Recurse -Force
Set-Content (Join-Path $P10Dst "CONCEPTGHOST_P10_VERSION.txt") "ConceptGhost v1.54 P10 Gate 5 Refined WAN Preview r1" -Encoding UTF8

$InternalBaseWorkflowOnly = ($env:CONCEPTGHOST_INTERNAL_BASE_WORKFLOW_ONLY -eq "1")
if ($InternalBaseWorkflowOnly) {
    # Modern DR9R+ bundles intentionally ship only the two current numbered workflows.
    # Reuse the current Stage-B Production workflow as a PRIVATE verifier fixture; do
    # not require or install the historical Gate5 preview workflow.
    $PrivateWorkflowDir = Join-Path $InstallRoot "internal\workflows"
    New-Item -ItemType Directory -Force -Path $PrivateWorkflowDir | Out-Null
    $WorkflowSrc = Join-Path $PayloadRoot "workflows\02_ConceptGhost_P10_PRODUCTION.json"
    $WorkflowDst = Join-Path $PrivateWorkflowDir "02_ConceptGhost_P10_PRODUCTION_GATE5_VERIFY.json"
    if (-not (Test-Path $WorkflowSrc)) { throw "Current P10 Production workflow missing from bundle: $WorkflowSrc" }
    Copy-Item $WorkflowSrc $WorkflowDst -Force
    Write-Host "[internal] Gate5 uses the current Production workflow only as a private verifier fixture." -ForegroundColor Green
} else {
    $WorkflowRoot = Join-Path $ComfyRoot "user\default\workflows"
    $WorkflowDir = Join-Path $WorkflowRoot "ConceptGhost"
    New-Item -ItemType Directory -Force -Path $WorkflowDir | Out-Null
    $WorkflowSrc = Join-Path $PayloadRoot "workflows\ConceptGhost_v1.54_P10_Gate05_REFINED_WAN_PREVIEW_r1.json"
    $WorkflowDst = Join-Path $WorkflowDir "ConceptGhost_v1.54_P10_Gate05_REFINED_WAN_PREVIEW_r1.json"
    if (-not (Test-Path $WorkflowSrc)) { throw "P10 Gate 5 workflow missing from bundle" }
    Copy-Item $WorkflowSrc $WorkflowDst -Force
}

Write-Host ""
Write-Host "[3/3] Verifying/downloading WAN assets (~24 GB total; existing verified files are reused)..." -ForegroundColor Yellow
$ModelsReport = Join-Path $InstallRoot "P10_GATE5_MODELS_READY.json"
$modelArgs = @("--comfy-root",$ComfyRoot,"--report",$ModelsReport)
if ($SkipWanDownload) { $modelArgs += "--skip-download" }
& $ComfyPython (Join-Path $PSScriptRoot "download_gate5_models.py") @modelArgs
if ($LASTEXITCODE -ne 0) {
    if (Test-Path $P10Backup) {
        if (Test-Path $P10Dst) { Remove-Item $P10Dst -Recurse -Force -ErrorAction SilentlyContinue }
        Copy-Item $P10Backup $P10Dst -Recurse -Force
    }
    throw "WAN asset installation/verification failed; previous P10 Lab restored when available."
}

$P10Report = Join-Path $InstallRoot "P10_GATE5_READY.json"
& $ComfyPython (Join-Path $PSScriptRoot "verify_p10_gate5.py") --comfy-root $ComfyRoot --workflow $WorkflowDst --models-report $ModelsReport --report $P10Report
if ($LASTEXITCODE -ne 0) {
    if (Test-Path $P10Backup) {
        if (Test-Path $P10Dst) { Remove-Item $P10Dst -Recurse -Force -ErrorAction SilentlyContinue }
        Copy-Item $P10Backup $P10Dst -Recurse -Force
    }
    throw "P10 Gate 5 verification failed; previous P10 Lab restored when available."
}

$Marker | Add-Member -NotePropertyName p10_gate5_status -NotePropertyValue "PASS" -Force
$Marker | Add-Member -NotePropertyName p10_gate5_release -NotePropertyValue "ConceptGhost_v1.54_P10_Gate05_REFINED_WAN_PREVIEW_r1" -Force
$Marker | Add-Member -NotePropertyName p10_gate5_workflow -NotePropertyValue $WorkflowDst -Force
$Marker | Add-Member -NotePropertyName p10_gate5_node_root -NotePropertyValue $P10Dst -Force
$Marker | Add-Member -NotePropertyName p10_gate5_report -NotePropertyValue $P10Report -Force
$Marker | Add-Member -NotePropertyName p10_gate5_models_report -NotePropertyValue $ModelsReport -Force
$Marker | ConvertTo-Json -Depth 12 | Set-Content $MarkerPath -Encoding UTF8

Write-Host ""
Write-Host "[PASS] Full v1.53 base remains installed and verified." -ForegroundColor Green
Write-Host "[PASS] P10 Gate 5 Refined WAN overlay installed and verified." -ForegroundColor Green
Write-Host "[PASS] Gate4 controls/masks feed one sequential WAN sampler." -ForegroundColor Green
Write-Host "[PASS] Known P9 pixels are restored after WAN; WAN is used only in holes." -ForegroundColor Green
Write-Host "Workflow: $WorkflowDst" -ForegroundColor Cyan
