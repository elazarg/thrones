# Run all tests: main app, plugins, and integration
# Run from the project root: .\scripts\run-all-tests.ps1

$ErrorActionPreference = "Continue"
$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $projectRoot

$failed = 0

# --- Main App Tests (no plugins needed) ---
Write-Host "`n=== Main App Tests ===" -ForegroundColor Cyan
& .venv\Scripts\python -m pytest tests/ -v --tb=short --ignore=tests/integration
if ($LASTEXITCODE -ne 0) { $failed++ }

# --- Gambit Plugin Tests ---
if (Test-Path "plugins\gambit\venv\Scripts\python.exe") {
    Write-Host "`n=== Gambit Plugin Tests ===" -ForegroundColor Cyan
    & plugins\gambit\venv\Scripts\python -m pytest plugins\gambit\tests\ -v --tb=short
    if ($LASTEXITCODE -ne 0) { $failed++ }
} else {
    Write-Host "`n=== Gambit Plugin Tests SKIPPED (no venv) ===" -ForegroundColor DarkYellow
}

# --- PyCID Plugin Tests ---
if (Test-Path "plugins\pycid\venv\Scripts\python.exe") {
    Write-Host "`n=== PyCID Plugin Tests ===" -ForegroundColor Cyan
    & plugins\pycid\venv\Scripts\python -m pytest plugins\pycid\tests\ -v --tb=short
    if ($LASTEXITCODE -ne 0) { $failed++ }
} else {
    Write-Host "`n=== PyCID Plugin Tests SKIPPED (no venv) ===" -ForegroundColor DarkYellow
}

# --- Integration Tests (plugins started automatically by app lifespan) ---
Write-Host "`n=== Integration Tests ===" -ForegroundColor Cyan
& .venv\Scripts\python -m pytest tests\integration\ -v --tb=short
if ($LASTEXITCODE -ne 0) { $failed++ }

# --- Summary ---
Write-Host "`n========================================" -ForegroundColor Cyan
if ($failed -eq 0) {
    Write-Host "All test suites passed." -ForegroundColor Green
} else {
    Write-Host "$failed test suite(s) had failures." -ForegroundColor Red
}
exit $failed
