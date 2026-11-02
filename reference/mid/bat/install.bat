@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0.."
set "PYTHONUTF8=1"
where python >nul 2>&1
if not errorlevel 1 (
    python run.py setup %*
) else (
    py -3 run.py setup %*
)
if errorlevel 1 pause
endlocal
