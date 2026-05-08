# Terminal Optimizer - Release Notes

## Version 1.1 (January 9, 2026)

### New Features

#### Advanced Capabilities
- **Sequence Editor**: Manual adjustment of operation timing, swapping, and locking.
  - Allows users to fine-tune the generated schedule.
  - Supports locking operations to prevent automatic rescheduling.
  - Validates manual changes against all constraints.
- **Monte Carlo Simulation**: Probabilistic analysis of schedule robustness.
  - Runs 50 iterations with random variations in vessel ETA and flow rates.
  - Provides a Confidence Score (0.0 - 1.0) and Success Rate (%).
  - Identifies potential bottlenecks under uncertainty.

### Documentation Updates
- Updated `USER_MANUAL.md` with new features.
- Updated `API_REFERENCE.md` with `SequenceEditor` and `MonteCarloSimulator` classes.
- Updated `INSTALLATION_GUIDE.md` and `QUICKSTART_EXCEL.md`.
- Created `DOCUMENTATION_STATUS.md` registry.

---

## Version 1.0 (December 19, 2025)

### Initial Release

This is the first official release of Terminal Optimizer - a comprehensive planning tool for oil terminal operations.

### Features

#### Core Functionality
- **Tank Management**: Full support for РВС 1-5 and ШТ (shore tank)
  - Real-time capacity tracking
  - Product compatibility checking
  - Automatic cleaning requirement detection
  
- **Sequence Generation**: Intelligent operation planning
  - Palm oil discharge (8 fractions support)
  - Sunflower oil loading
  - Automatic tank allocation
  - Conflict resolution
  
- **Balance Calculation**: Hour-by-hour tank level simulation
  - Capacity constraint validation
  - Overfill detection
  - Product segregation enforcement
  
- **Wagon Management**: Railway logistics optimization
  - Batch scheduling (4 batches/day limit)
  - Looping logic (sunflower → palm transformation)
  - External wagon ordering recommendations
  
- **Risk Analysis**: Proactive risk identification
  - Markov chain-based wagon availability forecast
  - Tank overflow risk detection
  - Critical path analysis
  - ROI-based recommendations

#### Supported Operations
- Vessel berthing and unberthing
- Ship discharge via Line1 (900 t/h) and Line2 (500 t/h)
- Ship loading with optional direct rail variant
- Tank-to-tank transfers
- Rail wagon operations
- Tank cleaning between incompatible products
- Product quality analysis

### Technical Specifications

####Components
- **Domain Models**: Tank, Vessel, Operation, Scenario classes
- **Sequence Generator**: Palm and Sunflower handlers with conflict resolution
- **Balance Calculator**: Discrete-time simulation engine
- **Validation Engine**: Multi-level constraint checking
- **Wagon Manager**: Looping logic with external order calculation
- **Risk Analyzer**: Markov forecasting with recommendation generation
- **Excel I/O**: Full integration with Excel templates

#### Test Coverage
- **382 automated tests** covering all components
- **Unit tests**: 300+ test cases
- **Integration tests**: 20+ end-to-end scenarios
- **Edge case tests**: 40+ boundary conditions
- **Performance tests**: 15+ benchmarks

#### Performance
- Small scenarios (7 days, 2 vessels): < 10 seconds
- Medium scenarios (14 days, 5 vessels): < 30 seconds
- Large scenarios (30 days, 10 vessels): < 2 minutes
- Memory usage: < 1GB for all tested scenarios

### System Requirements

- **OS**: Windows 10 or later
- **Python**: 3.9+
- **Excel**: 2016 or later
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 500MB free space

### Known Limitations

1. **Excel-Only Interface**: No web interface in this version
2. **Windows-Only**: Not tested on Linux/Mac
3. **Single-Site**: Configured for one terminal location
4. **Manual Execution**: No automated scheduling system

### Installation

See `INSTALLATION_GUIDE.md` for detailed instructions.

Quick install:
1. Run `install.bat`
2. Wait for completion
3. Done!

### Usage

See `QUICKSTART.md` and `docs/USER_MANUAL.md` for usage instructions.

Quick start:
1. Open `terminal_template.xlsx`
2. Fill vessel data in Input_Vessels sheet
3. Run: `run.bat terminal_template.xlsx`
4. Review results in output sheets

### Files Included

```
TerminalOptimizer_v1.0/
├── terminal_optimizer/       (Python package - 6,000+ lines)
│   ├── main.py              (Main application)
│   ├── domain_models.py     (Core classes)
│   ├── sequence_generator.py (Sequence planning)
│   ├── balance_calculator.py (Tank simulation)
│   ├── wagon_manager.py     (Railway logistics)
│   ├── validation.py        (Constraint checking)
│   ├── risk_analysis.py     (Risk forecasting)
│   └── excel_io.py          (Excel integration)
├── docs/                    (Documentation)
│   ├── USER_MANUAL.md       (User guide)
│   ├── METHODOLOGY.md       (Mathematical model)
│   ├── ARCHITECTURE.md      (System design)
│   └── API_REFERENCE.md     (Technical reference)
├── templates/               (Reference data)
│   ├── tank_config.csv
│   ├── product_compatibility_matrix.csv
│   └── operation_time_standards.csv
├── terminal_template.xlsx   (Main Excel template)
├── install.bat              (Installation script)
├── run.bat                  (Execution script)
├── requirements.txt         (Python dependencies)
└── README_RELEASE.txt       (Quick reference)
```

### Bug Fixes

N/A - Initial release

### Improvements

N/A - Initial release

### Breaking Changes

N/A - Initial release

### Migration Guide

N/A - Initial release

### Roadmap for v2.0

Planned features for future versions:
- Web-based interface
- Multi-site support
- Mobile app for field checking
- Stage I optimization solver
- Multi-scenario comparison

### Support

For issues and questions:
1. Check `docs/USER_MANUAL.md`
2. Review `INSTALLATION_GUIDE.md`
3. Check log files in `logs/` directory
4. Contact technical support

### Credits

Developed for oil terminal operations planning.

### License

Proprietary - All rights reserved.

---
