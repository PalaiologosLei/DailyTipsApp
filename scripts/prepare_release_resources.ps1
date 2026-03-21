param(
    [string]$PythonExe = "",
    [switch]$SkipPythonRuntime
)

$ErrorActionPreference = "Stop"

function Resolve-PythonExe {
    param([string]$ExplicitPath)

    if ($ExplicitPath) {
        return (Resolve-Path $ExplicitPath).Path
    }

    if ($env:DAILYTIPS_PYTHON_EXE) {
        return (Resolve-Path $env:DAILYTIPS_PYTHON_EXE).Path
    }

    $preferred = @(
        "D:\Applications\miniconda\python.exe",
        (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1)
    ) | Where-Object { $_ }

    foreach ($candidate in $preferred) {
        if (Test-Path $candidate) {
            return (Resolve-Path $candidate).Path
        }
    }

    throw "Unable to locate python.exe. Pass -PythonExe or set DAILYTIPS_PYTHON_EXE."
}

function Reset-Directory {
    param([string]$PathValue)

    if (Test-Path $PathValue) {
        Remove-Item $PathValue -Recurse -Force
    }
    New-Item -ItemType Directory -Path $PathValue | Out-Null
}

function Copy-Directory {
    param(
        [string]$Source,
        [string]$Destination
    )

    if (-not (Test-Path $Source)) {
        throw "Required source path not found: $Source"
    }

    New-Item -ItemType Directory -Path (Split-Path -Parent $Destination) -Force | Out-Null
    Copy-Item $Source -Destination $Destination -Recurse -Force
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$resourceRoot = Join-Path $repoRoot "src-tauri\resources"

Reset-Directory $resourceRoot

Copy-Directory (Join-Path $repoRoot "src") (Join-Path $resourceRoot "src")

$assetSource = Join-Path $repoRoot "assets\backgrounds\default"
$assetTarget = Join-Path $resourceRoot "assets\backgrounds\default"
Copy-Directory $assetSource $assetTarget

$tectonicSource = Join-Path $repoRoot "vendor\tectonic"
$tectonicTarget = Join-Path $resourceRoot "vendor\tectonic"
Copy-Directory $tectonicSource $tectonicTarget

if (-not $SkipPythonRuntime) {
    $pythonExePath = Resolve-PythonExe -ExplicitPath $PythonExe
    $pythonRoot = Split-Path -Parent $pythonExePath
    $pythonTarget = Join-Path $resourceRoot "python-runtime"
    New-Item -ItemType Directory -Path $pythonTarget -Force | Out-Null

    $filePatterns = @(
        "python.exe",
        "pythonw.exe",
        "python*.dll",
        "vcruntime*.dll",
        "msvcp*.dll"
    )

    foreach ($pattern in $filePatterns) {
        Get-ChildItem -Path $pythonRoot -Filter $pattern -File -ErrorAction SilentlyContinue | ForEach-Object {
            Copy-Item $_.FullName -Destination (Join-Path $pythonTarget $_.Name) -Force
        }
    }

    foreach ($dirName in @("DLLs", "Lib", "Library", "Scripts")) {
        $sourceDir = Join-Path $pythonRoot $dirName
        if (Test-Path $sourceDir) {
            Copy-Directory $sourceDir (Join-Path $pythonTarget $dirName)
        }
    }

    $siteCustomize = @'
import os
import sys
from pathlib import Path

runtime_root = Path(__file__).resolve().parent.parent
resource_root = Path(os.environ.get("DAILYTIPS_RESOURCE_ROOT", runtime_root.parent))
if str(resource_root) not in sys.path:
    sys.path.insert(0, str(resource_root))
'@

    $siteCustomizePath = Join-Path $pythonTarget "Lib\site-packages\sitecustomize.py"
    New-Item -ItemType Directory -Path (Split-Path -Parent $siteCustomizePath) -Force | Out-Null
    Set-Content -Path $siteCustomizePath -Value $siteCustomize -Encoding UTF8
}

Write-Host "Release resources are ready at $resourceRoot"
