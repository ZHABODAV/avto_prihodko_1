@echo off
REM ========================================
REM Terminal Optimizer Installation Script
REM ========================================

echo.
echo ========================================
echo Terminal Optimizer - Installation
echo ========================================
echo.

REM Check if Python is installed
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo.
    echo Please install Python 3.9 or higher from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

REM Check Python version
echo Python found. Checking version...
python -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"
if %errorlevel% neq 0 (
    echo ERROR: Python 3.9 or higher is required.
    echo.
    python --version
    echo.
    echo Please install Python 3.9+ from https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

python --version
echo Python version OK!
echo.

REM Create virtual environment
echo [2/5] Creating virtual environment...
if exist ".venv" (
    echo Virtual environment already exists. Removing old one...
    rmdir /s /q .venv
)

python -m venv .venv
if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment.
    echo.
    pause
    exit /b 1
)
echo Virtual environment created successfully!
echo.

REM Activate virtual environment
echo [3/5] Activating virtual environment...
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment.
    echo.
    pause
    exit /b 1
)
echo Virtual environment activated!
echo.

REM Upgrade pip
echo [4/5] Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1
echo pip upgraded!
echo.

REM Install dependencies
echo [5/5] Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies.
    echo.
    pause
    exit /b 1
)
echo.

REM Test imports
echo Testing module imports...
python -c "import pandas; import openpyxl; import yaml; import numpy; print('All modules imported successfully!')"
if %errorlevel% neq 0 (
    echo ERROR: Module import test failed.
    echo.
    pause
    exit /b 1
)
echo.

REM Success message
echo ========================================
echo Installation completed successfully!
echo ========================================
echo.
echo Virtual environment: .venv\
echo Python: 
python --version
echo.
echo Installed packages:
pip list | findstr /i "pandas openpyxl pyyaml numpy"
echo.
echo To run the optimizer, use: run.bat
echo.
pause
