@echo off
REM ========================================
REM Terminal Optimizer Execution Script
REM ========================================

echo.
echo ========================================
echo Terminal Optimizer - Running
echo ========================================
echo.

REM Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found.
    echo.
    echo Please run install.bat first to set up the environment.
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Check if Excel file is provided as argument
set "TARGET_FILE=%~1"
if "%TARGET_FILE%"=="" (
    if exist "terminal_template.xlsx" (
        echo No file specified. Defaulting to terminal_template.xlsx
        set "TARGET_FILE=terminal_template.xlsx"
    ) else if exist "templates\terminal_template.xlsx" (
        echo No file specified. Defaulting to templates\terminal_template.xlsx
        set "TARGET_FILE=templates\terminal_template.xlsx"
    ) else (
        echo ERROR: No Excel file specified and default template not found.
        echo.
        echo Usage: run.bat [path_to_excel_file]
        echo Example: run.bat terminal_template.xlsx
        echo.
        pause
        exit /b 1
    )
)

REM Check if file exists
if not exist "%TARGET_FILE%" (
    echo ERROR: File not found: %TARGET_FILE%
    echo.
    pause
    exit /b 1
)

REM Get full path and filename
for %%I in ("%TARGET_FILE%") do (
    set "INPUT_FILE=%%~fI"
    set "INPUT_DIR=%%~dpI"
    set "INPUT_NAME=%%~nI"
)
set OUTPUT_FILE=%INPUT_DIR%%INPUT_NAME%_optimized.xlsx

echo Input file: %INPUT_FILE%
echo Output file: %OUTPUT_FILE%
echo.

REM Run the optimizer
echo Running Terminal Optimizer...
echo.
python -m terminal_optimizer.main "%INPUT_FILE%"

if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo ERROR: Optimization failed!
    echo ========================================
    echo.
    echo Check the log file for details.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Optimization completed successfully!
echo ========================================
echo.
echo Output saved to: %OUTPUT_FILE%
echo.

REM Try to open the output file in Excel
if exist "%OUTPUT_FILE%" (
    echo Opening output file in Excel...
    start "" "%OUTPUT_FILE%"
) else (
    echo Warning: Output file not found at expected location.
)

echo.
pause
