# API Reference: Terminal Optimizer

## Python API Documentation

Complete reference for all public classes, methods, parameters, and return values.

---

## Table of Contents

1. [Domain Models](#domain-models)
2. [Sequence Generation](#sequence-generation)
3. [Balance Calculation](#balance-calculation)
4. [Wagon Management](#wagon-management)
5. [Risk Analysis](#risk-analysis)
6. [Validation](#validation)
7. [Excel I/O](#excel-io)
8. [Main Application](#main-application)

---

## 1. Domain Models

Module: [`terminal_optimizer.domain_models`](../terminal_optimizer/domain_models.py)

### Class: `Tank`

Storage tank with capacity, products, and state management.

#### Constructor

```python
Tank(
    tank_id: str,
    capacity: float,
    allowed_products: List[str],
    is_swing: bool = False,
    deadstock_ratio: Dict[str, float] = {},
    current_volume: float = 0.0,
    current_product: Optional[str] = None,
    state: TankState = TankState.IDLE,
    state_entry_time: Optional[datetime] = None,
    temperature: Optional[float] = None
)
```

**Parameters:**
- `tank_id` (str): Unique identifier (e.g., "RVS_1", "RVS_5", "SHT")
- `capacity` (float): Maximum capacity in tonnes
- `allowed_products` (List[str]): Products that can be stored
- `is_swing` (bool, optional): Whether tank can switch between product types. Default: False
- `deadstock_ratio` (Dict[str, float], optional): Product → deadstock ratio mapping. Default: auto-calculated
- `current_volume` (float, optional): Current inventory. Default: 0.0
- `current_product` (str, optional): Currently stored product. Default: None
- `state` (TankState, optional): Operational state. Default: IDLE
- `state_entry_time` (datetime, optional): When state started. Default: None
- `temperature` (float, optional): Current temperature. Default: None

**Raises:**
- `ValueError`: If capacity ≤ 0, or current_volume < 0, or current_volume > capacity

**Example:**
```python
from terminal_optimizer.domain_models import Tank, TankState

tank = Tank(
    tank_id="RVS_1",
    capacity=9900.0,
    allowed_products=["sunflower"],
    current_volume=8500.0,
    current_product="sunflower",
    state=TankState.IDLE
)
```

#### Methods

##### `get_effective_capacity(product: str) -> float`

Calculate effective capacity accounting for deadstock.

**Parameters:**
- `product` (str): Product type to calculate capacity for

**Returns:**
- `float`: Effective capacity in tonnes (capacity × (1 - deadstock_ratio))

**Raises:**
- `ValueError`: If product is not allowed in this tank

**Example:**
```python
effective_cap = tank.get_effective_capacity("sunflower")
# Returns: 8910.0 (9900 × 0.9)
```

##### `can_accept(product: str, volume: float) -> Tuple[bool, str]`

Check if tank can accept a given volume of product.

**Parameters:**
- `product` (str): Product type to add
- `volume` (float): Volume in tonnes to add

**Returns:**
- `Tuple[bool, str]`: (can_accept, reason)
  - `can_accept` (bool): True if tank can accept
  - `reason` (str): "OK" if can accept, otherwise error message

**Example:**
```python
can_fill, reason = tank.can_accept("sunflower", 1000.0)
if can_fill:
    tank.fill("sunflower", 1000.0)
else:
    print(f"Cannot fill: {reason}")
```

##### `requires_cleaning(new_product: str) -> bool`

Check if cleaning is required before storing a new product.

**Parameters:**
- `new_product` (str): Product type to be stored

**Returns:**
- `bool`: True if cleaning is required

**Example:**
```python
if tank.requires_cleaning("palm_oil"):
    print(f"Need {tank.get_cleaning_duration(tank.current_product, 'palm_oil')} hours cleaning")
```

##### `get_cleaning_duration(from_product: str, to_product: str) -> float`

Get required cleaning duration for product transition.

**Parameters:**
- `from_product` (str): Current product type
- `to_product` (str): New product type

**Returns:**
- `float`: Cleaning duration in hours

**Example:**
```python
duration = tank.get_cleaning_duration("sunflower", "palm_oil")
# Returns: 48.0 hours
```

##### `fill(product: str, volume: float) -> None`

Add product to the tank.

**Parameters:**
- `product` (str): Product type to add
- `volume` (float): Volume in tonnes to add

**Raises:**
- `ValueError`: If tank cannot accept the product/volume

**Example:**
```python
tank.fill("sunflower", 500.0)
```

##### `discharge(volume: float) -> float`

Remove product from the tank.

**Parameters:**
- `volume` (float): Volume in tonnes to remove

**Returns:**
- `float`: Actual volume discharged (may be less if tank doesn't have enough)

**Raises:**
- `ValueError`: If tank is in wrong state

**Example:**
```python
actual = tank.discharge(1000.0)
print(f"Discharged {actual}t")
```

---

### Class: `Vessel`

Ship with cargo plan and demurrage information.

#### Constructor

```python
Vessel(
    vessel_id: str,
    eta: datetime,
    cargo_type: CargoType,
    total_volume: float,
    cargo_plan: Dict[str, Tuple[str, float]] = {},
    demurrage_rate: float = 100000.0,
    strategic_weight: float = 1.0,
    notes: str = "",
    actual_arrival: Optional[datetime] = None,
    actual_departure: Optional[datetime] = None
)
```

**Parameters:**
- `vessel_id` (str): Unique identifier for the vessel
- `eta` (datetime): Expected time of arrival
- `cargo_type` (CargoType or str): "palm" or "sunflower"
- `total_volume` (float): Total cargo volume in tonnes
- `cargo_plan` (Dict[str, Tuple[str, float]], optional): For palm: hold_id → (fraction, volume)
- `demurrage_rate` (float, optional): Cost per hour of delay in RUB. Default: 100,000
- `strategic_weight` (float, optional): Priority multiplier. Default: 1.0
- `notes` (str, optional): Additional information
- `actual_arrival` (datetime, optional): Actual arrival time
- `actual_departure` (datetime, optional): Actual departure time

**Example:**
```python
from terminal_optimizer.domain_models import Vessel, CargoType
from datetime import datetime

vessel = Vessel(
    vessel_id="Victoria",
    eta=datetime(2024, 10, 15, 8, 0),
    cargo_type=CargoType.PALM,
    total_volume=28000.0,
    cargo_plan={
        "H1": ("palm_oil", 12000),
        "H2": ("palm_oil", 8000),
        "H3": ("palm_olein", 3500),
        "H4": ("palm_olein", 2000),
        "H5": ("palm_stearin", 1500),
        "H6": ("palm_pfad", 1000),
    },
    demurrage_rate=120000.0,
    strategic_weight=1.5
)
```

#### Methods

##### `get_fractions() -> List[Tuple[str, str, float]]`

Get list of fractions from cargo plan.

**Returns:**
- `List[Tuple[str, str, float]]`: List of (hold_id, fraction_name, volume)

**Example:**
```python
fractions = vessel.get_fractions()
# [("H1", "palm_oil", 12000), ("H2", "palm_oil", 8000), ...]
```

##### `validate_cargo_plan() -> Tuple[bool, str]`

Validate that cargo plan volumes sum to total volume.

**Returns:**
- `Tuple[bool, str]`: (is_valid, message)

**Example:**
```python
valid, msg = vessel.validate_cargo_plan()
if not valid:
    print(f"Invalid cargo plan: {msg}")
```

##### `calculate_demurrage(hours_delayed: float) -> float`

Calculate demurrage cost for delay.

**Parameters:**
- `hours_delayed` (float): Number of hours vessel was delayed

**Returns:**
- `float`: Total demurrage cost in RUB

**Example:**
```python
cost = vessel.calculate_demurrage(24.0)  # 24 hour delay
# Returns: 2,880,000 RUB (120,000 × 1.5 × 24)
```

---

### Class: `Operation`

A single operation in the terminal schedule.

#### Constructor

```python
Operation(
    op_id: str,
    vessel_id: Optional[str] = None,
    op_type: OperationType = OperationType.DISCHARGE,
    product: Optional[str] = None,
    source: str = "",
    target: str = "",
    volume: float = 0.0,
    start_time: Optional[datetime] = None,
    duration: float = 0.0,
    end_time: Optional[datetime] = None,
    line: Optional[str] = None,
    wagons: Optional[int] = None,
    user_locked: bool = False,
    dependencies: List[str] = [],
    notes: str = ""
)
```

**Parameters:**
- `op_id` (str): Unique operation identifier
- `vessel_id` (str, optional): Associated vessel (if any)
- `op_type` (OperationType, optional): Type of operation. Default: DISCHARGE
- `product` (str, optional): Product being handled
- `source` (str, optional): Source of product (Ship/Rail/Tank)
- `target` (str, optional): Destination (Tank/Ship/Rail)
- `volume` (float, optional): Volume in tonnes
- `start_time` (datetime, optional): When operation starts
- `duration` (float, optional): Duration in hours
- `end_time` (datetime, optional): When operation ends (auto-calculated if not provided)
- `line` (str, optional): Pipeline line (Line1/Line2 for palm)
- `wagons` (int, optional): Number of railway wagons (auto-calculated if not provided)
- `user_locked` (bool, optional): Whether user has locked this operation. Default: False
- `dependencies` (List[str], optional): Operations that must complete first
- `notes` (str, optional): Additional information

**Example:**
```python
from terminal_optimizer.domain_models import Operation, OperationType
from datetime import datetime

op = Operation(
    op_id="DISCHARGE_Victoria_H1",
    vessel_id="Victoria",
    op_type=OperationType.DISCHARGE,
    product="palm_oil",
    source="Ship_Victoria_H1",
    target="RVS_3",
    volume=20000.0,
    start_time=datetime(2024, 10, 16, 8, 0),
    duration=22.22,
    line="Line1"
)
```

#### Methods

##### `calculate_duration(rate: Optional[float] = None, season: str = "summer") -> float`

Calculate operation duration based on type and volume.

**Parameters:**
- `rate` (float, optional): Override flow rate in tonnes/hour
- `season` (str, optional): "summer" or "winter" for rail operations. Default: "summer"

**Returns:**
- `float`: Duration in hours

**Example:**
```python
duration = op.calculate_duration(rate=900.0)
# Returns: 22.22 hours (20000 / 900)
```

##### `overlaps_with(other: Operation) -> bool`

Check if this operation overlaps with another in time.

**Parameters:**
- `other` (Operation): Another operation to check against

**Returns:**
- `bool`: True if operations overlap in time

**Example:**
```python
if op1.overlaps_with(op2):
    print("Conflict detected!")
```

##### `can_start_at(time: datetime, completed_ops: Dict[str, datetime]) -> Tuple[bool, str]`

Check if operation can start at given time considering dependencies.

**Parameters:**
- `time` (datetime): Proposed start time
- `completed_ops` (Dict[str, datetime]): Mapping of op_id → completion time

**Returns:**
- `Tuple[bool, str]`: (can_start, reason)

**Example:**
```python
completed = {"OP_001": datetime(2024, 10, 16, 10, 0)}
can_start, reason = op.can_start_at(datetime(2024, 10, 16, 12, 0), completed)
```

---

### Class: `Scenario`

Container for all input data for a planning scenario.

#### Constructor

```python
Scenario(
    scenario_id: str,
    vessels: List[Vessel] = [],
    tanks: Dict[str, Tank] = {},
    rail_schedule: List[Dict[str, Any]] = [],
    current_inventory: Dict[str, Dict[str, Any]] = {},
    client_demand: Dict[str, Dict[str, Any]] = {},
    parameters: Dict[str, Any] = {},
    horizon_days: int = 30
)
```

**Parameters:**
- `scenario_id` (str): Unique identifier for this scenario
- `vessels` (List[Vessel], optional): List of vessels in the planning horizon
- `tanks` (Dict[str, Tank], optional): Dictionary of tank configurations
- `rail_schedule` (List[Dict], optional): List of incoming rail deliveries
- `current_inventory` (Dict, optional): Current state of all tanks
- `client_demand` (Dict, optional): Demand matrix by week and client
- `parameters` (Dict, optional): Scenario parameters (rates, times, costs)
- `horizon_days` (int, optional): Planning horizon in days. Default: 30

**Example:**
```python
from terminal_optimizer.domain_models import Scenario, create_standard_tanks

scenario = Scenario(
    scenario_id="test_scenario_1",
    vessels=[vessel1, vessel2],
    tanks=create_standard_tanks(),
    horizon_days=30
)
```

#### Methods

##### `validate() -> Tuple[bool, List[str]]`

Validate scenario data completeness and consistency.

**Returns:**
- `Tuple[bool, List[str]]`: (is_valid, list_of_errors)

**Example:**
```python
valid, errors = scenario.validate()
if not valid:
    for error in errors:
        print(f"Validation error: {error}")
```

---

## 2. Sequence Generation

Module: [`terminal_optimizer.sequence_generator`](../terminal_optimizer/sequence_generator.py)

### Class: `PalmSequenceGenerator`

Generate discharge sequence for palm vessels using heuristics.

#### Constructor

```python
PalmSequenceGenerator(
    tanks: Dict[str, Tank],
    parameters: Optional[Dict[str, Any]] = None
)
```

**Parameters:**
- `tanks` (Dict[str, Tank]): Tank configurations
- `parameters` (Dict[str, Any], optional): System parameters

#### Methods

##### `generate_sequence(vessel: Vessel, start_time: datetime) -> List[Operation]`

Generate full operation sequence for palm vessel discharge.

**Parameters:**
- `vessel` (Vessel): Palm vessel to discharge
- `start_time` (datetime): When discharge can begin (after berthing)

**Returns:**
- `List[Operation]`: Ordered list of operations

**Raises:**
- `ValueError`: If vessel cargo_type is not PALM

**Example:**
```python
from terminal_optimizer.sequence_generator import PalmSequenceGenerator
from datetime import datetime

gen = PalmSequenceGenerator(tanks)
operations = gen.generate_sequence(vessel, datetime(2024, 10, 16, 8, 0))
```

---

### Class: `SunflowerHandler`

Handle sunflower export with flow-through logic.

#### Constructor

```python
SunflowerHandler(
    tanks: Dict[str, Tank],
    parameters: Optional[Dict[str, Any]] = None
)
```

#### Methods

##### `calculate_critical_start_point(vessel: Vessel, rail_rate: float, ship_rate: float) -> Dict[str, Any]`

Calculate minimum tank inventory to start loading.

**Parameters:**
- `vessel` (Vessel): Sunflower vessel to load
- `rail_rate` (float): Rail delivery rate in  t/h
- `ship_rate` (float): Ship loading rate in t/h

**Returns:**
- `Dict[str, Any]`: Dictionary containing:
  - `critical_start` (float): Minimum tonnes needed before loading
  - `loading_duration` (float): Total loading duration in hours
  - `rail_inflow_during_loading` (float): Tonnes delivered by rail during loading
  - `is_feasible` (bool): Whether operation is feasible

**Example:**
```python
from terminal_optimizer.sequence_generator import SunflowerHandler

handler = SunflowerHandler(tanks)
result = handler.calculate_critical_start_point(vessel, rail_rate=195.0, ship_rate=700.0)
print(f"Need {result['critical_start']:.0f}t to start loading")
```

---

## 3. Balance Calculation

Module: [`terminal_optimizer.balance_calculator`](../terminal_optimizer/balance_calculator.py)

### Class: `TankBalanceCalculator`

Simulate tank inventory hour by hour.

#### Constructor

```python
TankBalanceCalculator(
    tanks: Dict[str, Tank],
    parameters: Optional[Dict[str, Any]] = None
)
```

**Parameters:**
- `tanks` (Dict[str, Tank]): Tank configurations
- `parameters` (Dict[str, Any], optional): System parameters

#### Methods

##### `simulate(operations: List[Operation], horizon_hours: int, current_inventory: Optional[Dict[str, Dict[str, Any]]] = None) -> pd.DataFrame`

Run full balance simulation.

**Parameters:**
- `operations` (List[Operation]): Operations to simulate
- `horizon_hours` (int): Number of hours to simulate
- `current_inventory` (Dict, optional): Initial tank states

**Returns:**
- `pd.DataFrame`: Balance results with columns [hour, RVS_1, RVS_2, RVS_3, RVS_5, SHT, total]

**Example:**
```python
from terminal_optimizer.balance_calculator import TankBalanceCalculator

calc = TankBalanceCalculator(tanks)
balance_df = calc.simulate(operations, horizon_hours=720)

# Access results
print(balance_df.head())
```

##### `has_violations(severity: Optional[str] = None) -> bool`

Check for constraint violations.

**Parameters:**
- `severity` (str, optional): Filter by "ERROR", "WARNING", or "INFO". Default: None (all)

**Returns:**
- `bool`: True if violations exist

**Example:**
```python
if calc.has_violations(severity="ERROR"):
    print("Critical errors found!")
```

---

## 4. Wagon Management

Module: [`terminal_optimizer.wagon_manager`](../terminal_optimizer/wagon_manager.py)

### Class: `WagonManager`

Calculate wagon requirements and schedule batches.

#### Constructor

```python
WagonManager(
    parameters: Optional[Dict[str, Any]] = None,
    total_fleet: int = 500,
    wagon_capacity: float = 65.0,
    batch_size: int = 18,
    max_batches_per_day: int = 4
)
```

**Parameters:**
- `parameters` (Dict[str, Any], optional): System parameters
- `total_fleet` (int, optional): Total wagon fleet size. Default: 500
- `wagon_capacity` (float, optional): Capacity per wagon in tonnes. Default: 65.0
- `batch_size` (int, optional): Wagons per batch. Default: 18
- `max_batches_per_day` (int, optional): Maximum batches per day. Default: 4

#### Methods

##### `calculate_requirement(operation: Operation) -> int`

Calculate wagon count from operation volume.

**Parameters:**
- `operation` (Operation): Operation to calculate for

**Returns:**
- `int`: Number of wagons needed (rounded up)

**Example:**
```python
from terminal_optimizer.wagon_manager import WagonManager

wm = WagonManager()
wagons = wm.calculate_requirement(operation)
print(f"Need {wagons} wagons")
```

##### `distribute_to_batches(day_wagons: int, date: date) -> List[WagonBatch]`

Distribute daily wagons to specific batches.

**Parameters:**
- `day_wagons` (int): Total wagons for the day
- `date` (date): The date

**Returns:**
- `List[WagonBatch]`: List of batches with timing

**Example:**
```python
from datetime import date

batches = wm.distribute_to_batches(54, date(2024, 10, 15))
for batch in batches:
    print(f"Batch at {batch.time}: {batch.wagons} wagons")
```

---

## 5. Risk Analysis

Module: [`terminal_optimizer.risk_analysis`](../terminal_optimizer/risk_analysis.py)

### Class: `WagonForecaster`

Predict wagon availability using Markov chains.

####Constructor

```python
WagonForecaster()
```

#### Methods

##### `forecast(initial_state: Dict[WagonState, int], days: int, transition_matrix: Optional[np.ndarray] = None) -> Dict[int, Dict[WagonState, float]]`

Project wagon state distribution forward.

**Parameters:**
- `initial_state` (Dict[WagonState, int]): Current wagon distribution by state
- `days` (int): Number of days to forecast
- `transition_matrix` (np.ndarray, optional): Custom transition matrix. Default: uses standard

**Returns:**
- `Dict[int, Dict[WagonState, float]]`: Forecast by day → state → expected count

**Example:**
```python
from terminal_optimizer.risk_analysis import WagonForecaster, WagonState

forecaster = WagonForecaster()
initial = {
    WagonState.LOADING: 20,
    WagonState.EN_ROUTE: 150,
    WagonState.AT_CLIENT: 200,
    WagonState.RETURNING: 100,
    WagonState.AVAILABLE: 30
}

forecast = forecaster.forecast(initial, days=30)
print(f"Day 7: {forecast[7][WagonState.AVAILABLE]:.0f} wagons available")
```

### Functions

##### `identify_wagon_shortage_risks(wagons_needed: Dict[date, int], forecast: Dict[int, Dict[WagonState, float]], dates: List[date]) -> List[Risk]`

Identify dates where wagon availability may be insufficient.

**Parameters:**
- `wagons_needed` (Dict[date, int]): Required wagons by date
- `forecast` (Dict): Wagon forecast from `WagonForecaster`
- `dates` (List[date]): Dates to check

**Returns:**
- `List[Risk]`: List of wagon shortage risks

**Example:**
```python
from terminal_optimizer.risk_analysis import identify_wagon_shortage_risks

risks = identify_wagon_shortage_risks(wagons_needed, forecast, dates)
for risk in risks:
    print(f"{risk.date}: {risk.description}")
```

---

## 6. Validation

Module: [`terminal_optimizer.validation`](../terminal_optimizer/validation.py)

### Functions

##### `validate_capacity_constraints(operations: List[Operation], tanks: Dict[str, Tank], balance_df: pd.DataFrame) -> List[Violation]`

Check that no tank exceeds capacity.

**Parameters:**
- `operations` (List[Operation]): Operations to validate
- `tanks` (Dict[str, Tank]): Tank configurations
- `balance_df` (pd.DataFrame): Balance simulation results

**Returns:**
- `List[Violation]`: Capacity violations found

**Example:**
```python
from terminal_optimizer.validation import validate_capacity_constraints

violations = validate_capacity_constraints(operations, tanks, balance_df)
for v in violations:
    print(f"{v.severity}: {v.description}")
```

##### `validate_rail_batches(operations: List[Operation]) -> List[Violation]`

Check that rail batches don't exceed 4 per day.

**Parameters:**
- `operations` (List[Operation]): Operations to validate

**Returns:**
- `List[Violation]`: Rail limit violations

**Example:**
```python
from terminal_optimizer.validation import validate_rail_batches

violations = validate_rail_batches(operations)
```

---

## 7. Excel I/O

Module: [`terminal_optimizer.excel_io`](../terminal_optimizer/excel_io.py)

### Class: `ExcelReader`

Load scenario data from Excel/CSV files.

#### Static Methods

##### `load_scenario(directory: str, scenario_id: str) -> Scenario`

Load complete scenario from directory.

**Parameters:**
- `directory` (str): Path to directory containing CSV files
- `scenario_id` (str): Unique scenario identifier

**Returns:**
- `Scenario`: Loaded scenario object

**Raises:**
- `FileNotFoundError`: If required files are missing
- `ValueError`: If data format is invalid

**Example:**
```python
from terminal_optimizer.excel_io import ExcelReader

scenario = ExcelReader.load_scenario("test_data/test_case_1", "test_1")
```

---

### Class: `ExcelWriter`

Export results to Excel/CSV format.

#### Static Methods

##### `write_operations(operations: List[Operation], filepath: str) -> None`

Export operation sequence to CSV.

**Parameters:**
- `operations` (List[Operation]): Operations to export
- `filepath` (str): Output file path

**Example:**
```python
from terminal_optimizer.excel_io import ExcelWriter

ExcelWriter.write_operations(operations, "output/operations.csv")
```

---

## 8. Main Application

Module: [`terminal_optimizer.main`](../terminal_optimizer/main.py)

### Class: `TerminalOptimizer`

Main application class coordinating all components.

#### Constructor

```python
TerminalOptimizer()
```

#### Methods

##### `run(input_excel: str, output_excel: str, run_simulation: bool = False) -> Dict[str, Any]`

Run full optimization workflow.

**Parameters:**
- `input_excel` (str): Path to input Excel/directory
- `output_excel` (str): Path for output files
- `run_simulation` (bool, optional): Whether to run Monte Carlo simulation. Default: False

**Returns:**
- `Dict[str, Any]`: Summary results containing:
  - `scenario_id` (str): Scenario identifier
  - `total_operations` (int): Number of operations generated
  - `makespan_hours` (float): Total time span
  - `violations` (int): Number of constraint violations
  - `total_cost` (float): Estimated total cost in RUB
  - `risks_high` (int): Number of HIGH severity risks
  - `risks_medium` (int): Number of MEDIUM severity risks
  - `simulation_confidence` (float, optional): Confidence score if simulation run

**Example:**
```python
from terminal_optimizer.main import TerminalOptimizer

optimizer = TerminalOptimizer()
results = optimizer.run("test_data/test_case_1", "output/results.csv", run_simulation=True)

print(f"Generated {results['total_operations']} operations")
print(f"Makespan: {results['makespan_hours']:.1f} hours")
print(f"Violations: {results['violations']}")
print(f"High risks: {results['risks_high']}")
```

##### `run_simulation(iterations: int = 50) -> Dict[str, Any]`

Run Monte Carlo simulation to assess plan robustness.

**Parameters:**
- `iterations` (int, optional): Number of simulation runs. Default: 50

**Returns:**
- `Dict[str, Any]`: Simulation report containing:
  - `success_rate` (float): Percentage of successful runs
  - `confidence_score` (float): Overall confidence (0.0-1.0)
  - `avg_conflicts` (float): Average number of conflicts per run
  - `recommendations` (List[str]): Suggestions to improve robustness

##### `load_scenario(excel_path: str) -> Scenario`

Load scenario from Excel file.

**Parameters:**
- `excel_path` (str): Path to Excel file or directory

**Returns:**
- `Scenario`: Loaded scenario

**Example:**
```python
scenario = optimizer.load_scenario("test_data/test_case_1")
```

##### `export_results(output_path: str) -> str`

Export all results to files.

**Parameters:**
- `output_path` (str): Base path for output files

**Returns:**
- `str`: Path to main output file

**Example:**
```python
output_file = optimizer.export_results("output/results")
print(f"Results saved to {output_file}")
```

---

## Usage Examples

### Complete Workflow

```python
from terminal_optimizer.main import TerminalOptimizer
from terminal_optimizer.domain_models import create_standard_tanks, Vessel, CargoType
from datetime import datetime

# Create optimizer
optimizer = TerminalOptimizer()

# Option 1: Load from files
result = optimizer.run("test_data/test_case_1", "output/results")

# Option 2: Programmatic setup
scenario = optimizer.load_scenario("test_data/test_case_1")

# Generate sequence
operations = optimizer.generate_initial_sequence()

# Calculate balances
balance_df = optimizer.calculate_balances(operations)

# Validate
violations = optimizer.validate_solution(balance_df, operations)

# Analyze risks
risks = optimizer.analyze_risks(operations)

# Export
optimizer.export_results("output/results")
```

### Custom Vessel Setup

```python
from terminal_optimizer.domain_models import Vessel, CargoType, Tank, create_standard_tanks
from datetime import datetime

# Create tanks
tanks = create_standard_tanks()

# Create vessel
vessel = Vessel(
    vessel_id="MyVessel",
    eta=datetime(2024, 11, 1, 10, 0),
    cargo_type=CargoType.PALM,
    total_volume=25000.0,
    cargo_plan={
        "H1": ("palm_oil", 15000),
        "H2": ("palm_olein", 7000),
        "H3": ("palm_stearin", 3000),
    },
    demurrage_rate=150000.0,
    strategic_weight=2.0
)

# Validate
valid, msg = vessel.validate_cargo_plan()
print(f"Valid: {valid}, Message: {msg}")
```

---

## Error Handling

All API functions raise standard Python exceptions:

- **`ValueError`**: Invalid parameters or data
- **`FileNotFoundError`**: Missing input files
- **`KeyError`**: Missing required data fields
- **`TypeError`**: Wrong parameter types

**Example:**
```python
try:
    result = optimizer.run("input.xlsx", "output.xlsx")
except FileNotFoundError as e:
    print(f"Input file not found: {e}")
except ValueError as e:
    print(f"Invalid data: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

### Class: `SequenceEditor`

Handles user edits to the operation sequence.

#### Constructor

```python
SequenceEditor(optimizer: TerminalOptimizer)
```

#### Methods

##### `apply_swap(op_a_id: str, op_b_id: str, validate: bool = True) -> Tuple[bool, str, List[Operation]]`

Swap start times of two operations.

**Parameters:**
- `op_a_id` (str): ID of first operation
- `op_b_id` (str): ID of second operation
- `validate` (bool, optional): Whether to validate after swapping. Default: True

**Returns:**
- `Tuple[bool, str, List[Operation]]`: (success, message, updated_operations)

##### `apply_lock(op_id: str) -> Tuple[bool, str]`

Lock an operation to prevent modifications.

**Parameters:**
- `op_id` (str): ID of operation to lock

**Returns:**
- `Tuple[bool, str]`: (success, message)

##### `apply_time_adjustment(op_id: str, new_start_time: datetime, validate: bool = True) -> Tuple[bool, str, List[Operation]]`

Adjust the start time of an operation.

**Parameters:**
- `op_id` (str): ID of operation to adjust
- `new_start_time` (datetime): New start time
- `validate` (bool, optional): Whether to validate after adjustment. Default: True

**Returns:**
- `Tuple[bool, str, List[Operation]]`: (success, message, updated_operations)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | 2026-01-09 | Added SequenceEditor and Monte Carlo simulation methods |
| 1.0 | 2024-12-19 | Initial API reference |

---

**End of API Reference**
