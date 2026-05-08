# Phase 3 Implementation Summary

## Overview

Phase 3 (Wagon Manager & Excel I/O) has been successfully completed. This phase implements railway wagon management including looping logic, and provides complete Excel/CSV input/output capabilities.

## Components Delivered

### 1. WagonManager Class
Location: [`terminal_optimizer/wagon_manager.py`](../terminal_optimizer/wagon_manager.py)

**Key Features:**
- **Wagon Requirement Calculation**: Computes wagons needed per operation (CEILING(volume/65))
- **Daily Distribution**: Groups wagon needs by day and checks batch limits
- **Batch Planning**: Distributes wagons into batches (18 wagons per batch, max 4/day)
- **Looping Logic**: Tracks wagon availability from sunflower discharge → palm reuse
- **Gap Detection**: Identifies shortfalls requiring external wagon orders
- **Cost Calculation**: Computes external wagon procurement costs

**Methods:**
- [`calculate_requirement(operation)`](../terminal_optimizer/wagon_manager.py:60): Calculate wagons for single operation
- [`distribute_to_days(operations)`](../terminal_optimizer/wagon_manager.py:79): Group operations by day
- [`distribute_to_batches(daily_reqs)`](../terminal_optimizer/wagon_manager.py:105): Create wagon batches
- [`track_wagon_transformation(operations)`](../terminal_optimizer/wagon_manager.py:157): Track wagon looping
- [`check_wagon_availability(operation, wagon_pool)`](../terminal_optimizer/wagon_manager.py:211): Check if wagons available
- [`calculate_external_order(gaps)`](../terminal_optimizer/wagon_manager.py:239): Calculate external wagon needs
- [`generate_wagon_report(operations)`](../terminal_optimizer/wagon_manager.py:261): Comprehensive wagon analysis

**Wagon Looping Algorithm:**
```
1. After sunflower discharge completes:
   - Record dirty_wagons = wagons_used
   - Add prep_time (default 1.5 hours)
   - Apply reject_rate (12%)
   - clean_wagons = dirty_wagons × (1 - 0.12)
   - Add to wagon_pool at ready_time

2. For palm operations:
   - Check wagon_pool for available wagons
   - If insufficient → identify gap
   - Generate external order (lead_time = 3 days)
```

**Constants:**
```python
WAGON_CAPACITY = 65.0  # tonnes per wagon
WAGONS_PER_BATCH = 18
MAX_BATCHES_PER_DAY_SUMMER = 4
MAX_BATCHES_PER_DAY_WINTER = 3
WAGON_PREP_TIME_HOURS = 1.5
WAGON_REJECT_RATE = 0.12  # 12% rejection rate
```

### 2. ExcelReader Class
Location: [`terminal_optimizer/excel_io.py`](../terminal_optimizer/excel_io.py)

**Key Features:**
- **Flexible Date Parsing**: Supports ISO, European, and US date formats
- **Vessel Import**: Reads vessel schedules with ETA, cargo type, volumes
- **Cargo Plan Import**: Parses palm vessel hold-by-hold cargo plans
- **Rail Schedule Import**: Reads railway delivery schedules
- **Inventory Import**: Loads current tank states
- **Demand Import**: Reads client demand matrices
- **Complete Scenario Loading**: Aggregates all inputs into Scenario object

**Methods:**
- [`read_vessels(filepath)`](../terminal_optimizer/excel_io.py:31): Read vessel schedule CSV
- [`read_cargo_plan(filepath, vessel_id)`](../terminal_optimizer/excel_io.py:96): Read palm cargo plan
- [`read_rail_schedule(filepath)`](../terminal_optimizer/excel_io.py:127): Read rail deliveries
- [`read_inventory(filepath)`](../terminal_optimizer/excel_io.py:164): Read tank inventory
- [`read_demand(filepath)`](../terminal_optimizer/excel_io.py:199): Read client demand
- [`load_scenario(vessels_file, inventory_file, ...)`](../terminal_optimizer/excel_io.py:230): Load complete scenario

**Supported Date Formats:**
- ISO: `2025-01-15T14:30:00`, `2025-01-15 14:30`, `2025-01-15`
- European: `15.01.2025 14:30`, `15.01.2025`
- US: `01/15/2025 14:30`, `01/15/2025`

**Input File Formats:**

*vessels.csv:*
```csv
vessel_id,eta,cargo_type,total_volume,demurrage_rate,strategic_weight,notes
Victoria,2025-01-15 08:00,palm,38000,120000,1.5,Priority vessel
Atlantic,2025-01-18 10:00,sunflower,35000,100000,1.0,
```

*cargo_plan.csv:*
```csv
vessel_id,hold_id,fraction,volume
Victoria,H1,palm_oil,8070.5
Victoria,H2,palm_olein,6842.6
Victoria,H3,palm_stearin,5643.2
```

*inventory.csv:*
```csv
tank_id,current_product,current_volume,temperature
RVS_1,sunflower,5000,
RVS_2,sunflower,3000,
RVS_3,empty,0,
RVS_5,palm_oil,1500,45
SHT,empty,0,
```

*rail_schedule.csv:*
```csv
date,product,volume,wagons
2025-01-10 08:00,sunflower,1170,18
2025-01-10 14:00,sunflower,1170,18
```

### 3. ExcelWriter Class
Location: [`terminal_optimizer/excel_io.py`](../terminal_optimizer/excel_io.py:296)

**Key Features:**
- **Operations Export**: Writes complete operation timeline
- **Wagon Analysis Export**: Detailed wagon report with batches, gaps, costs
- **Executive Summary**: High-level summary of scenario and results
- **CSV Format**: Uses CSV for maximum Excel compatibility

**Methods:**
- [`write_operations(operations, filepath)`](../terminal_optimizer/excel_io.py:307): Export operations timeline
- [`write_wagon_analysis(wagon_report, filepath)`](../terminal_optimizer/excel_io.py:339): Export wagon analysis
- [`write_summary(scenario, operations, wagon_report, filepath)`](../terminal_optimizer/excel_io.py:400): Export executive summary

**Output File Formats:**

*operations.csv:*
```csv
Operation ID,Vessel ID,Type,Product,Source,Target,Volume (t),Start Time,Duration (h),End Time,Line,Wagons,Locked,Notes
OP_0001,Victoria,berthing,,,,,2025-01-15T08:00:00,1.50,2025-01-15T09:30:00,,,No,Berthing Victoria
OP_0002,Victoria,discharge,palm_oil,Ship_Victoria_H1,RVS_3,8070.5,2025-01-15T09:30:00,8.97,2025-01-15T18:28:00,Line1,,No,Discharge H1: palm_oil
```

*wagon_analysis.csv:*
```csv
DAILY WAGON REQUIREMENTS
Date,Total Wagons,Operations
2025-01-15,36,OP_0010, OP_0011

WAGON BATCHES
Batch ID,Product,Wagons,Volume (t),Arrival Time,Origin,Notes
BATCH_0001,sunflower,18,1170.0,2025-01-15T08:00:00,external,Batch 1 of day 2025-01-15

EXTERNAL WAGON ORDERS
Order Date,Wagons,Cost (RUB)
2025-01-12,15,750000
TOTAL,,750000
```

## Test Coverage

Comprehensive test suite created in:
- [`tests/test_wagon_manager.py`](../tests/test_wagon_manager.py) (13 tests)
- [`tests/test_excel_io.py`](../tests/test_excel_io.py) (10 tests)

### Test Classes for WagonManager:

1. **TestWagonManager** (10 tests)
   - Wagon requirement calculation
   - Rounding behavior (ceiling function)
   - Daily distribution
   - Batch creation
   - Daily limit checking
   - Wagon transformation tracking
   - Availability checking (sufficient/insufficient)
   - External order calculation
   - Comprehensive report generation

2. **TestWagonBatch** (1 test)
   - Batch dataclass creation

3. **TestWagonAvailability** (1 test)
   - Availability dataclass creation

4. **TestIntegration** (1 test)
   - End-to-end wagon workflow

### Test Classes for ExcelIO:

1. **TestExcelReader** (8 tests)
   - Reading vessels from CSV
   - Reading cargo plans
   - Reading rail schedules
   - Reading inventory
   - Reading demand
   - Complete scenario loading
   - Date format parsing (multiple formats)
   - Error handling

2. **TestExcelWriter** (3 tests)
   - Writing operations to CSV
   - Writing wagon analysis
   - Writing executive summary

**Total Phase 3 Tests: 23 comprehensive tests**

## Key Algorithms Implemented

### 1. Wagon Looping
Tracks sunflower wagon reuse for palm loading:
```
For each sunflower discharge operation:
  1. Wagons become "dirty" at end_time
  2. After prep_time (1.5h): ready for reuse
  3. Apply reject_rate (12%): clean = dirty × 0.88
  4. Add to available pool at ready_time

For palm operations:
  1. Count available clean wagons before start_time
  2. Compare with requirement
  3. If gap exists: order external wagons
```

### 2. Batch Distribution
Distributes wagon requirements into batches:
```
For each day:
  1. Sum total wagon requirements
  2. Check against daily limit (72 sunflower, 54 palm)
  3. Create batches (18 wagons each, max 4/day)
  4. If exceeds limit: generate warning
```

### 3. External Wagon Ordering
Calculates when to order external wagons:
```
For each gap (shortage):
  1. Identify need_date (when wagons needed)
  2. Calculate order_date = need_date - lead_time (3 days)
  3. Calculate cost = wagons × unit_cost (50,000 RUB/wagon)
  4. Add to external order list
```

## Integration with Previous Phases

Phase 3 integrates seamlessly with Phases 1 & 2:

- **Uses [`Operation`](../terminal_optimizer/domain_models.py:623)** objects from Phase 1
- **Works with operations** generated by [`PalmSequenceGenerator`](../terminal_optimizer/sequence_generator.py:55) and [`SunflowerHandler`](../terminal_optimizer/sequence_generator.py:434)
- **Reads [`Scenario`](../terminal_optimizer/domain_models.py:871)** data via ExcelReader
- **Exports results** for use in balance calculation and optimization

## Usage Examples

### Reading a Scenario

```python
from terminal_optimizer.excel_io import ExcelReader

# Load complete scenario from CSV files
scenario = ExcelReader.load_scenario(
    vessels_file="test_data/test_case_1/vessels.csv",
    inventory_file="test_data/test_case_1/inventory.csv",
    rail_schedule_file="test_data/test_case_1/rail_schedule.csv",
    scenario_id="test_case_1"
)

# Access loaded data
print(f"Loaded {len(scenario.vessels)} vessels")
print(f"Tanks: {list(scenario.tanks.keys())}")
```

### Wagon Analysis

```python
from terminal_optimizer.wagon_manager import WagonManager

# Initialize manager
wagon_mgr = WagonManager(
    total_wagon_fleet=500,
    season="summer"
)

# Generate comprehensive report
report = wagon_mgr.generate_wagon_report(operations)

# Check results
print(f"Total external cost: {report['total_external_cost']:,.0f} RUB")
print(f"Warnings: {len(report['warnings'])}")

for gap_time, gap_wagons in report['gaps'].items():
    print(f"Gap at {gap_time}: {gap_wagons} wagons short")
```

### Writing Results

```python
from terminal_optimizer.excel_io import ExcelWriter

# Write operations timeline
ExcelWriter.write_operations(
    operations,
    "output/operations.csv"
)

# Write wagon analysis
ExcelWriter.write_wagon_analysis(
    wagon_report,
    "output/wagon_analysis.csv"
)

# Write executive summary
ExcelWriter.write_summary(
    scenario,
    operations,
    wagon_report,
    "output/summary.csv"
)
```

### Complete Workflow

```python
from terminal_optimizer.excel_io import ExcelReader, ExcelWriter
from terminal_optimizer.sequence_generator import PalmSequenceGenerator, SunflowerHandler
from terminal_optimizer.wagon_manager import WagonManager

# Step 1: Load scenario
scenario = ExcelReader.load_scenario(
    vessels_file="input/vessels.csv",
    inventory_file="input/inventory.csv"
)

# Step 2: Generate sequences
palm_gen = PalmSequenceGenerator(scenario.tanks)
sun_handler = SunflowerHandler(scenario.tanks)

operations = []
for vessel in scenario.vessels:
    if vessel.cargo_type.value == "palm":
        # Generate palm sequence
        large, small = palm_gen.classify_fractions(vessel)
        allocations = palm_gen.allocate_lines(large, small)
        tank_allocs = palm_gen.allocate_tanks(allocations, scenario.current_inventory)
        ops = palm_gen.generate_sequence(vessel, tank_allocs, 
                                         scenario.current_inventory, vessel.eta)
        operations.extend(ops)
    else:
        # Generate sunflower sequence
        s_start = sun_handler.calculate_critical_start_point(
            vessel.total_volume, 195.0, 700.0
        )
        accum_ops = sun_handler.generate_accumulation_plan(
            s_start, scenario.rail_schedule, scenario.current_inventory,
            vessel.eta - timedelta(days=14)
        )
        load_ops = sun_handler.generate_loading_plan(
            vessel, scenario.current_inventory, vessel.eta
        )
        operations.extend(accum_ops)
        operations.extend(load_ops)

# Step 3: Analyze wagons
wagon_mgr = WagonManager(season=scenario.parameters.get("season", "summer"))
wagon_report = wagon_mgr.generate_wagon_report(operations)

# Step 4: Export results
ExcelWriter.write_operations(operations, "output/operations.csv")
ExcelWriter.write_wagon_analysis(wagon_report, "output/wagons.csv")
ExcelWriter.write_summary(scenario, operations, wagon_report, "output/summary.csv")

print(f"✓ Generated {len(operations)} operations")
print(f"✓ External wagon cost: {wagon_report['total_external_cost']:,.0f} RUB")
```

## Next Steps (Phase 4)

The following components remain to be implemented:

1. **Balance Calculator** (TODOLIST 3)
   - Tank balance simulation
   - Flow rate calculations
   - Capacity validation
   - Product segregation checks

2. **Validation Engine** (TODOLIST 7)
   - Physical constraint validation
   - Operational rule checking
   - Business rule enforcement
   - Comprehensive violation reporting

3. **Risk Analysis** (TODOLIST 8)
   - Wagon availability forecasting (Markov model)
   - Risk identification
   - Recommendation generation

4. **Main Application** (TODOLIST 9)
   - Pipeline orchestration
   - User edit handling
   - End-to-end integration

## Performance Characteristics

- **Wagon Calculation**: O(n) where n = number of operations
- **Daily Distribution**: O(n log n) for sorting operations by date
- **Batch Creation**: O(d × b) where d = days, b = batches per day
- **Looping Tracking**: O(n) linear scan of operations
- **Gap Detection**: O(n × p) where p = wagon pool entries

## Files Modified/Created

- ✅ Created: [`terminal_optimizer/wagon_manager.py`](../terminal_optimizer/wagon_manager.py) (476 lines)
- ✅ Created: [`terminal_optimizer/excel_io.py`](../terminal_optimizer/excel_io.py) (518 lines)
- ✅ Created: [`tests/test_wagon_manager.py`](../tests/test_wagon_manager.py) (293 lines)
- ✅ Created: [`tests/test_excel_io.py`](../tests/test_excel_io.py) (380 lines)
- ✅ Created: [`docs/PHASE3_SUMMARY.md`](PHASE3_SUMMARY.md) (this file)

## Validation

All 23 Phase 3 tests pass successfully:
- ✅ Wagon requirement calculation
- ✅ Batch distribution
- ✅ Looping logic and wagon transformation
- ✅ Gap detection and external ordering
- ✅ CSV reading for all input types
- ✅ CSV writing for all output types
- ✅ Date format parsing
- ✅ Complete scenario loading

---

**Phase 3 Status: ✅ COMPLETE**

Ready to proceed to Phase 4 (Balance Calculator & Validation Engine).
