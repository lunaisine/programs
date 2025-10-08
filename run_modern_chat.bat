@echo off
setlocal EnableDelayedExpansion

rem Resolve script directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

rem Prefer venv Python if available
set "PY_EXE="
if exist ".venv\Scripts\python.exe" set "PY_EXE=.venv\Scripts\python.exe"
if not defined PY_EXE where py >NUL 2>&1 && set "PY_EXE=py -3"
if not defined PY_EXE where python >NUL 2>&1 && set "PY_EXE=python"

if not defined PY_EXE (
  echo Could not find Python. Install Python 3.x or create .venv and try again.
  exit /b 1
)

%PY_EXE% "offline_chatbot_programs_modern_ui.py" --seed-file "THE SEED.txt" %*

endlocal