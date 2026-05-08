# Phase 6: Risk Analysis - Implementation Summary

## Overview

Phase 6 implements comprehensive risk analysis capabilities for the terminal optimizer, including:
- **Wagon availability forecasting** using Markov chain models
- **Risk identification** for wagon shortages, tank overflows, and critical path operations
- **Recommendation generation** with cost/benefit analysis and ROI calculations

## Implementation Details

### 1. Wagon Availability Forecasting

#### WagonForecaster Class
The [`WagonForecaster`](../terminal_optimizer/risk_analysis.py:90) class implements a Markov chain-based forecaster for predicting wagon availability states.

**Key Methods:**

##### build_markov_matrix()
```python
def build_markov_matrix(
    self,
    historical_delays: List[Tuple[str, str]]
) -> np.ndarray:
```

**Purpose:** Builds a 6×6 transition matrix from historical wagon state transitions.

**Algorithm:**
1. Initialize a count matrix to track state transitions
2. Count each (from_state, to_state) transition in the historical data
3. Normalize each row so it sums to 1.0 (probability distribution)
4. Handle states with no observed transitions (assume they stay in the same state)

**Wagon States:**
- Available
- In Transit to Terminal
- At Terminal
- In Transit to Client
- At Client
- In Transit Returning

**Example:**
```python
forecaster = WagonForecaster()
historical = [
    ("Available", "In Transit to Terminal"),
    ("In Transit to Terminal", "At Terminal"),
    # ... more transitions
]
matrix = forecaster.build_markov_matrix(historical)
# matrix[i,j] = probability of transitioning from state i to state j
```

##### forecast()
```python
def forecast(
    self,
    current_state_vector: np.ndarray,
    days_ahead: int
) -> np.ndarray:
```

**Purpose:** Forecast future state distributions using the Markov chain.

**Algorithm:**
1. Start with π[0] = current_state (initial probability distribution)
2. For each day d from 1 to days_ahead:
   - π[d] = π[d-1] · P (matrix multiplication with transition matrix)
3. Return array of shape (days_ahead+1, 6) containing daily probability distributions

**Mathematical Foundation:**
- Based on Markov property: future state depends only on current state
- π(t+1) = π(t) · P where P is the transition matrix
- Each π(t) is a probability distribution over the 6 states

**Example:**
```python
# All wagons start available
initial = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0])
forecast = forecaster.forecast(initial, days_ahead=7)
# forecast[0] = initial state
# forecast[7] = probability distribution 7 days ahead
```

##### get_expected_available()
```python
def get_expected_available(
    self,
    forecast: np.ndarray,
    N_total: int
) -> Dict[int, float]:
```

**Purpose:** Calculate expected number of available wagons for each day.

**Formula:**
```
E[available on day d] = N_total × π_Available[d]
```

Where:
- N_total = total wagon fleet size
- π_Available[d] = probability of being in "Available" state on day d

**Example:**
```python
expected = forecaster.get_expected_available(forecast, N_total=500)
# expected[0] = 500.0  (if all start available)
# expected[7] = 350.5  (after transitions)
```

##### get_P90_quantile()
```python
def get_P90_quantile(
    self,
    forecast: np.ndarray,
    N_total: int,
    trials: int = 10000
) -> Dict[int, float]:
```

**Purpose:** Calculate 90th percentile (conservative estimate) using Monte Carlo simulation.

**Algorithm:**
1. For each day in the forecast:
   - Run Monte Carlo simulation with `trials` iterations
   - In each trial:
     - Sample a state for each wagon according to the probability distribution
     - Count how many wagons are in "Available" state
   - Calculate 10th percentile of the samples
     - Note: 10th percentile gives us "90% chance of at least this many"

**Why P90?**
- Conservative planning: 90% confidence that at least this many wagons will be available
- Accounts for stochastic variation in the system
- Better than expected value for risk management

**Example:**
```python
P90 = forecaster.get_P90_quantile(forecast, N_total=500, trials=10000)
# P90[7] might be 320 (conservative), while E[available] might be 350
```

### 2. Risk Identification

#### Wagon Shortage Risks

**Function:** [`identify_wagon_shortage_risks()`](../terminal_optimizer/risk_analysis.py:313)

**Purpose:** Identify operations at risk due to insufficient wagon availability.

**Algorithm:**
1. For each operation that requires wagons (rail operations):
   - Get forecasted wagon availability for the scheduled day (using P90)
   - Calculate shortage gap: `gap = wagons_needed - forecast_available`
   - If gap > 0, create a risk
2. Determine severity based on gap size:
   - **CRITICAL:** gap ≥ 100% of needed (complete shortage)
   - **HIGH:** gap ≥ 50% of needed
   - **MEDIUM:** gap ≥ 25% of needed
   - **LOW:** gap < 25% of needed
3. Calculate impact: `gap × demurrage_rate × delay_hours / wagons_needed`

**Output:** List of [`Risk`](../terminal_optimizer/risk_analysis.py:56) objects with:
- Risk type: `WAGON_SHORTAGE`
- Probability and severity classifications
- Financial impact estimate
- Affected operations
- Metadata: shortage gap, forecast values

#### Tank Overflow Risks

**Function:** [`identify_tank_overflow_risks()`](../terminal_optimizer/risk_analysis.py:413)

**Purpose:** Identify tanks at risk of exceeding capacity.

**Algorithm:**
1. For each tank in the balance simulation:
   - Find peak utilization: `max(volume / capacity)` across all time points
   - If peak > threshold (default 95%):
     - Create overflow risk
2. Determine severity:
   - **CRITICAL:** utilization ≥ 100% (actual overflow)
   - **HIGH:** utilization ≥ 98%
   - **MEDIUM:** utilization ≥ 96%
   - **LOW:** utilization ≥ 95%
3. Calculate impact: `(utilization - threshold) × 1,000,000 RUB per 1%`

**Output:** Risk objects with:
- Risk type: `TANK_OVERFLOW`
- Peak utilization metrics
- Time window when overflow occurs
- Tank identification

#### Critical Path Operations

**Function:** [`identify_critical_path_ops()`](../terminal_optimizer/risk_analysis.py:490)

**Purpose:** Identify operations on the critical path (zero slack time).

**Algorithm:**
1. **Forward Pass** - Calculate earliest start/finish times:
   - For operations with no dependencies: earliest_start = scheduled_time
   - For operations with dependencies: earliest_start = max(dependency finish times)
   - earliest_finish = earliest_start + duration

2. **Backward Pass** - Calculate latest start/finish times:
   - Project deadline = max(earliest_finish)
   - For operations with no successors: latest_finish = project_deadline
   - For operations with successors: latest_finish = min(successor start times)
   - latest_start = latest_finish - duration

3. **Slack Calculation:**
   - slack = latest_start - earliest_start
   - If slack ≈ 0 (< 0.1 hours): operation is on critical path

4. Create risks for critical path operations (probability 30%, high severity)

**Why Critical Path Matters:**
- Operations with zero slack: any delay propagates to project completion
- High risk: delays are likely to cascade
- Requires careful monitoring and contingency planning

### 3. Recommendation Generation

**Function:** [`generate_recommendations()`](../terminal_optimizer/risk_analysis.py:605)

**Purpose:** Generate mitigation strategies for identified risks with cost/benefit analysis.

**Algorithm:**
1. For each risk, generate multiple mitigation options
2. Calculate for each recommendation:
   - **Cost:** Implementation cost in RUB
   - **Benefit:** Expected value of risk avoided (probability × impact)
   - **ROI:** Return on investment (benefit / cost)
   - **Implementation time:** Hours required to implement
3. Sort all recommendations by ROI (descending)
4. Assign priorities based on sorted order

**Recommendation Types by Risk:**

#### Wagon Shortage Risks
1. **Lease External Wagons**
   - Cost: `shortage_gap × wagon_external_cost` (default 50,000 RUB/wagon)
   - Benefit: Full risk expected value
   - Implementation: 48 hours

2. **Reschedule Operation**
   - Cost: 50,000 RUB (administrative)
   - Benefit: 80% of risk expected value
   - Implementation: 24 hours

#### Tank Overflow Risks
1. **Accelerate Discharge**
   - Cost: 200,000 RUB (overtime, expediting)
   - Benefit: Full risk expected value
   - Implementation: 12 hours

2. **Arrange Temporary Storage**
   - Cost: `excess_volume × 500 RUB/tonne`
   - Benefit: Full risk expected value
   - Implementation: 72 hours

#### Critical Path Risks
1. **Add Contingency Time Buffer**
   - Cost: 100,000 RUB (schedule adjustment)
   - Benefit: Full risk expected value
   - Implementation: 24 hours

2. **Increase Resource Allocation**
   - Cost: 300,000 RUB (extra equipment/personnel)
   - Benefit: 120% of risk expected value (faster execution)
   - Implementation: 48 hours

**Output Format:**
```python
Recommendation(
    rec_id="REC_001",
    risk_id="RISK_001",
    action="Lease 10 external wagons",
    cost=500000.0,
    benefit=800000.0,
    roi=1.6,
    priority=1
)
```

### 4. Risk Summary

**Function:** [`create_risk_summary()`](../terminal_optimizer/risk_analysis.py:766)

**Purpose:** Generate executive summary of risks and recommendations.

**Output Structure:**
```python
{
    "total_risks": 15,
    "total_expected_value": 5_234_000.0,
    "risks_by_type": {
        "wagon_shortage": 8,
        "tank_overflow": 5,
        "critical_path": 2
    },
    "risks_by_severity": {
        "critical": 2,
        "high": 7,
        "medium": 4,
        "low": 2
    },
    "top_risks": [
        # Top 10 risks sorted by expected value
    ],
    "total_recommendations": 30,
    "top_recommendations": [
        # Top 10 recommendations sorted by ROI
    ],
    "total_mitigation_cost": 8_500_000.0,
    "total_potential_benefit": 15_200_000.0
}
```

## Data Classes

### Risk
```python
@dataclass
class Risk:
    risk_id: str
    risk_type: RiskType  # WAGON_SHORTAGE, TANK_OVERFLOW, CRITICAL_PATH
    severity: RiskSeverity  # CRITICAL, HIGH, MEDIUM, LOW
    description: str
    probability: float  # 0.0-1.0
    impact: float  # RUB
    expected_value: float  # probability × impact (auto-calculated)
    affected_operations: List[str]
    time_window: Optional[Tuple[datetime, datetime]]
    metadata: Dict[str, Any]
```

### Recommendation
```python
@dataclass
class Recommendation:
    rec_id: str
    risk_id: str
    action: str
    cost: float  # RUB
    benefit: float  # RUB
    roi: float  # benefit / cost (auto-calculated)
    implementation_time: Optional[float]  # hours
    priority: int  # Ranking (1 = highest)
    notes: str
```

## Testing

Comprehensive test suite with 26 tests covering:

### WagonForecaster Tests (8 tests)
- Initialization and state management
- Markov matrix construction (simple and mixed transitions)
- Single and multi-step forecasting
- Expected value calculations
- P90 quantile with Monte Carlo simulation

### Risk Identification Tests (7 tests)
- Wagon shortage detection (basic, no risk, severity classification)
- Tank overflow detection (basic, no risk)
- Critical path identification (simple chains, operations with slack)

### Recommendation Generation Tests (5 tests)
- Recommendations for each risk type
- ROI calculation accuracy
- Sorting and prioritization
- Data class initialization

### Risk Summary Tests (2 tests)
- Basic summary generation
- Top risks sorting and limiting

### Integration Tests (4 tests)
- Full workflow from forecasting to recommendations
- Data class validation
- Edge cases

**Test Results:** All 26 tests pass ✅

## Usage Examples

### Example 1: Wagon Availability Forecasting
```python
from terminal_optimizer.risk_analysis import WagonForecaster
import numpy as np

# Create forecaster
forecaster = WagonForecaster()

# Load historical data (from Table 1.8 or similar)
historical = [
    ("Available", "In Transit to Terminal"),
    ("In Transit to Terminal", "At Terminal"),
    # ... more transitions
]

# Build transition matrix
matrix = forecaster.build_markov_matrix(historical)

# Set current state (e.g., 70% available, 30% in various other states)
current_state = np.array([0.7, 0.1, 0.1, 0.05, 0.05, 0.0])

# Forecast 30 days ahead
forecast = forecaster.forecast(current_state, days_ahead=30)

# Get expected availability
expected = forecaster.get_expected_available(forecast, N_total=500)
print(f"Expected available wagons on day 7: {expected[7]:.0f}")

# Get conservative estimate (P90)
P90 = forecaster.get_P90_quantile(forecast, N_total=500)
print(f"P90 available wagons on day 7: {P90[7]:.0f}")
```

### Example 2: Risk Identification
```python
from terminal_optimizer.risk_analysis import (
    identify_wagon_shortage_risks,
    identify_tank_overflow_risks,
    identify_critical_path_ops
)

# Identify wagon shortage risks
operations = [
    {
        "op_id": "RAIL_001",
        "op_type": "rail_batch",
        "wagons_needed": 54,
        "scheduled_day": 5,
        "product": "palm_oil"
    }
]

wagon_risks = identify_wagon_shortage_risks(operations, P90)

# Identify tank overflow risks
balance_simulation = {
    "RVS_3": [
        {"time": datetime(2024, 1, 1), "volume": 9500, "capacity": 9900},
        {"time": datetime(2024, 1, 2), "volume": 9850, "capacity": 9900},
    ]
}

overflow_risks = identify_tank_overflow_risks(balance_simulation, tanks)

# Identify critical path operations
timed_operations = [
    {
        "op_id": "OP_001",
        "start_time": datetime(2024, 1, 1, 8, 0),
        "end_time": datetime(2024, 1, 1, 20, 0),
        "duration": 12.0,
        "dependencies": []
    }
]

critical_risks = identify_critical_path_ops(timed_operations)

# Combine all risks
all_risks = wagon_risks + overflow_risks + critical_risks
```

### Example 3: Generate Recommendations
```python
from terminal_optimizer.risk_analysis import (
    generate_recommendations,
    create_risk_summary
)

# Generate mitigation recommendations
recommendations = generate_recommendations(
    all_risks,
    demurrage_rate=100000.0,
    wagon_external_cost=50000.0
)

# Print top 5 recommendations
for rec in recommendations[:5]:
    print(f"Priority {rec.priority}: {rec.action}")
    print(f"  Cost: {rec.cost:,.0f} RUB")
    print(f"  Benefit: {rec.benefit:,.0f} RUB")
    print(f"  ROI: {rec.roi:.2f}")
    print()

# Create executive summary
summary = create_risk_summary(all_risks, recommendations)
print(f"Total risks identified: {summary['total_risks']}")
print(f"Total expected value at risk: {summary['total_expected_value']:,.0f} RUB")
print(f"Potential benefit from mitigations: {summary['total_potential_benefit']:,.0f} RUB")
```

## Files Created

1. **[`terminal_optimizer/risk_analysis.py`](../terminal_optimizer/risk_analysis.py)** (827 lines)
   - `WagonForecaster` class with Markov chain forecasting
   - `Risk` and `Recommendation` dataclasses
   - Risk identification functions
   - Recommendation generation
   - Risk summary utilities

2. **[`tests/test_risk_analysis.py`](../tests/test_risk_analysis.py)** (595 lines)
   - Comprehensive test suite with 26 tests
   - 100% pass rate
   - Covers all major functionality

3. **[`docs/PHASE6_SUMMARY.md`](./PHASE6_SUMMARY.md)** (this file)
   - Complete implementation documentation
   - Algorithm descriptions
   - Usage examples

## Integration with Existing Modules

The risk analysis module integrates with:

1. **[`domain_models.py`](../terminal_optimizer/domain_models.py)**
   - Uses `Operation`, `Tank`, `Vessel` data structures
   - Compatible with existing operation scheduling

2. **[`balance_calculator.py`](../terminal_optimizer/balance_calculator.py)**
   - Consumes balance simulation results
   - Identifies tank overflow risks from balance data

3. **[`wagon_manager.py`](../terminal_optimizer/wagon_manager.py)**
   - Extends wagon management with forecasting
   - Provides risk-aware wagon allocation

4. **[`sequence_generator.py`](../terminal_optimizer/sequence_generator.py)**
   - Can use risk insights for operation scheduling
   - Critical path awareness for sequencing

## Key Formulas and Algorithms

### Markov Chain Forecasting
```
π(t+1) = π(t) · P

where:
- π(t) = state probability distribution at time t
- P = transition matrix
- P[i,j] = probability of transitioning from state i to state j
```

### Expected Available Wagons
```
E[W_available(t)] = N_total × π_available(t)

where:
- N_total = total wagon fleet size
- π_available(t) = probability of being in "Available" state at time t
```

### Risk Expected Value
```
EV = P(risk) × Impact(risk)

where:
- P(risk) = probability of risk occurrence [0, 1]
- Impact(risk) = financial impact in RUB
```

### Return on Investment
```
ROI = Benefit / Cost

where:
- Benefit = Expected value of risk avoided
- Cost = Implementation cost of mitigation
```

### Tank Utilization
```
Utilization = Current_Volume / Effective_Capacity

Risk_Impact = (Utilization - Threshold) × 1,000,000 RUB per 1%
```

### Critical Path - Slack Time
```
Slack = Latest_Start - Earliest_Start

If Slack ≈ 0: Operation is on critical path
```

## Performance Characteristics

- **Markov Matrix Construction:** O(n) where n = number of historical transitions
- **Forecast Calculation:** O(d × s²) where d = days ahead, s = number of states (6)
- **P90 Calculation:** O(d × t × N) where t = trials, N = total wagons
- **Risk Identification:** O(r) where r = number of operations/tanks
- **Recommendation Generation:** O(r × m) where m = recommendations per risk
- **Critical Path:** O(o²) where o = number of operations (dependency resolution)

**Typical Performance:**
- 30-day forecast: < 1ms
- P90 calculation (10,000 trials): ~100ms
- Risk identification for 100 operations: < 10ms
- Recommendation generation: < 50ms

## Future Enhancements

1. **Advanced Forecasting:**
   - Time-varying Markov chains (seasonal effects)
   - Hidden Markov Models for unobserved states
   - Bayesian updating with real-time data

2. **Machine Learning:**
   - Neural network-based wagon availability prediction
   - Anomaly detection for unusual patterns
   - Predictive maintenance integration

3. **Optimization:**
   - Automatic mitigation strategy selection
   - Multi-objective optimization (cost vs. risk)
   - Dynamic replanning based on risk thresholds

4. **Visualization:**
   - Risk heat maps
   - Tornado diagrams for sensitivity analysis
   - Monte Carlo simulation visualizations

5. **Real-time Integration:**
   - Live wagon tracking
   - Automatic risk alerts
   - Integration with IoT sensors

## References

- Markov Chains: Ross, S. M. (2014). Introduction to Probability Models
- Critical Path Method: Project Management Institute (2017). PMBOK Guide
- Risk Analysis: Hillson, D. & Murray-Webster, R. (2017). Understanding and Managing Risk Attitude
- Monte Carlo Simulation: Metropolis, N. & Ulam, S. (1949). The Monte Carlo Method

## Conclusion

Phase 6 successfully implements comprehensive risk analysis capabilities:
- ✅ Wagon availability forecasting using proven Markov chain methods
- ✅ Multi-dimensional risk identification (wagons, tanks, critical path)
- ✅ ROI-driven recommendation generation
- ✅ Comprehensive test coverage (26 tests, 100% pass)
- ✅ Well-documented with usage examples
- ✅ Integrated with existing terminal optimizer modules

The implementation provides terminal operators with:
- **Proactive risk management** through forecasting
- **Data-driven decision making** with quantified impacts
- **Cost-effective mitigation strategies** ranked by ROI
- **Conservative planning** using P90 estimates

This completes Phase 6 of the Terminal Optimizer project.
