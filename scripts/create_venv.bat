@echo off
REM Create a .venv using Python 3.12
py -3.12 -m venv .venv
if %ERRORLEVEL% neq 0 (
  echo Failed to create virtual environment.
  exit /b %ERRORLEVEL%
)

echo Created .venv using Python 3.12.
echo To activate (cmd): .\.venv\Scripts\activate.bat
echo To activate (PowerShell): .\.venv\Scripts\Activate.ps1
