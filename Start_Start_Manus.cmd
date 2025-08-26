@echo off
setlocal
pushd "%~dp0"

REM Wrapper ruft PowerShell-Startskript auf und zeigt Exitcode an.
powershell -NoProfile -ExecutionPolicy Bypass -File ".\Start-OpenManus.ps1" %*
set ERR=%ERRORLEVEL%

echo.
echo ===========================
echo  Exitcode: %ERR%
echo ===========================
echo.

pause
endlocal & exit /b %ERR%
