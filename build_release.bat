@echo off
REM ========================================
REM Terminal Optimizer - Release Builder
REM ========================================

echo.
echo ========================================
echo Terminal Optimizer - Build Release v1.0
echo ========================================
echo.

REM Create release directory
if exist "release" (
    echo Removing old release directory...
    rmdir /s /q release
)

echo Creating release directory structure...
mkdir release
mkdir release\terminal_optimizer
mkdir release\templates
mkdir release\docs
mkdir release\examples

echo.
echo [1/5] Copying Python code...
xcopy /E /I terminal_optimizer release\terminal_optimizer >nul
echo Done.

echo [2/5] Copying templates and data...
if exist "terminal_template.xlsx" (
    copy terminal_template.xlsx release\ >nul
) else (
    copy templates\terminal_template.xlsx release\ >nul
)
xcopy /E /I templates release\templates >nul
echo Done.

echo [3/5] Copying documentation...
copy README.md release\ >nul
copy QUICKSTART.md release\ >nul
copy INSTALLATION_GUIDE.md release\ >nul
copy RELEASE_NOTES.md release\ >nul
xcopy /E /I docs release\docs >nul
echo Done.

echo [4/5] Copying installation scripts...
copy requirements.txt release\ >nul
copy install.bat release\ >nul
copy run.bat release\ >nul
echo Done.

echo [5/5] Creating README for release...
(
echo ========================================
echo TERMINAL OPTIMIZER v1.0
echo ========================================
echo.
echo QUICK START:
echo 1. Run install.bat to set up Python environment
echo 2. Open terminal_template.xlsx
echo 3. Fill in your vessel data
echo 4. Save the file
echo 5. Run: run.bat terminal_template.xlsx
echo.
echo For detailed instructions, see INSTALLATION_GUIDE.md
echo For usage guide, see QUICKSTART.md
echo For release notes, see RELEASE_NOTES.md
echo.
echo Support: See docs/USER_MANUAL.md
echo ========================================
) > release\README_RELEASE.txt

echo Done.
echo.
echo ========================================
echo Release package created in: release/
echo ========================================
echo.
echo Next steps:
echo 1. Review files in release/ directory
echo 2. Test installation on clean machine
echo 3. Create ZIP archive for distribution
echo.
pause
