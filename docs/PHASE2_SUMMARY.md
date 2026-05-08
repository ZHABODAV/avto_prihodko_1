# Phase 2 Implementation Summary

## Overview

Phase 2 (Sequence Generator) has been successfully completed. This phase implements the core logic for generating operational sequences for both palm oil discharge and sunflower oil loading operations.

## Components Delivered

### 1. PalmSequenceGenerator Class
Location: [`terminal_optimizer/sequence_generator.py`](../terminal_optimizer/sequence_generator.py:78)

**Key Features:**
- **Fraction Classification**: Automatically classifies palm fractions into large (>5000t) and small (≤5000t) categories
- **Line Allocation**: Assigns large fractions to Line1 (900 t/h) and small fractions to Line2 (500 t/h or 146 t/h direct)
- **Tank Assignment**: Allocates fractions to appropriate tanks (RVS-3, RVS-5, or SHT)
- **Cleaning Operations**: Automatically inserts cleaning operations when product changes require them
- **Parallel Processing**: Supports simultaneous Line1 and Line2 operations

**Methods:**
- [`classify_fractions()`](../terminal_optimizer/sequence_generator.py:109): Splits fractions by size and priority
- [`allocate_lines()`](../terminal_optimizer/sequence_generator.py:140): Assigns fractions to discharge lines
- [`allocate_tanks()`](../terminal_optimizer/sequence_generator.py:173): Determines tank allocation for each fraction
- [`generate_sequence()`](../terminal_optimizer/sequence_generator.py:240): Creates complete operation sequence

**Palm Fraction Priorities:**
```python
PALM_FRACTION_PRIORITIES = {
    "palm_oil": 10,
    "palm_oil_low3mcpd": 9,
    "palm_olein": 8,
    "palm_olein_low3mcpd": 7,
    "palm_stearin": 6,
    "palm_pfad": 5,
}
```

### 2. SunflowerHandler Class
Location: [`terminal_optimizer/sequence_generator.py`](../terminal_optimizer/sequence_generator.py:382)

**Key Features:**
- **Critical Point Calculation**: Implements the "critical starting volume" algorithm
- **Capacity Checking**: Validates if sufficient tank capacity is available (RVS-1, RVS-2, optionally RVS-5)
- **Accumulation Planning**: Generates rail discharge operations to build required inventory
- **Loading Plans**: Creates ship loading operations with optional direct rail variant

**Methods:**
- [`calculate_critical_start_point()`](../terminal_optimizer/sequence_generator.py:406): Calculates minimum tank volume needed
- [`check_capacity_available()`](../terminal_optimizer/sequence_generator.py:438): Validates tank capacity
- [`generate_accumulation_plan()`](../terminal_optimizer/sequence_generator.py:499): Creates rail discharge operations
- [`generate_loading_plan()`](../terminal_optimizer/sequence_generator.py:575): Creates ship loading operations

**Critical Point Algorithm:**
```
T_loading = vessel_volume / ship_rate
rail_contribution = rail_rate × T_loading
S_start = vessel_volume - rail_contribution
S_start_safe = S_start × (1 + safety_margin)
```

### 3. SequenceCoordinator Class
Location: [`terminal_optimizer/sequence_generator.py`](../terminal_optimizer/sequence_generator.py:644)

**Key Features:**
- **Sequence Merging**: Combines multiple vessel sequences into unified timeline
- **Conflict Detection**: Identifies resource conflicts (tanks, berth, rail platform)
- **Conflict Resolution**: Automatically reschedules operations to eliminate conflicts
- **Priority Handling**: Respects user-locked operations during rescheduling

**Methods:**
- [`merge_sequences()`](../terminal_optimizer/sequence_generator.py:660): Combines operation lists
- [`check_conflicts()`](../terminal_optimizer/sequence_generator.py:678): Detects overlapping resource usage
- [`resolve_conflict()`](../terminal_optimizer/sequence_generator.py:729): Resolves individual conflicts
- [`resolve_all_conflicts()`](../terminal_optimizer/sequence_generator.py:764): Iteratively resolves all conflicts

**Conflict Types Detected:**
- Tank resource conflicts (same tank, overlapping time)
- Berth conflicts (multiple vessels at once)
- Rail platform conflicts (too many batches)

## Test Coverage

Comprehensive test suite created in [`tests/test_sequence_generator.py`](../tests/test_sequence_generator.py)

### Test Classes:

1. **TestPalmSequenceGenerator** (11 tests)
   - Fraction classification (large/small)
   - Priority sorting
   - Line allocation (Line1/Line2)
   - Direct discharge for very small fractions
   - Tank preference (RVS-3, RVS-5, SHT)
   - Complete sequence generation
   - Operation types (berthing, discharge, unberthing)

2. **TestSunflowerHandler** (10 tests)
   - Critical point calculation
   - Capacity checking (with/without RVS-5)
   - Existing inventory handling
   - Accumulation plan generation
   - Loading plan (standard and direct variant)

3. **TestSequenceCoordinator** (7 tests)
   - Sequence merging
   - Conflict detection
   - Sequential operations (no conflict)
   - Conflict resolution by delay
   - Locked operation priority
   - Iterative conflict resolution

4. **TestSequenceGeneratorIntegration** (3 tests)
   - End-to-end palm workflow
   - End-to-end sunflower workflow
   - Combined palm + sunflower coordination

**Total: 31 comprehensive tests**

## Key Algorithms Implemented

### 1. Palm Fraction Classification
- Threshold: 5000 tonnes
- Large fractions → Line1 (900 t/h, goes to RVS-3 or RVS-5)
- Small fractions → Line2 (500 t/h via SHT, or 146 t/h direct to rail)
- Very small (<2000t) → Direct discharge to rail

### 2. Sunflower Critical Point
- Calculates minimum tank volume needed before ship loading begins
- Accounts for parallel rail contribution during loading
- Includes safety margin (default 10%)
- Determines if RVS-5 swing tank is needed

### 3. Conflict Resolution
- Detects resource overlaps (tanks, berth, rails)
- Resolves by delaying lower-priority operations
- Respects user-locked operations
- Iterates up to N times until all conflicts resolved

## Usage Examples

### Palm Vessel Sequence Generation

```python
from terminal_optimizer.sequence_generator import PalmSequenceGenerator
from terminal_optimizer.domain_models import create_standard_tanks

# Initialize
tanks = create_standard_tanks()
generator = PalmSequenceGenerator(tanks, parameters)

# Classify fractions
large_fractions, small_fractions = generator.classify_fractions(palm_vessel)

# Allocate to lines
line_allocations = generator.allocate_lines(large_fractions, small_fractions)

# Allocate to tanks
tank_allocations = generator.allocate_tanks(line_allocations, current_inventory)

# Generate complete sequence
operations = generator.generate_sequence(
    vessel=palm_vessel,
    allocations=tank_allocations,
    current_inventory=current_inventory,
    start_time=vessel.eta
)
```

### Sunflower Vessel Sequence Generation

```python
from terminal_optimizer.sequence_generator import SunflowerHandler

# Initialize
handler = SunflowerHandler(tanks, parameters)

# Calculate requirements
s_start = handler.calculate_critical_start_point(
    vessel_volume=35000.0,
    rail_rate=195.0,
    ship_rate=700.0,
    safety_margin=0.10
)

# Check capacity
is_feasible, gap, uses_rvs5 = handler.check_capacity_available(
    s_start_needed=s_start,
    current_inventory=inventory
)

# Generate accumulation plan
accum_ops = handler.generate_accumulation_plan(
    s_start_needed=s_start,
    rail_schedule=rail_deliveries,
    current_inventory=inventory,
    start_time=start_date
)

# Generate loading plan
loading_ops = handler.generate_loading_plan(
    vessel=sunflower_vessel,
    tank_status=inventory,
    start_time=load_date,
    use_direct_variant=False
)
```

### Coordinating Multiple Vessels

```python
from terminal_optimizer.sequence_generator import SequenceCoordinator

# Initialize coordinator
coordinator = SequenceCoordinator(tanks, parameters)

# Merge sequences
all_operations = coordinator.merge_sequences([palm_ops, sunflower_ops])

# Resolve conflicts
resolved_ops, warnings = coordinator.resolve_all_conflicts(all_operations)

# Check final state
remaining_conflicts = coordinator.check_conflicts(resolved_ops)
if not remaining_conflicts:
    print("All conflicts resolved successfully!")
```

## Integration with Phase 1

Phase 2 builds directly on Phase 1 components:

- **Uses [`Tank`](../terminal_optimizer/domain_models.py:113)** for capacity checks and cleaning duration calculations
- **Uses [`Vessel`](../terminal_optimizer/domain_models.py:439)** for cargo plan parsing and fraction extraction
- **Creates [`Operation`](../terminal_optimizer/domain_models.py:623)** objects for each step in the sequence
- **Leverages** product compatibility matrix from domain models

## Next Steps (Phase 3)

The following components remain to be implemented:

1. **Wagon Manager** (TODOLIST 4)
   - Wagon requirement calculation
   - Batch distribution
   - Looping logic (sunflower → palm wagon reuse)

2. **Flow-Through Handler** (TODOLIST 5)
   - Direct rail variant calculations
   - Capacity checks for large vessels

3. **Excel I/O** (TODOLIST 6)
   - Read input data from Excel
   - Write results to Excel output

## Key Decisions Made

1. **Large Fraction Threshold**: Set at 5000 tonnes (configurable constant)
2. **Safety Margin**: Default 10% for sunflower critical point
3. **Conflict Resolution**: Delay-based strategy (preserves locked operations)
4. **Direct Discharge**: Enabled for fractions <2000 tonnes
5. **Shore Tank**: SHT exclusively for Line2 non-direct fractions

## Performance Characteristics

- **Classification**: O(n log n) where n = number of fractions
- **Conflict Detection**: O(m²) where m = number of operations per resource
- **Conflict Resolution**: O(k × m²) where k = max iterations (default 10)

## Files Modified

- ✅ Created: [`terminal_optimizer/sequence_generator.py`](../terminal_optimizer/sequence_generator.py) (789 lines)
- ✅ Created: [`tests/test_sequence_generator.py`](../tests/test_sequence_generator.py) (728 lines)
- ✅ Created: [`docs/PHASE2_SUMMARY.md`](PHASE2_SUMMARY.md) (this file)

## Validation

All 31 tests pass successfully:
- ✅ Palm sequence generation
- ✅ Sunflower critical point calculation
- ✅ Capacity checking
- ✅ Conflict detection and resolution
- ✅ Integration workflows

---

**Phase 2 Status: ✅ COMPLETE**

Ready to proceed to Phase 3 (Wagon Manager & Excel I/O).
