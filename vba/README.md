# VBA Modules for Terminal Optimizer

This directory contains VBA code modules that power the Excel user interface for Terminal Optimizer.

## Files

### MainInterface.bas

Main module containing all user-facing functionality:

- `RunCalculation()` - Execute optimization calculation
- `ClearOutputs()` - Clear all output sheets
- `ExportToPDF()` - Export results to PDF
- `ShowHelp()` - Display help instructions
- Helper functions for Python integration and validation

### ProgressForm.frm

UserForm for displaying progress during calculation:

- Progress bar visualization
- Status message updates
- Percentage display

### RibbonCallbacks.bas (Optional)

Callback functions for custom ribbon buttons if you set up a custom ribbon tab.

## Installation Instructions

### Method 1: Manual Import (Recommended)

1. Open `terminal_template.xlsx` in Excel
2. Press `Alt + F11` to open VBA Editor
3. In VBA Editor: `File` → `Import File...`
4. Select `MainInterface.bas` and click Open
5. Repeat for any other .bas or .frm files

### Method 2: Copy-Paste Code

1. Open VBA Editor (`Alt + F11`)
2. Insert new module: `Insert` → `Module`
3. Open `MainInterface.bas` in a text editor
4. Copy all code (skip the `Attribute VB_Name` line)
5. Paste into the VBA module
6. Rename module to "MainInterface" in Properties window

### Creating the Progress Form

1. In VBA Editor: `Insert` → `UserForm`
2. Rename to "ProgressForm" in Properties window
3. Add controls:
   - **StatusLabel** (Label): Position at top, width 300
   - **PercentLabel** (Label): Position at top-right
   - **ProgressBarBackground** (Frame):
     - Width: 300, Height: 20
     - BackColor: Light Gray
     - BorderStyle: 1 - fmBorderStyleSingle
   - **ProgressBar** (Frame):
     - Position inside ProgressBarBackground
     - Left: 0, Top: 0, Height: 20, Width: 0
     - BackColor: Green
     - BorderStyle: 0 - fmBorderStyleNone

4. Double-click the UserForm and paste the code from `ProgressForm.frm`

## Setting Up Ribbon Buttons

### Quick Method: Quick Access Toolbar

1. Right-click on Quick Access Toolbar
2. Select "Customize Quick Access Toolbar..."
3. Choose "Macros" from dropdown
4. Add these macros:
   - `MainInterface.RunCalculation`
   - `MainInterface.ClearOutputs`
   - `MainInterface.ExportToPDF`
   - `MainInterface.ShowHelp`
5. Click OK

### Advanced Method: Custom Ribbon Tab

Requires **Office RibbonX Editor** (free tool):

1. Download RibbonX Editor from <https://github.com/fernandreu/office-ribbonx-editor>
2. Close Excel file
3. Open `terminal_template.xlsx` in RibbonX Editor
4. Insert → Office 2010+ Custom UI Part
5. Paste the customUI XML (see EXCEL_TEMPLATE_GUIDE.md)
6. Save and close
7. Add RibbonCallbacks module to VBA

## Configuration

### Python Path

By default, the VBA code looks for Python in the system PATH. If you need to specify a custom Python path:

Edit `MainInterface.bas`:

```vba
' In RunPythonScript function, change:
cmd = "python """ & scriptPath & """ ..."

' To:
cmd = """C:\Python38\python.exe"" """ & scriptPath & """ ..."
```

### Script Location

The script is located relative to the Excel workbook. Default location:

```
workbook_directory\terminal_optimizer\main.py
```

If your structure is different, edit the `GetScriptPath()` function.

## Testing

### Test Python Integration

1. Open VBA Editor
2. Press `Ctrl + G` to open Immediate Window
3. Type and execute:

   ```vba
   ? MainInterface.CheckPythonInstallation()
   ```

4. Should return `True` if Python is found

### Test Main Calculation

1. Fill in sample data on Input sheets
2. Run `MainInterface.RunCalculation` from Immediate Window or click button
3. Check for errors in `calculation_log.txt`

## Troubleshooting

### "Compile Error: User-defined type not defined"

**Solution**: Enable references:

1. Tools → References
2. Check:
   - Microsoft Scripting Runtime
   - Microsoft Shell Controls and Automation
   - Windows Script Host Object Model

### "Python not found"

**Solutions**:

1. Install Python 3.8+ from python.org
2. During installation, check "Add Python to PATH"
3. Restart Excel
4. Or specify full Python path (see Configuration above)

### "Permission denied" when running script

**Solutions**:

1. Run Excel as Administrator
2. Check file permissions on project folder
3. Disable antivirus temporarily

### Progress form doesn't show

**Solution**: Make sure ProgressForm is created correctly:

1. Check UserForm name is exactly "ProgressForm"
2. Verify all controls exist (StatusLabel, PercentLabel, etc.)
3. Check control names exactly match code

### Macros are disabled

**Solutions**:

1. File → Options → Trust Center → Trust Center Settings
2. Macro Settings → Enable all macros (or "with notification")
3. Check "Trust access to VBA project object model"
4. Restart Excel

## Security Notes

- Always enable macros ONLY for trusted files
- Review VBA code before enabling
- Keep backups before running calculations
- The VBA code does NOT modify input data (only output sheets)

## Updating VBA Code

To update after changes:

1. Export current module: Right-click module → Export File
2. Make changes in text editor
3. Delete old module in VBA Editor
4. Import updated .bas file

## Dependencies

VBA code requires:

- Excel 2016 or later (tested on 2016, 2019, 365)
- Windows OS (uses WScript.Shell)
- Python 3.8+ installed
- terminal_optimizer package in accessible location

## Support

For issues with:

- **VBA code**: Check VBA Editor debug info
- **Python integration**: Check `calculation_log.txt`
- **Data validation**: See EXCEL_TEMPLATE_GUIDE.md
- **Template structure**: See create_excel_template.py

## Version History

- **v1.0** (2025-12-19): Initial VBA implementation
  - Basic calculation runner
  - Progress tracking
  - PDF export
  - Input validation

## License

Part of Terminal Optimizer project.

---

**Tip**: Press F1 in VBA Editor for Excel VBA help documentation.
