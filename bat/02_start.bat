@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\tools\launcher.ps1" -Mode start %*
set "DEMO_EXIT_CODE=%ERRORLEVEL%"
if not "%DEMO_EXIT_CODE%"=="0" pause
exit /b %DEMO_EXIT_CODE%
