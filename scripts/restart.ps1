# Restart the Game Theory Workbench backend server

Write-Host "Stopping existing Python/uvicorn processes..." -ForegroundColor Yellow

# Find and stop uvicorn processes
Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*uvicorn*app.main*"
} | Stop-Process -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 1

Write-Host "Starting uvicorn server..." -ForegroundColor Green

# Change to project root
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

# Start the server
Start-Process python -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000" -NoNewWindow

Write-Host "Server starting on http://localhost:8000" -ForegroundColor Cyan
