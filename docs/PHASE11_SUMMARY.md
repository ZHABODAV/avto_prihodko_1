# Phase 11: Sequence Optimization & Strict Segregation

## Objectives
1.  **Strict Cargo Segregation**: Implement strict cleaning logic for pipelines (`Line1`, `Line2`) to prevent cominglement of incompatible palm fractions.
2.  **Sequence Optimization**: Develop an optimizer to reorder vessels within their respective queues to minimize total costs (demurrage + cleaning downtime).
3.  **Berth Separation**: Model independent berths for Palm and Sunflower operations to allow simultaneous processing.
4.  **Operational Patterns**: Enable scenario filtering to run simulations for specific subsets of vessels (e.g., "Only Sunflower", "Only Palm").

## Completed Tasks

### 1. Domain Models & Constants
- [x] Defined `BERTH_PALM` and `BERTH_SUNFLOWER` resources in `constants.py`.
- [x] Defined line cleaning durations (`CLEANING_LINE_DEFAULT`, etc.) in `constants.py`.
- [x] Updated `domain_models.py` to handle case-insensitive product checks for cleaning logic.

### 2. Sequence Generation & Berth Logic
- [x] Updated `PalmSequenceGenerator` to use `BERTH_PALM`.
- [x] Updated `SunflowerHandler` to use `BERTH_SUNFLOWER`.
- [x] Implemented line cleaning logic in `PalmSequenceGenerator` (tracking `Line1`/`Line2` state).
- [x] Updated `SequenceCoordinator` to handle separate berth conflicts and propagate delays to dependent operations.

### 3. Sequence Optimizer
- [x] Created `SequenceOptimizer` class in `terminal_optimizer/sequence_optimizer.py`.
- [x] Implemented permutation (small N) and greedy (large N) algorithms for vessel reordering.
- [x] Defined cost function (Duration + Demurrage + Cleaning).

### 4. Integration & Filtering
- [x] Added `--mode` argument to CLI (`all`, `palm_only`, `sunflower_only`).
- [x] Added `--optimize` argument to CLI.
- [x] Added `--vessel <id>` argument for single-vessel simulation.
- [x] Implemented per-vessel filtering via "Active" column in `Input_Vessels`.
- [x] Updated `TerminalOptimizer.run` and `generate_initial_sequence` to support filtering and optimization.

### 5. Validation
- [x] Added `validate_line_cleaning` to `terminal_optimizer/validation.py`.
- [x] Updated `validate_resource_exclusivity` to respect separate berths.

### 6. Frontend & Documentation
- [x] Updated `vba/MainInterface.bas` to read settings from "Settings" sheet and pass arguments to Python.
- [x] Updated `create_excel_template.py` to include the "Settings" sheet.
- [x] Updated `docs/USER_MANUAL.md` with instructions for new features.

## Usage

### Running with Operational Patterns
To run the simulation for a specific cargo type:
```bash
python -m terminal_optimizer.main input.xlsx output.xlsx --mode palm_only
python -m terminal_optimizer.main input.xlsx output.xlsx --mode sunflower_only
```

### Optimizing Sequence
To automatically reorder vessels to minimize costs:
```bash
python -m terminal_optimizer.main input.xlsx output.xlsx --optimize
```

### Single Vessel Simulation
To run the simulation for a specific vessel:
```bash
python -m terminal_optimizer.main input.xlsx output.xlsx --vessel "MV-PALMOIL1"
```
