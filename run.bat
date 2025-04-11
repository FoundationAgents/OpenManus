@echo off
setlocal
cd /d %~dp0

set "VENV_DIR=%~dp0.venv"
set "PYTHON_PATH=%VENV_DIR%\Scripts\python.exe"

where git >nul 2>&1
if %errorlevel% == 0 (
    echo Trying to sync with GitHub repository...
    git pull origin front-end 2>&1 || echo Failed to sync with GitHub, skipping update...
) else (
    echo Git not detected, skipping code synchronization
)

if not exist "%VENV_DIR%\" (
    echo Virtual environment not found, initializing installation...
    python -m venv "%VENV_DIR%" || (
        echo Failed to create virtual environment, please install Python 3.12 first
        pause
        exit /b 1
    )
    call "%VENV_DIR%\Scripts\activate.bat"
    pip install -r requirements.txt || (
        echo Dependency installation failed, please check requirements. txt
        pause
        exit /b 1
    )
)

echo Starting Python application...
if not exist "%PYTHON_PATH%" (
    echo Error: Python executable file does not exist in %PYTHON_PATH%
    echo Please try deleting the venv folder and running the script again
    pause
    exit /b 1
)

"%PYTHON_PATH%" "%~dp0app.py"

pause
endlocal
