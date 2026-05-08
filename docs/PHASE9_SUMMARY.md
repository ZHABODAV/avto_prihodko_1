# Phase 9 Summary: Main Application Logic

## Overview
Phase 9 implements the main orchestration layer for the Terminal Optimizer system, including the [`TerminalOptimizer`](../terminal_optimizer/main.py:31) class that coordinates the entire optimization workflow and the [`SequenceEditor`](../terminal_optimizer/main.py:431) class for handling user edits to operation sequences.

## Components Implemented

### 1. TerminalOptimizer Class
**Location:** [`terminal_optimizer/main.py`](../terminal_optimizer/main.py:31)

Main orchestrator that manages the complete optimization pipeline:

#### Core Methods

- **[`load_scenario(excel_path)`](../terminal_optimizer/main.py:60)**: Load and validate scenario from Excel
  - Uses [`ExcelReader.load_all()`](../terminal_optimizer/excel_io.py) to read input data
  - Validates scenario completeness and consistency
  - Returns validated [`Scenario`](../terminal_optimizer/domain_models.py:870) object
  
- **[`generate_initial_sequence()`](../terminal_optimizer/main.py:95)**: Generate operations for all vessels
  - Processes palm vessels using [`PalmSequenceGenerator`](../terminal_optimizer/sequence_generator.py)
  - Processes sunflower vessels using [`SunflowerHandler`](../terminal_optimizer/sequence_generator.py)
  - Adds rail operations from schedule
  - Resolves timing conflicts between operations
  - Returns sorted list of operations
  
- **[`calculate_balances(operations)`](../terminal_optimizer/main.py:207)**: Simulate tank balances
  - Uses [`TankBalanceCalculator`](../terminal_optimizer/balance_calculator.py) for simulation
  - Returns balance dataframe with time-series data
  
- **[`validate_solution(operations, balances)`](../terminal_optimizer/main.py:234)**: Validate constraints
  - Uses [`ValidationEngine`](../terminal_optimizer/validation.py) for comprehensive checks
  - Returns [`ValidationResult`](../terminal_optimizer/validation.py) with errors and warnings
  - Stops pipeline if critical errors found
  
- **[`calculate_wagons(operations)`](../terminal_optimizer/main.py:275)**: Calculate wagon requirements
  - Uses [`WagonManager`](../terminal_optimizer/wagon_manager.py) for requirement calculation
  - Uses [`WagonForecaster`](../terminal_optimizer/wagon_manager.py) for availability prediction
  - Identifies gaps between supply and demand
  - Estimates costs (own wagons vs. external rental)
  - Returns comprehensive wagon analysis
  
- **[`analyze_risks(operations, wagon_analysis)`](../terminal_optimizer/main.py:324)**: Identify and assess risks
  - Identifies critical time-sensitive operations
  - Analyzes wagon shortage risks
  - Analyzes sequence feasibility risks
  - Generates prioritized recommendations
  - Returns risk report with mitigation strategies
  
- **[`export_results(output_path)`](../terminal_optimizer/main.py:388)**: Export to Excel
  - Uses [`ExcelWriter`](../terminal_optimizer/excel_io.py) to generate output workbook
  - Writes operations schedule, tank balances, wagon analysis, risk report, and validation results
  - Returns path to generated file
  
- **[`run(input_excel, output_excel)`](../terminal_optimizer/main.py:426)**: Main entry point
  - Executes complete pipeline from load to export
  - Provides execution summary with statistics
  - Handles errors gracefully with detailed logging

#### Helper Methods

- **[`_generate_rail_operations()`](../terminal_optimizer/main.py:155)**: Create operations from rail schedule
- **[`_resolve_conflicts(operations)`](../terminal_optimizer/main.py:173)**: Resolve timing conflicts on shared resources

### 2. SequenceEditor Class
**Location:** [`terminal_optimizer/main.py`](../terminal_optimizer/main.py:431)

Handles user modifications to the generated operation sequence:

#### Edit Operations

- **[`apply_swap(op_a_id, op_b_id, validate)`](../terminal_optimizer/main.py:447)**: Swap two operations
  - Exchanges start times of two operations
  - Checks for locked operations (rejects if locked)
  - Propagates timing changes to dependent operations
  - Optionally revalidates solution
  - Rolls back if validation fails
  - Returns (success, message, updated_operations)
  
- **[`apply_lock(op_id)`](../terminal_optimizer/main.py:521)**: Lock operation from changes
  - Sets [`user_locked`](../terminal_optimizer/domain_models.py:656) flag to True
  - Prevents future swaps and time adjustments
  - Returns (success, message)
  
- **[`apply_time_adjustment(op_id, new_start_time, validate)`](../terminal_optimizer/main.py:549)**: Adjust start time
  - Changes operation start time
  - Propagates to dependent operations
  - Optionally revalidates solution
  - Rolls back if validation fails
  - Returns (success, message, updated_operations)
  
- **[`recompute()`](../terminal_optimizer/main.py:631)**: Recalculate after edits
  - Recalculates tank balances
  - Revalidates solution
  - Recalculates wagon requirements
  - Re-analyzes risks
  - Returns summary of updates

#### Helper Methods

- **[`_propagate_dependencies(operation)`](../terminal_optimizer/main.py:616)**: Propagate timing changes
  - Recursively updates dependent operations
  - Ensures dependencies are satisfied

### 3. Workflow Pipeline

The complete optimization workflow:

```python
from terminal_optimizer import TerminalOptimizer

# Initialize optimizer
optimizer = TerminalOptimizer()

# Execute full pipeline
results = optimizer.run(
    input_excel="scenario_input.xlsx",
    output_excel="optimization_results.xlsx"
)

# Or run step-by-step for more control
scenario = optimizer.load_scenario("scenario_input.xlsx")
operations = optimizer.generate_initial_sequence()
balances = optimizer.calculate_balances()
validation = optimizer.validate_solution()

if not validation.has_errors():
    wagon_analysis = optimizer.calculate_wagons()
    risks = optimizer.analyze_risks()
    output_path = optimizer.export_results("results.xlsx")
```

### 4. User Edit Workflow

Example of editing the operation sequence:

```python
from terminal_optimizer import TerminalOptimizer, SequenceEditor

# Load and optimize
optimizer = TerminalOptimizer()
scenario = optimizer.load_scenario("input.xlsx")
operations = optimizer.generate_initial_sequence()
optimizer.calculate_balances()

# Create editor
editor = SequenceEditor(optimizer)

# Lock a critical operation
editor.apply_lock("OP_CRITICAL_001")

# Swap two operations
success, msg, ops = editor.apply_swap("OP_005", "OP_007")

if success:
    # Adjust timing
    from datetime import datetime
    new_time = datetime(2025, 1, 15, 10, 0)
    success, msg, ops = editor.apply_time_adjustment("OP_010", new_time)
    
    # Recompute solution
    results = editor.recompute()
    
    # Export updated results
    optimizer.export_results("updated_results.xlsx")
```

## Testing

### Test Coverage
**Location:** [`tests/test_main.py`](../tests/test_main.py)

Comprehensive test suite including:

#### Unit Tests
- TerminalOptimizer initialization and state management
- Each pipeline method with valid and invalid inputs
- Error handling for missing prerequisites
- Conflict resolution algorithm
- SequenceEditor operations (swap, lock, adjust)
- Dependency propagation logic

#### Integration Tests
- End-to-end simple workflow
- Editor workflow with multiple edits
- Validation and rollback scenarios

#### Test Statistics
- Total test cases: 30+
- Coverage areas:
  - Pipeline orchestration
  - Data validation
  - Error handling
  - Edit operations
  - Dependency management
  - Integration scenarios

## Error Handling

### Validation Checks
1. **Prerequisite Validation**: Checks for required data before each step
2. **Scenario Validation**: Validates scenario completeness and consistency
3. **Solution Validation**: Validates generated solution against all constraints
4. **Edit Validation**: Validates edits before applying (with optional rollback)

### Error Recovery
- Graceful handling of missing files
- Clear error messages for validation failures
- Automatic rollback of failed edits
- Detailed logging for debugging

## Logging

Comprehensive logging throughout the pipeline:
- INFO: Major pipeline steps and progress
- WARNING: Validation warnings and recoverable issues
- ERROR: Critical failures with stack traces
- DEBUG: Detailed operation information (conflict resolution, propagation)

## Key Features

### 1. Modular Pipeline
Each step can be run independently or as part of the complete workflow:
- Enables step-by-step debugging
- Allows custom workflows
- Supports partial re-runs

### 2. Conflict Resolution
Automatic resolution of timing conflicts:
- Groups operations by shared resource
- Detects overlaps on same resource
- Pushes conflicting operations to avoid overlaps

### 3. Dependency Propagation
Automatic propagation of timing changes:
- Maintains operation dependencies
- Recursively updates dependent operations
- Ensures timeline consistency

### 4. Edit Safety
Safe editing with validation:
- Optional validation before committing edits
- Automatic rollback on validation failure
- Lock mechanism to protect critical operations
- Complete edit history tracking

### 5. Comprehensive Analysis
Multi-dimensional analysis:
- Tank balance simulation
- Constraint validation
- Wagon requirement forecasting
- Risk identification
- Cost estimation

## Integration with Other Modules

### Dependencies
- **[`domain_models`](../terminal_optimizer/domain_models.py)**: Core data structures
- **[`excel_io`](../terminal_optimizer/excel_io.py)**: Input/output operations
- **[`sequence_generator`](../terminal_optimizer/sequence_generator.py)**: Operation generation
- **[`balance_calculator`](../terminal_optimizer/balance_calculator.py)**: Tank simulation
- **[`validation`](../terminal_optimizer/validation.py)**: Constraint checking
- **[`wagon_manager`](../terminal_optimizer/wagon_manager.py)**: Wagon logistics
- **[`risk_analysis`](../terminal_optimizer/risk_analysis.py)**: Risk assessment

### Export API
Updated [`__init__.py`](../terminal_optimizer/__init__.py:1) exports:
- [`TerminalOptimizer`](../terminal_optimizer/main.py:31)
- [`SequenceEditor`](../terminal_optimizer/main.py:431)

## Performance Considerations

### Optimization
- Operations sorted once after generation
- Efficient conflict resolution using resource grouping
- Minimal re-computation during edits

### Memory
- Lazy loading of optional components
- Balances stored as DataFrame for efficiency
- Minimal data duplication

## Future Enhancements

### Potential Improvements
1. **Multi-objective optimization**: Balance multiple objectives (cost, time, risk)
2. **What-if analysis**: Compare multiple scenarios side-by-side
3. **Undo/redo**: Stack-based edit history with undo support
4. **Batch editing**: Apply multiple edits as atomic transaction
5. **Auto-optimization**: Suggest improvements to user-edited sequences
6. **Parallel processing**: Multi-threaded scenario evaluation
7. **Incremental validation**: Validate only affected operations after edits

## Status
✅ **COMPLETE**

All components implemented and tested:
- [x] TerminalOptimizer main class
- [x] All pipeline methods
- [x] SequenceEditor class
- [x] All edit operations
- [x] Comprehensive tests
- [x] Documentation

## Usage Example

```python
from terminal_optimizer import TerminalOptimizer, SequenceEditor
from datetime import datetime

# Complete workflow
optimizer = TerminalOptimizer()

try:
    # Execute pipeline
    summary = optimizer.run(
        input_excel="data/scenario_march_2025.xlsx",
        output_excel="output/results_march_2025.xlsx"
    )
    
    print(f"✅ Optimization complete!")
    print(f"   Operations generated: {summary['operations_generated']}")
    print(f"   Warnings: {summary['validation_warnings']}")
    print(f"   Critical points: {summary['critical_points']}")
    print(f"   High risks: {summary['high_risks']}")
    print(f"   Output: {summary['output_file']}")
    
    # Interactive editing
    editor = SequenceEditor(optimizer)
    
    # Lock VIP vessel operations
    editor.apply_lock("OP_VIP_001")
    
    # Adjust timing based on user feedback
    success, msg, ops = editor.apply_time_adjustment(
        "OP_015",
        datetime(2025, 3, 10, 14, 0),
        validate=True
    )
    
    if success:
        # Recompute and export
        editor.recompute()
        optimizer.export_results("output/results_edited.xlsx")
        print("✅ Edited solution exported")
    else:
        print(f"❌ Edit failed: {msg}")
        
except ValueError as e:
    print(f"❌ Validation error: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
```

---

**Phase 9 Complete**: The Terminal Optimizer system now has a complete main application layer with full orchestration, user editing capabilities, and comprehensive testing. The system is ready for integration with a user interface or can be used programmatically for terminal operations planning.
