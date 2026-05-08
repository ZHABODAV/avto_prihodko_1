# Terminal Optimizer

Oil Terminal Operations Planning System for optimizing tank management, vessel cargo operations, and railway wagon logistics.

## Overview

Terminal Optimizer is a comprehensive planning tool designed for oil terminal operations that handle:
- **Sunflower oil** exports via ship loading
- **Palm oil fractions** (up to 8 types) imports via ship discharge

The system generates optimal operational sequences, calculates tank balances, manages railway wagon logistics, and provides risk analysis with cost optimization.

## Features

### Core Functionality
- **Tank Management**: RVS 1-5 and SHT (shore tank) capacity tracking with product compatibility
- **Sequence Generation**: Automatic operational sequence planning for vessel cargo operations
- **Balance Calculation**: Hourly tank balance simulation with constraint validation
- **Wagon Management**: Railway wagon scheduling with looping logic (sunflower discharge → palm loading)
- **Risk Analysis**: Markov chain-based wagon availability forecasting and risk identification

### Advanced Capabilities
- **Sequence Editor**: Manual adjustment of operation timing, swapping, and locking
- **Monte Carlo Simulation**: Probabilistic analysis of schedule robustness (confidence scores)
- **Excel Integration**: Seamless data loading and result export to formatted Excel reports

### Supported Operations
- Vessel berthing and unberthing
- Ship discharge (palm fractions) via Line1/Line2
- Ship loading (sunflower) with direct rail variant
- Tank-to-tank transfers
- Rail wagon discharge and loading
- Tank cleaning between incompatible products

## Project Structure

```
terminal_optimizer/
├── terminal_optimizer/           # Main Python package
│   ├── __init__.py
│   ├── domain_models.py          # Tank, Vessel, Operation, Scenario classes
│   ├── sequence_generator.py     # Palm and Sunflower sequence logic
│   ├── balance_calculator.py     # Tank balance simulation
│   ├── wagon_manager.py          # Wagon calculation and looping
│   ├── validation.py             # Constraint validation engine
│   ├── risk_analysis.py          # Markov forecasting and risk identification
│   ├── monte_carlo.py            # Simulation engine
│   ├── excel_io.py               # Excel reader and writer
│   ├── config.py                 # Configuration and constants
│   └── main.py                   # Main application entry point
├── templates/                    # Reference data and Excel templates
│   └── terminal_template.xlsx
├── docs/                         # Documentation
│   ├── USER_MANUAL.md
│   ├── METHODOLOGY.md
│   ├── ARCHITECTURE.md
│   ├── API_REFERENCE.md
│   └── DOCUMENTATION_STATUS.md
├── tests/                        # Unit and integration tests
├── requirements.txt
├── install.bat                   # Windows installation script
└── run.bat                       # Windows execution script
```

## Installation

### Prerequisites
- Python 3.9 or higher
- Microsoft Excel 2016 or later (for template usage)

### Quick Setup (Windows)

1. Clone or download the repository
2. Run the installation script:
   ```cmd
   install.bat
   ```
3. This will:
   - Create a virtual environment
   - Install required dependencies
   - Verify the installation

### Manual Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Quick Start

1. Open `templates/terminal_template.xlsx`
2. Fill in the input sheets:
   - **Input_Vessels**: Vessel schedule and cargo plans
   - **Input_CurrentState**: Current tank inventory
   - **Input_Rail**: Railway delivery schedule
   - **Input_Demand**: Client demand matrix
3. Run the optimizer via the provided batch script or command line
4. Review outputs in the generated Excel file

### Command Line

```bash
# Basic usage
python -m terminal_optimizer.main input_data.xlsx

# Specify output file
python -m terminal_optimizer.main input_data.xlsx output_results.xlsx

# Run with Monte Carlo simulation
python -m terminal_optimizer.main input_data.xlsx --simulate
```

### Python API

```python
from terminal_optimizer.main import TerminalOptimizer

optimizer = TerminalOptimizer()
summary = optimizer.run("input_data.xlsx", "output_results.xlsx", run_simulation=True)

print(f"Optimization complete. Status: {summary['status']}")
```

## Tank Configuration

| Tank | Capacity (t) | Allowed Products | Notes |
|------|-------------|------------------|-------|
| RVS-1 | 9,900 | Sunflower | Dedicated sunflower |
| RVS-2 | 9,900 | Sunflower | Dedicated sunflower |
| RVS-3 | 9,900 | Palm fractions | Dedicated palm |
| RVS-5 | 2,700 | Sunflower, Palm | Swing tank (requires cleaning) |
| SHT | 2,700 | Palm fractions | Shore tank for small fractions |

## Key Constraints

- **Railway Batches**: Maximum 4 batches per day (18 wagons each, 72 wagons total)
- **Product Compatibility**: Cleaning required when switching between sunflower and palm (48-72 hours)
- **Parallel Lines**: Palm discharge can use Line1 (900 t/h) and Line2 (500 t/h) simultaneously
- **SHT Mutex**: Cannot fill and discharge SHT simultaneously

## Documentation

- [User Manual](docs/USER_MANUAL.md) - Complete usage guide
- [Methodology](docs/METHODOLOGY.md) - Mathematical model and algorithms
- [Architecture](docs/ARCHITECTURE.md) - System design and module descriptions
- [API Reference](docs/API_REFERENCE.md) - Python API documentation
- [Documentation Status](docs/DOCUMENTATION_STATUS.md) - Current status of project docs

## Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=terminal_optimizer --cov-report=html
```

## License

Proprietary - All rights reserved.

## Support

For issues and feature requests, please contact the development team.
