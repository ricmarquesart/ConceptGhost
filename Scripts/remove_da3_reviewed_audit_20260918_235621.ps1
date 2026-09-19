param(
    [string]$AuditJson = "$env:LOCALAPPDATA\ConceptGhost-Audits\DA3_SAFE_CLEANUP_AUDIT_20260918_235621.json"
)
$ErrorActionPreference = "Stop"

$ExpectedSchema = "ConceptGhost.DA3SafeCleanupAudit.v0.32"
$ExpectedAuditSha256 = "c68c19255eb982887762a3c8248c6dd1c0fe59caab09faeb2403679f676b7b82"
$ExpectedMode = "MEASURE_AND_CLASSIFY_ONLY_NO_DELETION"
$ConfirmationPhrase = "REMOVE_REVIEWED_DA3_4GB"

$AllowedExact = @(
    "C:\ConceptGhost\cache\da3-comfy-env",
    "C:\ConceptGhost\config\da3_host_paths.json"
)

$ProtectedKeepExact = @(
    "C:\ConceptGhost\cache\pixi",
    "C:\Users\rmarq\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\custom_nodes\ComfyUI-DepthAnythingV3",
    "C:\Users\rmarq\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\models\depthanything3"
)

function Get-PathStats([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        return [pscustomobject]@{ Bytes=[int64]0; Files=[int64]0; Exists=$false }
    }
    $item = Get-Item -LiteralPath $Path -Force
    if (-not $item.PSIsContainer) {
        return [pscustomobject]@{ Bytes=[int64]$item.Length; Files=[int64]1; Exists=$true }
    }
    $sum=[int64]0; $count=[int64]0
    Get-ChildItem -LiteralPath $Path -Recurse -Force -File -ErrorAction SilentlyContinue | ForEach-Object {
        $sum += [int64]$_.Length; $count++
    }
    return [pscustomobject]@{ Bytes=$sum; Files=$count; Exists=$true }
}

function Assert-ProtectedHashes($Audit) {
    $mismatches = New-Object System.Collections.Generic.List[object]
    foreach($H in @($Audit.protected_reference_hashes)) {
        $path=[string]$H.Path
        $expected=([string]$H.Sha256).ToLowerInvariant()
        if (-not (Test-Path -LiteralPath $path)) {
            $mismatches.Add([pscustomobject]@{Path=$path;Reason="MISSING"})
            continue
        }
        try {
            $actual=(Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
            if ($actual -ne $expected) {
                $mismatches.Add([pscustomobject]@{Path=$path;Reason="HASH_CHANGED";Before=$expected;After=$actual})
            }
        } catch {
            $mismatches.Add([pscustomobject]@{Path=$path;Reason="HASH_ERROR";Error=$_.Exception.Message})
        }
    }
    if ($mismatches.Count -gt 0) {
        throw "Protected Single/Multi/Trellis evidence changed since the reviewed audit. Re-run the audit before deleting anything. First mismatch: $($mismatches[0] | ConvertTo-Json -Compress)"
    }
}

function Assert-NoDa3ProcessUse {
    try {
        $root = "C:\ConceptGhost\cache\da3-comfy-env"
        $users = Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
            ($_.ExecutablePath -and $_.ExecutablePath.StartsWith($root,[System.StringComparison]::OrdinalIgnoreCase)) -or
            ($_.CommandLine -and $_.CommandLine.IndexOf($root,[System.StringComparison]::OrdinalIgnoreCase) -ge 0)
        }
        if (@($users).Count -gt 0) {
            $names = @($users | ForEach-Object { "$($_.Name) pid=$($_.ProcessId)" }) -join ", "
            throw "A running process is using the DA3-only environment: $names"
        }
    } catch {
        if ($_.Exception.Message -like "A running process is using*") { throw }
        Write-Host "[WARN] Could not inspect Win32_Process usage; continuing with path/hash safety fences. $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " ConceptGhost - Reviewed DA3 Cleanup v0.32" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "This remover is pinned to the reviewed audit from 2026-09-18 23:56:21." -ForegroundColor Yellow
Write-Host "It can delete ONLY the two exact DA3-exclusive paths approved by that audit." -ForegroundColor Yellow
Write-Host "It cannot delete Pixi, the DA3 plugin, DA3 models, Python, Torch, CUDA, NumPy, Single View, Multi View/Trellis, or unrelated workflows." -ForegroundColor Green
Write-Host ""

if (-not (Test-Path -LiteralPath $AuditJson)) {
    throw "Reviewed audit not found: $AuditJson"
}
$AuditJson=(Resolve-Path -LiteralPath $AuditJson).Path
$AuditHash=(Get-FileHash -Algorithm SHA256 -LiteralPath $AuditJson).Hash.ToLowerInvariant()
if ($AuditHash -ne $ExpectedAuditSha256) {
    throw "Audit file differs from the reviewed upload. Expected SHA-256 $ExpectedAuditSha256 but got $AuditHash. Re-review before cleanup."
}
$Audit=Get-Content -LiteralPath $AuditJson -Raw | ConvertFrom-Json
if ($Audit.schema -ne $ExpectedSchema) { throw "Unsupported audit schema: $($Audit.schema). Expected $ExpectedSchema" }
if ($Audit.mode -ne $ExpectedMode) { throw "Unexpected audit mode: $($Audit.mode)" }
if (@($Audit.protected_reference_hashes).Count -lt 1) { throw "Audit contains no protected-reference hashes; cleanup blocked." }

$SafeItems=@($Audit.items | Where-Object { $_.Class -eq "SAFE_TO_DELETE" })
if ($SafeItems.Count -ne 2) { throw "Reviewed audit must contain exactly two SAFE_TO_DELETE items; found $($SafeItems.Count)." }
$SafePaths=@($SafeItems | ForEach-Object { [string]$_.Path })
foreach($P in $SafePaths) {
    if ($AllowedExact -notcontains $P) { throw "Audit contains an unapproved SAFE_TO_DELETE path: $P" }
}
foreach($P in $AllowedExact) {
    if ($SafePaths -notcontains $P) { throw "Reviewed SAFE_TO_DELETE path missing from audit: $P" }
}

foreach($P in $ProtectedKeepExact) {
    $item=@($Audit.items | Where-Object { [string]$_.Path -eq $P })
    if ($item.Count -ne 1 -or [string]$item[0].Class -ne "KEEP") {
        throw "Protected reviewed path is not KEEP in the audit: $P"
    }
}

Write-Host "[PRECHECK] Verifying protected Single/Multi/Trellis hashes..." -ForegroundColor Cyan
Assert-ProtectedHashes $Audit
Write-Host "[PASS] Protected hashes match the reviewed audit." -ForegroundColor Green

Write-Host "[PRECHECK] Verifying current DA3-exclusive folder size/file counts still match the reviewed audit..." -ForegroundColor Cyan
foreach($T in $SafeItems) {
    $P=[string]$T.Path
    $stats=Get-PathStats $P
    if (-not $stats.Exists) { throw "Approved DA3-exclusive path is already missing: $P" }
    if ([int64]$stats.Bytes -ne [int64]$T.Bytes -or [int64]$stats.Files -ne [int64]$T.Files) {
        throw "Approved path changed since audit: $P. Audit bytes/files=$($T.Bytes)/$($T.Files), current=$($stats.Bytes)/$($stats.Files). Re-run audit before cleanup."
    }
    Write-Host ("  PASS  {0}  bytes={1:N0} files={2:N0}" -f $P,$stats.Bytes,$stats.Files) -ForegroundColor Green
}

Assert-NoDa3ProcessUse

Write-Host ""
Write-Host "APPROVED DELETE SET:" -ForegroundColor Yellow
foreach($T in $SafeItems) {
    Write-Host ("  {0:N2} GB  {1}" -f ([double]$T.Bytes/1GB),$T.Path) -ForegroundColor Yellow
}
Write-Host ""
Write-Host "PROTECTED KEEP SET:" -ForegroundColor Green
foreach($P in $ProtectedKeepExact) { Write-Host "  KEEP  $P" -ForegroundColor Green }
Write-Host ""
$Answer=Read-Host "Type $ConfirmationPhrase to delete only the approved DA3-exclusive paths"
if ($Answer -ne $ConfirmationPhrase) {
    Write-Host "Cancelled. No files were changed." -ForegroundColor Yellow
    exit 0
}

$BeforeBytes=[int64](($SafeItems | Measure-Object -Property Bytes -Sum).Sum)
$ResultRoot=Join-Path $env:LOCALAPPDATA "ConceptGhost-Audits"
New-Item -ItemType Directory -Force -Path $ResultRoot | Out-Null
$Stamp=Get-Date -Format "yyyyMMdd_HHmmss"
$ResultPath=Join-Path $ResultRoot ("DA3_SAFE_CLEANUP_RESULT_"+$Stamp+".json")

foreach($T in $SafeItems) {
    $P=[string]$T.Path
    $resolved=(Resolve-Path -LiteralPath $P).Path
    if ($AllowedExact -notcontains $resolved) { throw "Resolved-path safety fence rejected: $resolved" }
    Remove-Item -LiteralPath $resolved -Recurse -Force
    Write-Host "[REMOVED] $resolved" -ForegroundColor Green
}

foreach($P in $AllowedExact) {
    if (Test-Path -LiteralPath $P) { throw "Cleanup verification failed; approved path still exists: $P" }
}
foreach($P in $ProtectedKeepExact) {
    if (-not (Test-Path -LiteralPath $P)) { throw "Protected KEEP path disappeared during cleanup: $P" }
}
Assert-ProtectedHashes $Audit

$Result=[ordered]@{
    schema="ConceptGhost.DA3SafeCleanupResult.v0.32"
    timestamp=(Get-Date).ToString("o")
    source_audit=$AuditJson
    source_audit_sha256=$AuditHash
    source_audit_schema=$Audit.schema
    removed_items=$SafeItems
    reclaimed_bytes=$BeforeBytes
    protected_keep_paths=$ProtectedKeepExact
    protected_reference_hash_check="PASS"
    cleanup_scope="ONLY_REVIEWED_DA3_EXCLUSIVE_PATHS"
}
$Result | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $ResultPath -Encoding UTF8

Write-Host ""
Write-Host "[PASS] Reviewed DA3-exclusive cleanup completed." -ForegroundColor Green
Write-Host ("Reclaimed approximately {0:N2} GB ({1:N0} bytes)." -f ([double]$BeforeBytes/1GB),$BeforeBytes) -ForegroundColor Green
Write-Host "Protected KEEP paths: PASS" -ForegroundColor Green
Write-Host "Protected Single/Multi/Trellis hashes: PASS" -ForegroundColor Green
Write-Host "Result report: $ResultPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "NEXT: do not delete anything else. Run ConceptGhost/Single View/Multi View smoke checks separately." -ForegroundColor Yellow
