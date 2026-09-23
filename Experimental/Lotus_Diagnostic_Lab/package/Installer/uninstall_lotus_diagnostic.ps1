$ErrorActionPreference = 'Stop'
$RuntimeRoot = Join-Path $env:LOCALAPPDATA 'ConceptGhost-LotusDiagnostic'
$Manifest = Join-Path $RuntimeRoot 'Manifests\install_manifest.json'
$PackageRoot = Split-Path -Parent $PSScriptRoot
$PackageReport = Join-Path $PackageRoot 'UNINSTALL_REPORT.txt'
$report = @()

# Do not use short helper names such as R. Windows PowerShell defines R as an alias
# for Invoke-History, and aliases take precedence over functions when invoked.
function Write-UninstallReport([string]$Message) {
  $script:report += $Message
  Write-Host $Message
}

function Save-UninstallReport {
  try {
    $script:report | Set-Content -LiteralPath $PackageReport -Encoding UTF8
  } catch {
    Write-Warning "Could not write uninstall report to package folder: $($_.Exception.Message)"
  }
}

Write-UninstallReport 'ConceptGhost-LotusDiagnostic uninstall started.'
Write-UninstallReport "Runtime root: $RuntimeRoot"

if (-not (Test-Path $RuntimeRoot)) {
  Write-UninstallReport 'Lotus Diagnostic runtime is already absent. Nothing was removed.'
  Save-UninstallReport
  exit 0
}

if (-not (Test-Path $Manifest)) {
  Save-UninstallReport
  throw "Safety stop: runtime exists but ownership manifest is missing: $Manifest"
}

$m = Get-Content -LiteralPath $Manifest -Raw | ConvertFrom-Json
if ($m.owner -ne 'ConceptGhost-LotusDiagnostic') {
  Save-UninstallReport
  throw 'Safety stop: ownership manifest does not belong to Lotus Diagnostic.'
}

$bridge = [string]$m.paths.bridge
$workflow = [string]$m.paths.workflow
$backup = [string]$m.paths.preexisting_workflow_backup

if ($bridge) {
  if (Test-Path $bridge) {
    $owner = Join-Path $bridge 'OWNERSHIP.json'
    if ((Test-Path $owner) -and ((Get-Content -LiteralPath $owner -Raw | ConvertFrom-Json).owner -eq 'ConceptGhost-LotusDiagnostic')) {
      Remove-Item -LiteralPath $bridge -Recurse -Force
      Write-UninstallReport "Removed owned bridge: $bridge"
    } else {
      Write-UninstallReport "PRESERVED unknown/modified bridge without valid ownership marker: $bridge"
    }
  } else {
    Write-UninstallReport "Owned bridge already absent; continuing resumable uninstall: $bridge"
  }
}

if ($workflow) {
  if (Test-Path $workflow) {
    $hash = (Get-FileHash -LiteralPath $workflow -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($hash -eq ([string]$m.hashes.workflow).ToLowerInvariant()) {
      Remove-Item -LiteralPath $workflow -Force
      Write-UninstallReport "Removed owned workflow: $workflow"
    } else {
      Write-UninstallReport "PRESERVED modified workflow: $workflow"
    }
  } else {
    Write-UninstallReport "Owned workflow already absent; continuing resumable uninstall: $workflow"
  }
}

if ($backup -and (Test-Path $backup)) {
  if ($workflow -and -not (Test-Path $workflow)) {
    $workflowParent = Split-Path -Parent $workflow
    if ($workflowParent -and -not (Test-Path $workflowParent)) {
      New-Item -ItemType Directory -Force -Path $workflowParent | Out-Null
    }
    Copy-Item -LiteralPath $backup -Destination $workflow -Force
    Write-UninstallReport "Restored pre-existing workflow backup: $workflow"
  } else {
    Write-UninstallReport 'Pre-existing workflow backup retained only inside runtime because destination is occupied.'
  }
}

Save-UninstallReport

Remove-Item -LiteralPath $RuntimeRoot -Recurse -Force
Write-Host 'Removed isolated runtime, models, caches, temporary files, logs and diagnostic outputs.'
Write-Host "Uninstall report: $PackageReport"
