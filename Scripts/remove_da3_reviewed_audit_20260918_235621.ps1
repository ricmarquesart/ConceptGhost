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

function Test-IsVolatileProtectedPath([string]$Path) {
    $p = $Path.ToLowerInvariant()
    if ($p -like '*\user\__manager\cache\*') { return $true }
    if ($p -like '*\user\__manager\batch_history\*') { return $true }
    if ($p -like '*\__pycache__\*') { return $true }
    if ($p -like '*.pyc') { return $true }
    if ($p -like '*\*.egg-info\*') { return $true }
    if ($p -like '*\cache\*') { return $true }
    if ($p -like '*\logs\*') { return $true }
    if ($p -like '*\log\*') { return $true }
    if ($p -like '*.log') { return $true }
    if ($p -like '*.tmp') { return $true }
    if ($p -like '*.temp') { return $true }
    return $false
}

function Get-StableProtectedPaths($Audit) {
    $stable = @()
    $volatile = @()
    foreach($H in @($Audit.protected_reference_hashes)) {
        $path=[string]$H.Path
        if ([string]::IsNullOrWhiteSpace($path)) { continue }
        if (Test-IsVolatileProtectedPath $path) { $volatile += $path } else { $stable += $path }
    }
    $stable = @($stable | Sort-Object -Unique)
    $volatile = @($volatile | Sort-Object -Unique)
    return @($stable), @($volatile)
}

function Capture-StableHashes([string[]]$Paths) {
    $hashes = @{}
    foreach($path in @($Paths)) {
        if (-not (Test-Path -LiteralPath $path)) {
            throw "Stable protected workflow/source file is missing before cleanup: $path. Re-run/review audit before deleting anything."
        }
        $hashes[$path] = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
    }
    return $hashes
}

function Assert-StableHashesUnchanged($BeforeHashes) {
    foreach($path in @($BeforeHashes.Keys)) {
        if (-not (Test-Path -LiteralPath $path)) {
            throw "Protected stable workflow/source disappeared during cleanup: $path"
        }
        $after=(Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
        $before=[string]$BeforeHashes[$path]
        if ($after -ne $before) {
            throw "Protected stable workflow/source changed during cleanup: $path. Before=$before After=$after"
        }
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
        Write-Host "[WARN] Could not inspect Win32_Process usage; continuing with exact-path and before/after hash safety fences. $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " ConceptGhost - Reviewed DA3 Cleanup v0.32.2" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "This remover is pinned to the reviewed audit from 2026-09-18 23:56:21." -ForegroundColor Yellow
Write-Host "It can delete ONLY the two exact DA3-exclusive paths approved by that audit." -ForegroundColor Yellow
Write-Host "Dynamic Manager caches/logs/bytecode are never deleted and do not act as hash blockers." -ForegroundColor Green
Write-Host "Stable workflows/source files are hashed immediately before cleanup and compared immediately after cleanup." -ForegroundColor Green
Write-Host "It cannot delete Pixi, the DA3 plugin, DA3 models, Python, Torch, CUDA, NumPy, Single View, Multi View/Trellis, or unrelated workflows." -ForegroundColor Green
Write-Host ""

if (-not (Test-Path -LiteralPath $AuditJson)) { throw "Reviewed audit not found: $AuditJson" }
$AuditJson=(Resolve-Path -LiteralPath $AuditJson).Path
$AuditHash=(Get-FileHash -Algorithm SHA256 -LiteralPath $AuditJson).Hash.ToLowerInvariant()
if ($AuditHash -ne $ExpectedAuditSha256) { throw "Audit file differs from the reviewed upload. Re-review before cleanup." }
$Audit=Get-Content -LiteralPath $AuditJson -Raw | ConvertFrom-Json
if ($Audit.schema -ne $ExpectedSchema) { throw "Unsupported audit schema: $($Audit.schema). Expected $ExpectedSchema" }
if ($Audit.mode -ne $ExpectedMode) { throw "Unexpected audit mode: $($Audit.mode)" }

$SafeItems=@($Audit.items | Where-Object { $_.Class -eq "SAFE_TO_DELETE" })
if ($SafeItems.Count -ne 2) { throw "Reviewed audit must contain exactly two SAFE_TO_DELETE items; found $($SafeItems.Count)." }
$SafePaths=@($SafeItems | ForEach-Object { [string]$_.Path })
foreach($P in $SafePaths) { if ($AllowedExact -notcontains $P) { throw "Audit contains an unapproved SAFE_TO_DELETE path: $P" } }
foreach($P in $AllowedExact) { if ($SafePaths -notcontains $P) { throw "Reviewed SAFE_TO_DELETE path missing from audit: $P" } }

foreach($P in $ProtectedKeepExact) {
    $item=@($Audit.items | Where-Object { [string]$_.Path -eq $P })
    if ($item.Count -ne 1 -or [string]$item[0].Class -ne "KEEP") { throw "Protected reviewed path is not KEEP in the audit: $P" }
    if (-not (Test-Path -LiteralPath $P)) { throw "Protected KEEP path is missing before cleanup: $P" }
}

Write-Host "[PRECHECK] Building current stable protection baseline..." -ForegroundColor Cyan
$split = Get-StableProtectedPaths $Audit
$StablePaths = @($split[0])
$VolatilePaths = @($split[1])
if ($StablePaths.Count -lt 1) { throw "No stable protected workflow/source files remained after volatility filtering; cleanup blocked." }
$StableBefore = Capture-StableHashes $StablePaths
Write-Host ("[PASS] Stable protected files captured: {0}" -f $StablePaths.Count) -ForegroundColor Green
Write-Host ("[INFO] Volatile references ignored as hash blockers only (never deleted): {0}" -f $VolatilePaths.Count) -ForegroundColor DarkGray

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
foreach($T in $SafeItems) { Write-Host ("  {0:N2} GB  {1}" -f ([double]$T.Bytes/1GB),$T.Path) -ForegroundColor Yellow }
Write-Host ""
$Answer=Read-Host "Type $ConfirmationPhrase to delete only the approved DA3-exclusive paths"
if ($Answer -ne $ConfirmationPhrase) { Write-Host "Cancelled. No files were changed."; exit 0 }

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
foreach($P in $AllowedExact) { if (Test-Path -LiteralPath $P) { throw "Cleanup verification failed; approved path still exists: $P" } }
foreach($P in $ProtectedKeepExact) { if (-not (Test-Path -LiteralPath $P)) { throw "Protected KEEP path disappeared during cleanup: $P" } }
Assert-StableHashesUnchanged $StableBefore

$Result=[ordered]@{
    schema="ConceptGhost.DA3SafeCleanupResult.v0.32.2"
    timestamp=(Get-Date).ToString("o")
    source_audit=$AuditJson
    source_audit_sha256=$AuditHash
    source_audit_schema=$Audit.schema
    removed_items=$SafeItems
    reclaimed_bytes=$BeforeBytes
    protected_keep_paths=$ProtectedKeepExact
    stable_protected_file_count=$StablePaths.Count
    volatile_reference_count=$VolatilePaths.Count
    stable_before_after_hash_check="PASS"
    cleanup_scope="ONLY_REVIEWED_DA3_EXCLUSIVE_PATHS"
}
$Result | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $ResultPath -Encoding UTF8
Write-Host ""
Write-Host "[PASS] Reviewed DA3-exclusive cleanup completed." -ForegroundColor Green
Write-Host ("Reclaimed approximately {0:N2} GB ({1:N0} bytes)." -f ([double]$BeforeBytes/1GB),$BeforeBytes) -ForegroundColor Green
Write-Host "Result report: $ResultPath" -ForegroundColor Cyan
