$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Error "Virtual environment not found. Create .venv first."
    exit 1
}

$env:PYTHONPATH = Join-Path $projectRoot "src"

& $python -m recall.main