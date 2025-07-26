@echo off
REM Change directory to the script's location
cd /D "%~dp0"

REM Run the launcher script
echo Starting OpenManus...
python openmanus_launcher.py

REM Pause if the launcher exits with an error, or always pause if verbose output is desired.
REM For now, only pause on error.
if %errorlevel% neq 0 (
    echo.
    echo OpenManus launcher exited with an error.
    pause
)

REM If you want it to always pause, uncomment the line below and remove the if block above.
REM pause
