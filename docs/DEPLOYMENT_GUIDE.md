# Terminal Optimizer - Deployment Guide

## Overview

This guide explains how to deploy the Terminal Optimizer to end users.

## Version

**Version:** 1.0.0  
**Date:** December 2025  
**Status:** Production Ready

## Deployment Files Created

### 1. Python Environment Setup

#### `requirements.txt`

Production dependencies:

- pandas>=2.0.0
- openpyxl>=3.1.0
- pyyaml>=6.0
- numpy>=1.24.0

Development dependencies (optional):

- pytest>=7.4.0
- pytest-cov>=4.1.0

#### `pyproject.toml`

Modern Python packaging configuration following PEP 518.

- Defines project metadata
- Specifies dependencies
- Configures build system
- Sets up pytest configuration

#### `install.bat`

Windows installation script that:

1. Checks Python version (>=3.9 required)
2. Creates virtual environment
3. Installs dependencies
4. Tests module imports
5. Displays success message

### 2. Execution Scripts

#### `run.bat`

Windows execution script that:

1. Activates virtual environment
2. Validates input file
3. Runs `python -m terminal_optimizer.main`
4. Opens output file in Excel automatically
5. Displays results

Usage:

```batch
run.bat input_file.xlsx
```

#### `build_release.bat`

Creates release package by:

1. Creating `release/` directory
2. Copying all necessary files
3. Generating terminal template
4. Creating distribution structure

### 3. Error Handling System

#### `terminal_optimizer/error_messages.yaml`

Centralized error messages in Russian with error codes:

- **ERR_001-099**: File I/O errors
- **ERR_100-199**: Excel sheet errors
- **ERR_200-299**: Data validation errors
- **ERR_300-399**: Tank capacity errors
- **ERR_400-499**: Product compatibility errors
- **ERR_500-599**: Sequence generation errors
- **ERR_600-699**: Calculation errors
- **ERR_700-799**: Configuration errors
- **ERR_800-899**: Wagon manager errors
- **ERR_900-999**: Risk analysis errors
- **WARN_001+**: Warning messages
- **INFO_001+**: Info messages

#### `terminal_optimizer/logger.py`

Comprehensive logging system:

- File logging (detailed debug level)
- Console logging (info level)
- Error message lookup by code
- Custom exception classes
- Automatic log file creation with timestamps

Features:

- Logs saved to `logs/` directory
- UTF-8 encoding for Russian text
- Structured logging format
- Exception classes for each error category

### 4. Documentation

#### `README_RELEASE.txt`

User-facing documentation in Russian including:

- System requirements
- Installation instructions
- Usage guide
- Error code reference
- FAQ
- Troubleshooting

### 5. Main Application Updates

#### `terminal_optimizer/main.py`

Enhanced with:

- Integrated logging system
- Custom exception handling
- Error code usage
- Command-line interface
- Progress tracking
- User-friendly error messages

Command-line interface:

```bash
python -m terminal_optimizer.main input.xlsx [output.xlsx]
```

## Release Package Structure

```
release/
├── terminal_optimizer/           # Python source code
│   ├── __init__.py
│   ├── main.py
│   ├── excel_io.py
│   ├── sequence_generator.py
│   ├── balance_calculator.py
│   ├── critical_point.py
│   ├── risk_analysis.py
│   ├── wagon_manager.py
│   ├── validation.py
│   ├── domain_models.py
│   ├── logger.py
│   └── error_messages.yaml
├── docs/                         # Documentation
│   ├── USER_MANUAL.md
│   ├── METHODOLOGY.md
│   ├── API_REFERENCE.md
│   └── ... other docs
├── templates/                    # Configuration templates
│   ├── tank_config.csv
│   ├── product_compatibility_matrix.csv
│   └── ... other templates
├── requirements.txt              # Python dependencies
├── pyproject.toml                # Python project config
├── install.bat                   # Installation script
├── run.bat                       # Execution script
├── terminal_template.xlsx        # Excel template
└── README.txt                    # User guide
```

## Deployment Steps

### For Release Manager

1. **Build Release Package**

   ```batch
   build_release.bat
   ```

2. **Create ZIP Archive**
   - Navigate to `release/` directory
   - Select all contents
   - Create ZIP: `terminal_optimizer_v1.0.0.zip`

3. **Test on Clean Machine** (recommended)
   - Extract ZIP to clean Windows machine
   - Run `install.bat`
   - Test with sample data using `run.bat`

4. **Distribute**
   - Upload to file sharing service
   - Send to end users
   - Provide README.txt for reference

### For End Users

1. **Extract Files**
   - Unzip to desired location (e.g., `C:\TerminalOptimizer\`)

2. **Install**
   - Double-click `install.bat`
   - Follow on-screen instructions
   - Wait for "Installation completed successfully!"

3. **Run**
   - Prepare Excel file based on `terminal_template.xlsx`
   - Drag-drop Excel file onto `run.bat`
   - OR: Run `run.bat your_file.xlsx` from command line
   - Results will open automatically in Excel

4. **Check Logs**
   - Logs saved to `logs/` directory
   - Named: `terminal_optimizer_YYYYMMDD_HHMMSS.log`
   - Check for errors if problems occur

## System Requirements

### Minimum

- Windows 7 or higher
- Python 3.9+ (installed by user if not present)
- 100 MB disk space
- 2 GB RAM
- Microsoft Excel 2010+ (for viewing results)

### Recommended  

- Windows 10/11
- Python 3.11+
- 500 MB disk space
- 4 GB RAM
- Microsoft Excel 2016+

## Error Handling

### User-Visible Errors

All errors display:

1. Error code (e.g., ERR_001)
2. Russian description
3. Suggested action

### Logging

- All operations logged to file
- Console shows INFO level and above
- File contains DEBUG level for troubleshooting
- UTF-8 encoding supports Russian text

### Error Recovery

- File errors: Check file path and permissions
- Validation errors: Review input data
- Calculation errors: Check tank capacities and constraints
- See logs for detailed stack traces

## Testing Checklist

Before deployment, verify:

- [ ] `install.bat` completes successfully
- [ ] Virtual environment created in `venv/`
- [ ] All dependencies installed
- [ ] `run.bat` accepts input file
- [ ] Output file generated with `_optimized` suffix
- [ ] Results open automatically in Excel
- [ ] Logs created in `logs/` directory
- [ ] Error messages display in Russian
- [ ] Documentation is complete
- [ ] Templates included

## Troubleshooting

### Python Not Found

**Problem:** `install.bat` fails with "Python not found"  
**Solution:** Install Python 3.9+ from python.org, check "Add to PATH"

### Permission Denied

**Problem:** Cannot create files or folders  
**Solution:** Run as Administrator or move to user directory

### Module Import Errors

**Problem:** `ModuleNotFoundError` when running  
**Solution:** Rerun `install.bat` to reinstall dependencies

### Excel Not Opening

**Problem:** Output file doesn't open automatically  
**Solution:** Open manually from same directory as input, named `input_optimized.xlsx`

### Russian Text Garbled

**Problem:** Cyrillic characters display incorrectly  
**Solution:** Ensure terminal/console set to UTF-8 encoding

## Support

For issues:

1. Check `logs/` directory for error details
2. Review error code in [`error_messages.yaml`](../terminal_optimizer/error_messages.yaml)
3. Consult [`README.txt`](../README_RELEASE.txt)
4. Contact development team with log file

## Future Enhancements

Potential improvements:

- [ ] GUI application (PyQt/Tkinter)
- [ ] Web interface (Flask/FastAPI)
- [ ] Docker containerization
- [ ] Linux/Mac support
- [ ] Auto-update mechanism
- [ ] Database integration
- [ ] Report templates (PDF/Word)

## License

MIT License - See LICENSE file

## Authors

Terminal Optimizer Development Team  
December 2024
