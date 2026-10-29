@echo off
setlocal
cd /d "%~dp0.."
set PYTHONUTF8=1
where py >nul 2>&1
if errorlevel 1 (
    python run.py %*
) else (
    py -3 run.py %*
)
if errorlevel 1 pause
endlocal
