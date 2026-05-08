# Terminal Optimizer - Installation Guide

## System Requirements

### Minimum Requirements
- **Operating System:** Windows 10 or later
- **Python:** 3.9 or higher
- **Excel:** Microsoft Excel 2016 or later
- **RAM:** 4GB minimum, 8GB recommended
- **Disk Space:** 500MB free space

### Software Dependencies
- Python packages (automatically installed):
  - pandas >= 2.0.0
  - openpyxl >= 3.1.0
  - pyyaml >= 6.0
  - numpy >= 1.24.0

## Installation Steps

### Step 1: Check Python Installation

1. Open Command Prompt (Win + R, type `cmd`, press Enter)
2. Type: `python --version`
3. You should see: `Python 3.x.x` where x >= 9

#### If Python is NOT installed:

1. Download Python from: https://www.python.org/downloads/
2. **IMPORTANT:** During installation, CHECK the box "Add Python to PATH"
3. Choose "Install Now"
4. Restart your computer after installation

### Step 2: Extract Terminal Optimizer

1. Extract the ZIP file to your desired location
2. Example: `C:\TerminalOptimizer\`
3. Folder structure should look like:
   ```
   TerminalOptimizer/
   ├── terminal_optimizer/    (Python code)
   ├── docs/                  (Documentation)
   ├── templates/             (Reference data)
   ├── terminal_template.xlsx (Main Excel file)
   ├── install.bat            (Installation script)
   ├── run.bat                (Execution script)
   └── README_RELEASE.txt     (Quick start)
   ```

### Step 3: Run Installation Script

1. Open the extracted folder
2. **Right-click** on `install.bat`
3. Select **"Run as Administrator"**
4. Wait for the installation to complete (2-5 minutes)
5. You should see "Installation completed successfully!"

#### What the install script does:
- Creates a Python virtual environment
- Installs all required dependencies
- Tests that all modules can be imported
- Verifies the installation

### Step 4: Verify Installation

1. In the installation folder, you should see a new `venv` folder
2. The installation script shows a list of installed packages
3. If you see errors, check the Troubleshooting section below

## Quick Test

1. Open `terminal_template.xlsx`
2. The template should open in Excel without errors
3. You should see input sheets (Input_Vessels, Input_CurrentState, etc.)

## Troubleshooting

### Problem: "Python is not recognized"

**Solution:**
1. Python is not in your PATH
2. Reinstall Python and CHECK "Add Python to PATH"
3. OR manually add Python to PATH:
   - Right-click "This PC" → Properties
   - Advanced system settings → Environment Variables
   - Edit PATH, add Python installation directory

### Problem: "install.bat failed"

**Solution:**
1. Run Command Prompt as Administrator
2. Navigate to the folder: `cd C:\TerminalOptimizer`
3. Run manually: `python -m venv venv`
4. Then: `venv\Scripts\activate`
5. Then: `pip install -r requirements.txt`

### Problem: "Module import test failed"

**Solution:**
1. Delete the `venv` folder
2. Run `install.bat` again
3. If still fails, check internet connection (pip needs to download packages)

### Problem: Excel shows errors when opening template

**Solution:**
1. Enable macros in Excel:
   - File → Options → Trust Center → Trust Center Settings
   - Macro Settings → Enable all macros
2. Check Excel version (must be 2016 or later)

## Updating

To update to a new version:

1. Extract new version to a different folder
2. Copy your data files to the new folder
3. Run `install.bat` in the new folder

## Uninstalling

To remove Terminal Optimizer:

1. Simply delete the installation folder
2. No registry entries or system files are created

## Next Steps

After successful installation:
1. Read `QUICKSTART.md` for usage instructions
2. Review `docs/USER_MANUAL.md` for detailed documentation
3. Check `examples/` folder for sample scenarios

## Support

If you encounter issues not covered here:
1. Check `docs/USER_MANUAL.md` → Troubleshooting section
2. Review log files in `logs/` directory
3. Contact technical support with:
   - Your Python version
   - Error messages
   - Log files

---

**Installation Guide v1.1**
Last Updated: January 9, 2026
