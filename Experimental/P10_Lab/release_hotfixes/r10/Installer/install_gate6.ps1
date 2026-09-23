param(
    [string]$InstallRoot = $(Join-Path $env:LOCALAPPDATA "ConceptGhost"),
    [switch]$SkipComfyDownload,
    [switch]$ForcePortable,
    [switch]$SkipWanDownload,
    [switch]$SkipColmapDownload
)

$ErrorActionPreference = "Stop"
$BundleRoot = Split-Path -Parent $PSScriptRoot
$PayloadRoot = Join-Path $BundleRoot "Payload"
$Gate5Installer = Join-Path $PSScriptRoot "install_gate5.ps1"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " ConceptGhost v1.54 P10 Gate 6 - REFINED RECONSTRUCTION COMPLETE INSTALLER r10" -ForegroundColor Cyan
Write-Host " Base: full proven v1.53.0 + Gate5 WAN + known-camera COLMAP reconstruction" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[1/5] Installing/verifying complete Gate 5 stack first..." -ForegroundColor Yellow
$gate5Params = @{ InstallRoot = $InstallRoot }
if ($SkipComfyDownload) { $gate5Params["SkipComfyDownload"] = $true }
if ($ForcePortable) { $gate5Params["ForcePortable"] = $true }
if ($SkipWanDownload) { $gate5Params["SkipWanDownload"] = $true }
& $Gate5Installer @gate5Params
if ($LASTEXITCODE -ne 0) { throw "Gate 5 installer returned exit code $LASTEXITCODE" }

$MarkerPath = Join-Path $InstallRoot "INSTALL_READY.json"
if (-not (Test-Path $MarkerPath)) { throw "Gate5/base installation did not create INSTALL_READY.json" }
$Marker = Get-Content $MarkerPath -Raw | ConvertFrom-Json
$ComfyRoot = [string]$Marker.comfy_root
$ComfyPython = [string]$Marker.comfy_python
if (-not (Test-Path $ComfyRoot)) { throw "ComfyUI root is missing: $ComfyRoot" }
if (-not (Test-Path $ComfyPython)) { throw "ComfyUI Python is missing: $ComfyPython" }

$CustomNodes = Join-Path $ComfyRoot "custom_nodes"
$P10Dst = Join-Path $CustomNodes "ConceptGhost_P10_Lab"
$BackupRoot = Join-Path $InstallRoot "backups"
$P10Backup = Join-Path $BackupRoot "ConceptGhost_P10_Lab_before_gate6"
New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
if (Test-Path $P10Backup) { Remove-Item $P10Backup -Recurse -Force }
if (Test-Path $P10Dst) { Copy-Item $P10Dst $P10Backup -Recurse -Force }

try {
    Write-Host ""
    Write-Host "[2/5] Updating P10 runtime to frozen Gate 6 code..." -ForegroundColor Yellow
    $CodeManifest = Join-Path $BundleRoot "P10_GATE6_CODE_MANIFEST.json"
    $CodeReport = Join-Path $InstallRoot "P10_GATE6_CODE_READY.json"
    & $ComfyPython (Join-Path $PSScriptRoot "download_gate6_code.py") --p10-root $P10Dst --manifest $CodeManifest --report $CodeReport
    if ($LASTEXITCODE -ne 0) { throw "Gate6 code overlay download/verification failed." }
    Set-Content (Join-Path $P10Dst "CONCEPTGHOST_P10_VERSION.txt") "ConceptGhost v1.54 P10 Gate 6 Reconstruction Preview r10" -Encoding UTF8

    Write-Host ""
    Write-Host "[3/5] Installing integrated Gate 6 Refined workflow..." -ForegroundColor Yellow
    $InternalBaseWorkflowOnly = ($env:CONCEPTGHOST_INTERNAL_BASE_WORKFLOW_ONLY -eq "1")
    if ($InternalBaseWorkflowOnly) {
        # Modern DR9R+ bundles intentionally ship only the two current numbered workflows.
        # Reuse the current Stage-B Production workflow as a PRIVATE Gate6 verifier fixture.
        $PrivateWorkflowDir = Join-Path $InstallRoot "internal\workflows"
        New-Item -ItemType Directory -Force -Path $PrivateWorkflowDir | Out-Null
        $WorkflowSrc = Join-Path $PayloadRoot "workflows\02_ConceptGhost_P10_PRODUCTION.json"
        $WorkflowDst = Join-Path $PrivateWorkflowDir "02_ConceptGhost_P10_PRODUCTION_GATE6_VERIFY.json"
        if (-not (Test-Path $WorkflowSrc)) { throw "Current P10 Production workflow missing from bundle: $WorkflowSrc" }
        Copy-Item $WorkflowSrc $WorkflowDst -Force
        Write-Host "[internal] Gate6 uses the current Production workflow only as a private verifier fixture." -ForegroundColor Green
    } else {
        $WorkflowRoot = Join-Path $ComfyRoot "user\default\workflows"
        $WorkflowDir = Join-Path $WorkflowRoot "ConceptGhost"
        New-Item -ItemType Directory -Force -Path $WorkflowDir | Out-Null
        $WorkflowSrc = Join-Path $PayloadRoot "workflows\ConceptGhost_v1.54_P10_Gate06_REFINED_RECONSTRUCTION_PREVIEW_r10.json"
        $WorkflowDst = Join-Path $WorkflowDir "ConceptGhost_v1.54_P10_Gate06_REFINED_RECONSTRUCTION_PREVIEW_r10.json"
        if (-not (Test-Path $WorkflowSrc)) { throw "Gate6 workflow missing from bundle: $WorkflowSrc" }
        Copy-Item $WorkflowSrc $WorkflowDst -Force
    }

    Write-Host ""
    Write-Host "[4/5] Installing/verifying COLMAP 4.2.0 CUDA runtime..." -ForegroundColor Yellow
    Write-Host "Compressed download: 380.97 MB; installed footprint estimated ~1.3 GB." -ForegroundColor Cyan
    $ColmapReport = Join-Path $InstallRoot "P10_GATE6_COLMAP_READY.json"
    $colmapArgs = @("--install-root",$InstallRoot,"--report",$ColmapReport)
    if ($SkipColmapDownload) { $colmapArgs += "--skip-download" }
    & $ComfyPython (Join-Path $PSScriptRoot "download_gate6_colmap.py") @colmapArgs
    if ($LASTEXITCODE -ne 0) { throw "COLMAP installation/verification failed." }

    Write-Host ""
    Write-Host "[5/5] Verifying complete Gate 6 Refined reconstruction stack..." -ForegroundColor Yellow
    $P10Report = Join-Path $InstallRoot "P10_GATE6_READY.json"
    & $ComfyPython (Join-Path $PSScriptRoot "verify_p10_gate6.py") --comfy-root $ComfyRoot --workflow $WorkflowDst --models-report $Marker.p10_gate5_models_report --code-report $CodeReport --colmap-report $ColmapReport --report $P10Report
    if ($LASTEXITCODE -ne 0) { throw "P10 Gate 6 verification failed." }

    $Marker | Add-Member -NotePropertyName p10_gate6_status -NotePropertyValue "PASS" -Force
    $Marker | Add-Member -NotePropertyName p10_gate6_release -NotePropertyValue "ConceptGhost_v1.54_P10_Gate06_REFINED_RECONSTRUCTION_PREVIEW_r10" -Force
    $Marker | Add-Member -NotePropertyName p10_gate6_workflow -NotePropertyValue $WorkflowDst -Force
    $Marker | Add-Member -NotePropertyName p10_gate6_node_root -NotePropertyValue $P10Dst -Force
    $Marker | Add-Member -NotePropertyName p10_gate6_report -NotePropertyValue $P10Report -Force
    $Marker | Add-Member -NotePropertyName p10_gate6_code_report -NotePropertyValue $CodeReport -Force
    $Marker | Add-Member -NotePropertyName p10_gate6_colmap_report -NotePropertyValue $ColmapReport -Force
    $Marker | ConvertTo-Json -Depth 12 | Set-Content $MarkerPath -Encoding UTF8

    Write-Host ""
    Write-Host "[PASS] Gate 5 WAN stack remains installed and verified." -ForegroundColor Green
    Write-Host "[PASS] P10 Gate 6 known-camera reconstruction runtime installed." -ForegroundColor Green
    Write-Host "[PASS] COLMAP 4.2.0 CUDA installed/verified." -ForegroundColor Green
    Write-Host "[PASS] Refined workflow now continues WAN -> sparse -> dense -> pre-fusion mesh." -ForegroundColor Green
    Write-Host "Workflow: $WorkflowDst" -ForegroundColor Cyan
}
catch {
    if (Test-Path $P10Backup) {
        Write-Host "Restoring pre-Gate6 P10 runtime after failure..." -ForegroundColor Yellow
        if (Test-Path $P10Dst) { Remove-Item $P10Dst -Recurse -Force -ErrorAction SilentlyContinue }
        Copy-Item $P10Backup $P10Dst -Recurse -Force
    }
    throw
}
