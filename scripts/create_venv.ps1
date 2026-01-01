param(
    [string]$PythonLauncher = 'py -3.12'
)

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Error "Python launcher 'py' not found. Install Python 3.12 or use the full python executable path."
    exit 1
}

& py -3.12 -m venv .venv

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to create virtual environment."
    exit $LASTEXITCODE
}

Write-Output "Created .venv using Python 3.12."
Write-Output "Activate in PowerShell: .\\.venv\\Scripts\\Activate.ps1"
Write-Output "Activate in cmd: .\\.venv\\Scripts\\activate.bat"
