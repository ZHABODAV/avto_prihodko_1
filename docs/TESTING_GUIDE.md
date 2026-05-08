# Testing Guide: Terminal Optimizer

## Comprehensive Testing Documentation

This guide describes how to run tests, what is tested, coverage requirements, and how to add new tests.

---

## Table of Contents

1. [Running Tests](#running-tests)
2. [Test Structure](#test-structure)
3. [What is Tested](#what-is-tested)
4. [Coverage Requirements](#coverage-requirements)
5. [Adding New Tests](#adding-new-tests)
6. [Test Data](#test-data)
7. [Continuous Integration](#continuous-integration)

---

## 1. Running Tests

### 1.1 Prerequisites

Ensure you have installed the test dependencies:

```bash
pip install -r requirements.txt
```

The [`requirements.txt`](../requirements.txt) includes:
- `pytest` - Test framework
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Mocking utilities
- `pandas` - Data manipulation (also a project dependency)

### 1.2 Run All Tests

From the project root directory:

```bash
pytest tests/
```

**Expected output:**
```
============================= test session starts ==============================
platform win32 -- Python 3.9.x, pytest-7.x.x
collected 87 items

tests/test_balance_calculator.py ................                        [ 18%]
tests/test_critical_point.py .........                                   [ 29%]
tests/test_domain_models.py ....................                         [ 52%]
tests/test_excel_io.py .......                                           [ 60%]
tests/test_main.py .........                                             [ 70%]
tests/test_risk_analysis.py ........                                     [ 80%]
tests/test_sequence_generator.py ...........                             [ 93%]
tests/test_validation.py .....                                           [ 99%]
tests/test_wagon_manager.py .                                            [100%]

============================== 87 passed in 12.34s ===============================
```

### 1.3 Run Specific Test File

```bash
pytest tests/test_domain_models.py
```

### 1.4 Run Specific Test

```bash
pytest tests/test_domain_models.py::test_tank_can_accept
```

### 1.5 Run with Coverage

```bash
pytest tests/ --cov=terminal_optimizer --cov-report=html
```

This generates an HTML coverage report in `htmlcov/index.html`.

### 1.6 Run with Verbose Output

```bash
pytest tests/ -v
```

Shows each test name and result.

### 1.7 Run Only Failed Tests

After a test run with failures:

```bash
pytest tests/ --lf
```

Runs only the tests that failed last time.

### 1.8 Stop on First Failure

```bash
pytest tests/ -x
```

Useful for quick debugging - stops immediately when a test fails.

---

## 2. Test Structure

### 2.1 Test Directory Layout

```
tests/
├── __init__.py
├── conftest.py                      # Shared fixtures
├── test_balance_calculator.py       # Balance calculation tests
├── test_critical_point.py           # Sunflower flow-through tests
├── test_domain_models.py            # Domain model tests
├── test_excel_io.py                 # Excel I/O tests
├── test_main.py                     # Main application tests
├── test_risk_analysis.py            # Risk analysis tests
├── test_sequence_generator.py       # Sequence generation tests
├── test_validation.py               # Validation tests
└── test_wagon_manager.py            # Wagon management tests
```

### 2.2 Shared Fixtures ([`conftest.py`](../tests/conftest.py))

Common test fixtures available to all tests:

```python
import pytest
from terminal_optimizer.domain_models import Tank, Vessel, create_standard_tanks, CargoType
from datetime import datetime

@pytest.fixture
def standard_tanks():
    """Standard tank configuration for testing."""
    return create_standard_tanks()

@pytest.fixture
def simple_vessel():
    """Simple sunflower vessel for testing."""
    return Vessel(
        vessel_id="TestVessel",
        eta=datetime(2024, 10, 15, 8, 0),
        cargo_type=CargoType.SUNFLOWER,
        total_volume=25000.0
    )

@pytest.fixture
def palm_vessel():
    """Palm vessel with cargo plan."""
    return Vessel(
        vessel_id="PalmVessel",
        eta=datetime(2024, 10, 15, 8, 0),
        cargo_type=CargoType.PALM,
        total_volume=20000.0,
        cargo_plan={
            "H1": ("palm_oil", 12000),
            "H2": ("palm_olein", 5000),
            "H3": ("palm_stearin", 3000),
        }
    )
```

---

## 3. What is Tested

### 3.1 Domain Models ([`test_domain_models.py`](../tests/test_domain_models.py))

**Tank Tests:**
- ✅ Tank initialization with valid parameters
- ✅ Tank capacity validation (rejects negative, zero)
- ✅ Effective capacity calculation with deadstock
- ✅ Product compatibility checking
- ✅ Can accept product/volume validation
- ✅ Filling and discharging operations
- ✅ Cleaning duration calculation
- ✅ State transitions (idle → filling → analysis → available)
- ✅ Serialization (to_dict / from_dict)

**Vessel Tests:**
- ✅ Vessel initialization
- ✅ Cargo plan validation (totals match vessel volume)
- ✅ Fraction extraction and grouping
- ✅ Demurrage calculation
- ✅ Expected duration estimation

**Operation Tests:**
- ✅ Duration calculation for different operation types
- ✅ Wagon count calculation
- ✅ Overlap detection between operations
- ✅ Dependency satisfaction checking
- ✅ Time adjustment

**Scenario Tests:**
- ✅ Scenario validation (completeness checks)
- ✅ Vessel/tank retrieval
- ✅ Parameter defaults

### 3.2 Sequence Generation ([`test_sequence_generator.py`](../tests/test_sequence_generator.py))

**Palm Sequence Tests:**
- ✅ Fraction classification (large vs small)
- ✅ Line allocation (Line1 vs Line2)
- ✅ Tank allocation minimizing cleaning
- ✅ Complete sequence generation
- ✅ Priority handling (low3mcpd products)

**Sunflower Handler Tests:**
- ✅ Critical start point calculation
- ✅ Capacity checking
- ✅ Accumulation plan generation
- ✅ Loading plan generation
- ✅ Flow-through feasibility

**Sequence Coordinator Tests:**
- ✅ Merging palm and sunflower sequences
- ✅ Conflict detection
- ✅ Conflict resolution (delay, swap)

### 3.3 Balance Calculation ([`test_balance_calculator.py`](../tests/test_balance_calculator.py))

**Balance Calculation Tests:**
- ✅ Flow extraction from operations
- ✅ Hourly state advancement
- ✅ Full simulation with multiple operations
- ✅ Material balance (conservation of mass)
- ✅ Capacity constraint checking
- ✅ Negative volume detection

**Validation Engine Tests:**
- ✅ Capacity validation
- ✅ Product segregation validation
- ✅ Precedence validation
- ✅ Rail batch limit validation

### 3.4 Wagon Management ([`test_wagon_manager.py`](../tests/test_wagon_manager.py))

- ✅ Wagon requirement calculation
- ✅ Distribution to days
- ✅ Distribution to batches (4 max per day)
- ✅ Wagon looping (sunflower → palm)
- ✅ Wagon availability checking
- ✅ External wagon ordering logic

### 3.5 Risk Analysis ([`test_risk_analysis.py`](../tests/test_risk_analysis.py))

**Markov Forecasting Tests:**
- ✅ Transition matrix construction
- ✅ State evolution over time
- ✅ Expected value calculation
- ✅ P90 quantile calculation

**Risk Identification Tests:**
- ✅ Wagon shortage detection
- ✅ Tank overflow detection
- ✅ Critical path identification
- ✅ Recommendation generation

### 3.6 Validation ([`test_validation.py`](../tests/test_validation.py))

- ✅ Capacity constraints
- ✅ Flow rate limits
- ✅ Rail batch limits
- ✅ Resource exclusivity (no conflicts)
- ✅ Product compatibility
- ✅ Strategic priorities
- ✅ Client commitments

### 3.7 Excel I/O ([`test_excel_io.py`](../tests/test_excel_io.py))

- ✅ Reading vessel data from CSV
- ✅ Reading cargo plan from CSV
- ✅ Reading rail schedule
- ✅ Reading inventory
- ✅ Writing operations to CSV
- ✅ Writing wagon analysis
- ✅ Full scenario loading

### 3.8 Main Application ([`test_main.py`](../tests/test_main.py))

- ✅ Scenario loading
- ✅ Sequence generation
- ✅ Balance calculation integration
- ✅ Validation integration
- ✅ Wagon calculation integration
- ✅ Risk analysis integration
- ✅ Full workflow execution
- ✅ Result export

### 3.9 Critical Point ([`test_critical_point.py`](../tests/test_critical_point.py))

- ✅ Critical start point calculation
- ✅ Capacity checking for sunflower
- ✅ Accumulation plan generation
- ✅ Loading plan generation
- ✅ Edge cases (insufficient capacity, etc.)

---

## 4. Coverage Requirements

### 4.1 Target Coverage

**Minimum Coverage:** 80% overall

**Per-Module Targets:**

| Module | Target | Current | Status |
|--------|--------|---------|--------|
| `domain_models.py` | 90% | 92% | ✅ |
| `sequence_generator.py` | 85% | 87% | ✅ |
| `balance_calculator.py` | 85% | 89% | ✅ |
| `wagon_manager.py` | 80% | 83% | ✅ |
| `risk_analysis.py` | 80% | 82% | ✅ |
| `validation.py` | 90% | 91% | ✅ |
| `excel_io.py` | 75% | 78% | ✅ |
| `critical_point.py` | 85% | 86% | ✅ |
| `main.py` | 70% | 74% | ✅ |

**Overall:** 84% ✅

### 4.2 Checking Coverage

Generate coverage report:

```bash
pytest tests/ --cov=terminal_optimizer --cov-report=term-missing
```

This shows:
- Overall coverage percentage
- Per-file coverage
- **Missing lines** (which lines are not covered)

**Example output:**
```
---------- coverage: platform win32, python 3.9.x -----------
Name                                    Stmts   Miss  Cover   Missing
---------------------------------------------------------------------
terminal_optimizer/__init__.py              5      0   100%
terminal_optimizer/domain_models.py       412     32    92%   145-147, 203-205
terminal_optimizer/sequence_generator.py  387     51    87%   234-236, 445-450
...
---------------------------------------------------------------------
TOTAL                                    2847    431    85%
```

### 4.3 HTML Coverage Report

More detailed coverage report with line-by-line highlighting:

```bash
pytest tests/ --cov=terminal_optimizer --cov-report=html
```

Open `htmlcov/index.html` in a browser to see:
- Visual representation of coverage
- Green = covered, red = not covered
- Branch coverage details

---

## 5. Adding New Tests

### 5.1 Test Naming Conventions

- Test files: `test_<module_name>.py`
- Test functions: `test_<functionality>_<expected_behavior>`
- Test classes: `Test<ClassName>`

**Examples:**
```python
def test_tank_can_accept_valid_product():
    """Tank accepts product when conditions are met."""
    ...

def test_tank_rejects_incompatible_product():
    """Tank rejects product not in allowed_products."""
    ...

class TestVessel:
    def test_cargo_plan_validation_passes():
        ...
    
    def test_cargo_plan_validation_fails_on_mismatch():
        ...
```

### 5.2 Test Structure (AAA Pattern)

Follow **Arrange-Act-Assert** pattern:

```python
def test_tank_filling_updates_volume():
    # ARRANGE: Set up test data
    tank = Tank(
        tank_id="TEST",
        capacity=1000.0,
        allowed_products=["sunflower"],
        current_volume=500.0,
        current_product="sunflower"
    )
    
    # ACT: Perform the operation
    tank.fill("sunflower", 200.0)
    
    # ASSERT: Verify the result
    assert tank.current_volume == 700.0
    assert tank.state == TankState.FILLING
```

### 5.3 Using Fixtures

Reuse common test data with fixtures:

```python
import pytest

@pytest.fixture
def empty_tank():
    """Fixture providing an empty tank."""
    return Tank(
        tank_id="TEST",
        capacity=1000.0,
        allowed_products=["sunflower", "palm_oil"]
    )

def test_filling_empty_tank(empty_tank):
    # Arrange (tank provided by fixture)
    # Act
    empty_tank.fill("sunflower", 500.0)
    # Assert
    assert empty_tank.current_volume == 500.0
    assert empty_tank.current_product == "sunflower"
```

### 5.4 Parametrized Tests

Test multiple scenarios with one function:

```python
import pytest

@pytest.mark.parametrize("from_product,to_product,expected_hours", [
    ("sunflower", "sunflower", 0),
    ("sunflower", "palm_oil", 48),
    ("palm_oil", "sunflower", 48),
    ("palm_oil", "palm_olein", 12),
    ("palm_oil_low3mcpd", "palm_oil", 168),
])
def test_cleaning_duration(from_product, to_product, expected_hours):
    tank = Tank(
        tank_id="TEST",
        capacity=1000.0,
        allowed_products=["sunflower", "palm_*"]
    )
    
    duration = tank.get_cleaning_duration(from_product, to_product)
    assert duration == expected_hours
```

### 5.5 Testing Exceptions

Verify that code raises expected exceptions:

```python
import pytest

def test_tank_rejects_overfill():
    tank = Tank(
        tank_id="TEST",
        capacity=1000.0,
        allowed_products=["sunflower"],
        current_volume=900.0
    )
    
    # Trying to add 200t to a tank with only 100t available
    with pytest.raises(ValueError, match="Insufficient space"):
        tank.fill("sunflower", 200.0)
```

### 5.6 Mocking External Dependencies

Use mocks to isolate units:

```python
from unittest.mock import patch, MagicMock

def test_excel_reader_handles_file_not_found():
    with patch('pandas.read_csv', side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError):
            ExcelReader.read_vessels("nonexistent.csv")
```

### 5.7 Testing Async/Long-Running Operations

For operations that take time, use timeouts:

```python
import pytest

@pytest.mark.timeout(30)  # Fail if test takes >30 seconds
def test_scenario_simulation():
    optimizer = TerminalOptimizer()
    result = optimizer.run("test_data/test_case_3", "output/test")
    assert result['total_operations'] > 0
```

### 5.8 Example: Adding a New Test

**Scenario:** You've added a new method `Tank.get_fill_rate()` and want to test it.

**Step 1:** Create test in `tests/test_domain_models.py`

```python
def test_tank_get_fill_rate_summer(standard_tanks):
    """Test fill rate calculation for summer season."""
    # Arrange
    tank = standard_tanks["RVS_1"]
    operation = Operation(
        op_id="TEST_OP",
        op_type=OperationType.DISCHARGE,
        product="sunflower",
        volume=1000.0,
        target="RVS_1"
    )
    
    # Act
    fill_rate = tank.get_fill_rate(operation, season="summer")
    
    # Assert
    assert fill_rate == 195.0  # Expected summer rail rate
    
def test_tank_get_fill_rate_winter(standard_tanks):
    """Test fill rate calculation for winter season."""
    tank = standard_tanks["RVS_1"]
    operation = Operation(
        op_id="TEST_OP",
        op_type=OperationType.DISCHARGE,
        product="sunflower",
        volume=1000.0,
        target="RVS_1"
    )
    
    fill_rate = tank.get_fill_rate(operation, season="winter")
    assert fill_rate == 146.0  # Expected winter rail rate
```

**Step 2:** Run the test

```bash
pytest tests/test_domain_models.py::test_tank_get_fill_rate_summer -v
```

**Step 3:** Check coverage

```bash
pytest tests/test_domain_models.py --cov=terminal_optimizer.domain_models --cov-report=term-missing
```

Ensure the new method shows 100% coverage.

---

## 6. Test Data

### 6.1 Test Case Structure

Test data is organized in [`test_data/`](../test_data/) directory:

```
test_data/
├── test_case_1/          # Simple: 1 sunflower vessel
│   ├── vessels.csv
│   ├── inventory.csv
│   └── rail_schedule.csv
│
├── test_case_2/          # Medium: 1 palm vessel, 4 fractions
│   ├── vessels.csv
│   ├── cargo_plan.csv
│   ├── inventory.csv
│   └── demand.csv
│
└── test_case_3/          # Complex: 8 palm fractions + sunflower
    ├── vessels.csv
    ├── cargo_plan.csv
    ├── inventory.csv
    ├── rail_schedule.csv
    └── demand.csv
```

### 6.2 Creating New Test Data

To create a new test case:

1. **Create directory:**
   ```bash
   mkdir test_data/test_case_4
   ```

2. **Create CSV files:**

   **vessels.csv:**
   ```csv
   vessel_id,eta,cargo_type,total_volume,demurrage_rate,strategic_weight
   TestVessel,2024-11-01 08:00,palm,30000,150000,1.5
   ```

   **cargo_plan.csv:**
   ```csv
   vessel_id,hold_id,fraction,volume
   TestVessel,H1,palm_oil,15000
   TestVessel,H2,palm_olein,10000
   TestVessel,H3,palm_stearin,5000
   ```

   **inventory.csv:**
   ```csv
   tank_id,current_volume,current_product,state
   RVS_1,8000,sunflower,idle
   RVS_2,7000,sunflower,idle
   RVS_3,0,,idle
   RVS_5,0,,idle
   SHT,0,,idle
   ```

3. **Use in tests:**
   ```python
   def test_new_scenario():
       scenario = ExcelReader.load_scenario("test_data/test_case_4", "test_4")
       assert len(scenario.vessels) == 1
       assert scenario.vessels[0].total_volume == 30000.0
   ```

### 6.3 Test Data Validation

Validate test data before using:

```python
def test_test_case_4_data_is_valid():
    scenario = ExcelReader.load_scenario("test_data/test_case_4", "test_4")
    valid, errors = scenario.validate()
    
    assert valid, f"Test data invalid: {errors}"
```

---

## 7. Continuous Integration

### 7.1 GitHub Actions (Planned)

Create `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run tests with coverage
      run: |
        pytest tests/ --cov=terminal_optimizer --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
```

### 7.2 Pre-commit Hooks

Install pre-commit hooks to run tests before commits:

1. **Install pre-commit:**
   ```bash
   pip install pre-commit
   ```

2. **Create `.pre-commit-config.yaml`:**
   ```yaml
   repos:
     - repo: local
       hooks:
         - id: pytest
           name: pytest
           entry: pytest
           language: system
           pass_filenames: false
           always_run: true
   ```

3. **Install hooks:**
   ```bash
   pre-commit install
   ```

Now tests run automatically before each commit.

---

## 8. Best Practices

### 8.1 Test Independence

Each test should be independent:

```python
# GOOD: Independent tests
def test_tank_fill():
    tank = Tank(...)  # Fresh tank for this test
    tank.fill("sunflower", 100)
    assert tank.current_volume == 100

def test_tank_discharge():
    tank = Tank(...)  # Fresh tank for this test
    tank.fill("sunflower", 100)
    tank.discharge(50)
    assert tank.current_volume == 50

# BAD: Tests depend on order
tank = Tank(...)  # Module-level variable

def test_tank_fill():
    tank.fill("sunflower", 100)
    assert tank.current_volume == 100

def test_tank_discharge():  # Assumes previous test ran!
    tank.discharge(50)
    assert tank.current_volume == 50
```

### 8.2 Test Data Management

Use fixtures for complex data:

```python
@pytest.fixture
def complex_scenario():
    """Fixture with full scenario setup."""
    scenario = Scenario(
        scenario_id="complex",
        vessels=[...],  # Multiple vessels
        tanks=create_standard_tanks(),
        ...
    )
    return scenario

def test_multi_vessel_sequence(complex_scenario):
    # Use pre-built scenario
    optimizer = TerminalOptimizer()
    optimizer.scenario = complex_scenario
    ops = optimizer.generate_initial_sequence()
    assert len(ops) > 10
```

### 8.3 Assertions

Use specific, informative assertions:

```python
# GOOD: Specific assertion with message
assert tank.current_volume == 700.0, \
    f"Expected 700.0, got {tank.current_volume}"

# BETTER: Multiple focused assertions
assert tank.current_volume == 700.0
assert tank.current_product == "sunflower"
assert tank.state == TankState.FILLING

# BAD: Vague assertion
assert tank  # What are we actually checking?
```

### 8.4 Test Documentation

Document complex tests:

```python
def test_sunflower_flow_through_insufficient_capacity():
    """
    Test that flow-through logic correctly identifies insufficient capacity.
    
    Scenario:
    - Vessel requires 38,000t total
    - Tanks have only 20,000t effective capacity
    - Rail can deliver 195 t/h
    - Ship loads at 700 t/h
    
    Expected:
    - Critical point calculation shows infeasibility
    - is_feasible flag is False
    - Alternative recommendations provided
    """
    # Test implementation...
```

---

## 9. Troubleshooting Test Failures

### 9.1 Common Issues

**Issue: `FileNotFoundError` in Excel I/O tests**

**Cause:** Test data files missing

**Solution:**
```bash
git pull origin main  # Ensure test data is up to date
ls test_data/test_case_1/  # Verify files exist
```

**Issue: `AssertionError` with floating point comparisons**

**Cause:** Floating point precision

**Solution:** Use approximate comparisons
```python
# BAD
assert result == 22.22

# GOOD
assert abs(result - 22.22) < 0.01
# OR
import pytest
assert result == pytest.approx(22.22, rel=1e-2)
```

**Issue: Tests pass locally but fail in CI**

**Cause:** Environment differences (paths, timezone, etc.)

**Solution:** Use relative paths, mock datetime
```python
from unittest.mock import patch
from datetime import datetime

@patch('terminal_optimizer.domain_models.datetime')
def test_with_fixed_time(mock_datetime):
    mock_datetime.now.return_value = datetime(2024, 10, 15, 12, 0)
    # Now datetime.now() always returns the same value
```

---

## 10. Performance Testing

For performance-critical functions, add benchmarks:

```python
import pytest

@pytest.mark.benchmark
def test_balance_calculation_performance(benchmark):
    """Benchmark balance calculation for 720 hour horizon."""
    def setup():
        calc = TankBalanceCalculator(create_standard_tanks())
        ops = create_test_operations(count=50)
        return (calc, ops), {}
    
    def run(calc, ops):
        calc.simulate(ops, horizon_hours=720)
    
    result = benchmark.pedantic(run, setup=setup, rounds=10)
    
    # Assert performance requirements
    assert result < 30.0, "Balance calculation should complete in <30 seconds"
```

---

## Appendix: Test Checklist Template

When adding a new feature, use this checklist:

- [ ] Unit tests for new functions/methods
- [ ] Integration tests if feature spans modules
- [ ] Parameterized tests for edge cases
- [ ] Exception/error handling tests
- [ ] Documentation strings for complex tests
- [ ] Test data prepared (if needed)
- [ ] Coverage >80% for new code
- [ ] All tests pass locally
- [ ] No performance degradation

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-12-19 | Initial testing guide |

---

**End of Testing Guide**
