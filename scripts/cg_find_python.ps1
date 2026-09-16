param(
    [string]$ProjectRoot = 'G:\My Drive\ConceptGhost',
    [string]$LegacyRoot = 'C:\ConceptGhost',
    [string]$AppDataRoot = $env:APPDATA
)

$ErrorActionPreference = 'SilentlyContinue'
$ProgressPreference = 'SilentlyContinue'

function Emit-IfPythonExists {
    param([string]$Candidate)
    if ([string]::IsNullOrWhiteSpace($Candidate)) { return }
    if (Test-Path -LiteralPath $Candidate -PathType Leaf) {
        try {
            $resolved = (Resolve-Path -LiteralPath $Candidate).Path
        }
        catch {
            $resolved = $Candidate
        }
        [Console]::WriteLine($resolved)
        exit 0
    }
}

function Try-InstallManifest {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return }
    try {
        $doc = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
        Emit-IfPythonExists ([string]$doc.python_executable)
    }
    catch { }
}

function Try-PreinstallInventory {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return }
    try {
        $doc = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
        Emit-IfPythonExists ([string]$doc.comfyui.selected.python_executable)
    }
    catch { }
}

# Prefer manifests produced by successful protected ConceptGhost stages. They
# already record the exact ComfyUI host interpreter used on this machine.
foreach ($root in @($ProjectRoot, $LegacyRoot)) {
    if ([string]::IsNullOrWhiteSpace($root)) { continue }
    $manifestRoot = Join-Path $root 'Manifests'
    if (-not (Test-Path -LiteralPath $manifestRoot)) {
        $manifestRoot = Join-Path $root 'manifests'
    }
    Try-InstallManifest (Join-Path $manifestRoot 'da3_baseline_install.json')
    Try-InstallManifest (Join-Path $manifestRoot 'atlas_camera_deps_install.json')
    Try-PreinstallInventory (Join-Path $manifestRoot 'preinstall_inventory.json')
}

# If manifests are unavailable, recover ComfyUI Desktop's Python directly from
# its own installations.json. This does not modify the Desktop installation.
if (-not [string]::IsNullOrWhiteSpace($AppDataRoot)) {
    $installationsPath = Join-Path $AppDataRoot 'Comfy Desktop\installations.json'
    if (Test-Path -LiteralPath $installationsPath -PathType Leaf) {
        try {
            $records = Get-Content -LiteralPath $installationsPath -Raw | ConvertFrom-Json
            foreach ($record in @($records)) {
                $installPath = [string]$record.installPath
                if ([string]::IsNullOrWhiteSpace($installPath)) { continue }
                foreach ($relative in @(
                    'ComfyUI\.venv\Scripts\python.exe',
                    '.venv\Scripts\python.exe',
                    'ComfyUI\venv\Scripts\python.exe',
                    'venv\Scripts\python.exe',
                    'envs\default\Scripts\python.exe',
                    'ComfyUI\envs\default\Scripts\python.exe'
                )) {
                    Emit-IfPythonExists (Join-Path $installPath $relative)
                }
            }
        }
        catch { }
    }
}

# Last resort: a normal Python installation already exposed on PATH.
foreach ($name in @('py.exe', 'python.exe')) {
    try {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($null -ne $command) {
            Emit-IfPythonExists ([string]$command.Source)
        }
    }
    catch { }
}

exit 1
