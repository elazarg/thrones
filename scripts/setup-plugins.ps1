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
    if (-not (Test-Path "$gambitDir\.venv")) {
        Write-Host "Creating .venv..."
        python -m .venv "$gambitDir\.venv"
    }
    Write-Host "Installing dependencies..."
    & "$gambitDir\.venv\Scripts\pip" install -e "$gambitDir[dev]" --quiet
    Write-Host "Gambit plugin ready." -ForegroundColor Green
} else {
    Write-Host "Gambit plugin directory not found, skipping." -ForegroundColor DarkYellow
}

# --- PyCID plugin ---
$pycidDir = "plugins\pycid"
if (Test-Path $pycidDir) {
    Write-Host "`n--- PyCID Plugin ---" -ForegroundColor Yellow
    if (-not (Test-Path "$pycidDir\.venv")) {
        Write-Host "Creating .venv..."
        python -m .venv "$pycidDir\.venv"
    }
    Write-Host "Installing dependencies..."
    & "$pycidDir\.venv\Scripts\pip" install -e "$pycidDir[dev]" --quiet
    Write-Host "PyCID plugin ready." -ForegroundColor Green
} else {
    Write-Host "PyCID plugin directory not found, skipping." -ForegroundColor DarkYellow
}

# --- Vegas plugin ---
$vegasDir = "plugins\vegas"
if (Test-Path $vegasDir) {
    Write-Host "`n--- Vegas Plugin ---" -ForegroundColor Yellow
    if (-not (Test-Path "$vegasDir\.venv")) {
        Write-Host "Creating .venv..."
        python -m venv "$vegasDir\.venv"
    }
    Write-Host "Installing dependencies..."
    & "$vegasDir\.venv\Scripts\pip" install -e "$vegasDir[dev]" --quiet

    # Check that Vegas JAR exists
    $vegasJar = "$vegasDir\lib\vegas.jar"
    if (-not (Test-Path $vegasJar)) {
        Write-Host "Warning: Vegas JAR not found at $vegasJar" -ForegroundColor DarkYellow
        Write-Host "Build Vegas with 'cd ../vegas && mvn package -DskipTests' and copy the JAR" -ForegroundColor DarkYellow
    }
    Write-Host "Vegas plugin ready." -ForegroundColor Green
} else {
    Write-Host "Vegas plugin directory not found, skipping." -ForegroundColor DarkYellow
}

# --- EGTTools plugin ---
$egttoolsDir = "plugins\egttools"
if (Test-Path $egttoolsDir) {
    Write-Host "`n--- EGTTools Plugin ---" -ForegroundColor Yellow
    if (-not (Test-Path "$egttoolsDir\.venv")) {
        Write-Host "Creating .venv..."
        python -m venv "$egttoolsDir\.venv"
    }
    Write-Host "Installing dependencies..."
    & "$egttoolsDir\.venv\Scripts\pip" install -e "$egttoolsDir[dev]" --quiet
    Write-Host "EGTTools plugin ready." -ForegroundColor Green
} else {
    Write-Host "EGTTools plugin directory not found, skipping." -ForegroundColor DarkYellow
}

# --- OpenSpiel plugin ---
$openspielDir = "plugins\openspiel"
if (Test-Path $openspielDir) {
    Write-Host "`n--- OpenSpiel Plugin ---" -ForegroundColor Yellow
    Write-Host "Note: OpenSpiel only works on Linux/macOS. On Windows, the plugin" -ForegroundColor DarkYellow
    Write-Host "      will start but return an error status. Use WSL for full functionality." -ForegroundColor DarkYellow
    if (-not (Test-Path "$openspielDir\.venv")) {
        Write-Host "Creating .venv..."
        python -m venv "$openspielDir\.venv"
    }
    Write-Host "Installing dependencies (without open_spiel on Windows)..."
    & "$openspielDir\.venv\Scripts\pip" install -e "$openspielDir[dev]" --quiet
    Write-Host "OpenSpiel plugin ready (limited functionality on Windows)." -ForegroundColor Green
} else {
    Write-Host "OpenSpiel plugin directory not found, skipping." -ForegroundColor DarkYellow
}

Write-Host "`nPlugin setup complete." -ForegroundColor Cyan
