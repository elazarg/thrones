# Setup script for isolated plugin virtual environments (Windows)
# Run from the project root: .\scripts\setup-plugins.ps1

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $projectRoot

Write-Host "Setting up plugin virtual environments..." -ForegroundColor Cyan

# --- Gambit plugin ---
$gambitDir = "plugins\gambit"
if (Test-Path $gambitDir) {
    Write-Host "`n--- Gambit Plugin ---" -ForegroundColor Yellow
    if (-not (Test-Path "$gambitDir\venv")) {
        Write-Host "Creating venv..."
        python -m venv "$gambitDir\venv"
    }
    Write-Host "Installing dependencies..."
    & "$gambitDir\venv\Scripts\pip" install -e "$gambitDir[dev]" --quiet
    Write-Host "Gambit plugin ready." -ForegroundColor Green
} else {
    Write-Host "Gambit plugin directory not found, skipping." -ForegroundColor DarkYellow
}

# --- PyCID plugin ---
$pycidDir = "plugins\pycid"
if (Test-Path $pycidDir) {
    Write-Host "`n--- PyCID Plugin ---" -ForegroundColor Yellow
    if (-not (Test-Path "$pycidDir\venv")) {
        Write-Host "Creating venv..."
        python -m venv "$pycidDir\venv"
    }
    Write-Host "Installing dependencies..."
    & "$pycidDir\venv\Scripts\pip" install -e "$pycidDir[dev]" --quiet
    Write-Host "PyCID plugin ready." -ForegroundColor Green
} else {
    Write-Host "PyCID plugin directory not found, skipping." -ForegroundColor DarkYellow
}

Write-Host "`nPlugin setup complete." -ForegroundColor Cyan
