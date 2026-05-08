# Methodology: Terminal Optimizer

## Mathematical Model and Algorithms

This document describes the mathematical foundation, algorithms, and business rules underlying the Terminal Optimizer system.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Mathematical Model](#mathematical-model)
3. [Algorithms](#algorithms)
4. [Constraints](#constraints)
5. [Assumptions and Limitations](#assumptions-and-limitations)
6. [Validation Rules](#validation-rules)

---

## 1. System Architecture

### 1.1 Four-Layer Design

The terminal optimization system is structured in four layers:

#### Layer 1: Terminal Physics

**Physical infrastructure and capacities**

- **Tank Farm**: RVS 1-5, SHT (Shore Tank)
  - RVS-1, RVS-2: 9,900t each (sunflower dedicated)
  - RVS-3: 9,900t (palm dedicated)
  - RVS-5: 2,700t (swing tank: sunflower OR palm)
  - SHT: 2,700t (palm shore tank)

- **Pipeline Network**:
  - Line 1 (Main): 900 t/h capacity → RVS-3, RVS-5
  - Line 2 (Auxiliary): 500 t/h to tanks, 146 t/h direct to rail → SHT or Rail

- **Berths**: Separate for palm import and sunflower export

#### Layer 2: Operations Logistics

**Operational constraints and timing**

- **Railway Platform**: 4 batches/day max, 18 wagons/batch (hard limit)
- **Maneuver Cycles**: Discharge/loading + preparation time
- **Wagon Looping**: Sunflower → prep → palm (reuse empty wagons)
- **Berth Shifting**: 1.5h (summer) / 3h (winter) between products

#### Layer 3: Supply Chain

**External network and stochastic elements**

- **Wagon Fleet**: Total N wagons in circulation
- **Lead Times**: Factory → Terminal, Terminal → Clients
- **Railway Statistics**: Delay distributions (for Markov forecasting)
- **Client Demand**: Weekly demand matrix

#### Layer 4: Decision Support

**User interface and optimization**

- **Sequence Management**: Auto-generation + manual editing
- **Two-Stage Optimization**: Time minimization → Cost minimization
- **Risk Alerts**: Probability-based warnings

### 1.2 Data Flow

```
Input Data
    ↓
Validation
    ↓
Scenario Construction
    ↓
Sequence Generation (Heuristic)
    ↓
Balance Calculation
    ↓
Constraint Validation
    ↓
Risk Analysis (Markov Forecast)
    ↓
Output Generation
```

---

## 2. Mathematical Model

### 2.1 Notation

**Sets and Indices:**

| Symbol | Description |
|--------|-------------|
| `t ∈ T` | Time (hours) |
| `k ∈ K` | Tanks: {RVS_1, RVS_2, RVS_3, RVS_5, SHT} |
| `p ∈ P` | Products (sunflower, palm fractions) |
| `f ∈ F` | Palm fractions (up to 8 types) |
| `j ∈ J` | Vessels |
| `c ∈ C` | Clients |

**Constants:**

```
Tank Capacities (tonnes):
V_max[RVS_1] = V_max[RVS_2] = V_max[RVS_3] = 9,900
V_max[RVS_5] = V_max[SHT] = 2,700

Deadstock Ratios:
d[sunflower] = 0.10
d[palm_standard] = 0.10
d[palm_low3mcpd] = 0.15

Flow Rates (tonnes/hour):
Rate_ship_discharge[Line1] = 900
Rate_ship_discharge[Line2_tank] = 500
Rate_ship_discharge[Line2_direct] = 146
Rate_ship_load = 500-900 (variable)
Rate_rail_discharge[summer] = 195  (4×18×65÷24)
Rate_rail_discharge[winter] = 146  (3×18×65÷24)

Operation Times (hours):
T_berthing = 24 (minimum documentation time)
T_analysis = 72 (quality testing)
T_cleaning[sunflower ↔ palm] = 48
T_cleaning[standard ↔ low3mcpd] = 72
T_cleaning[from_low3mcpd] = 168
T_berth_shift = 1.5 (summer) / 3.0 (winter)
T_wagon_prep = 1.5 (inspection + wash)

Wagon Parameters:
Wagon_capacity = 65 tonnes
Wagons_per_batch = 18
Max_batches_per_day = 4
Wagon_reject_rate = 0.12 (12% fail inspection)
```

### 2.2 State Variables

**Continuous Variables:**

| Variable | Description | Units |
|----------|-------------|-------|
| `S[k,p,t]` | Stock of product p in tank k at time t | tonnes |
| `Q_in[k,p,t]` | Inflow to tank k of product p at time t | t/h |
| `Q_out[k,p,t]` | Outflow from tank k of product p at time t | t/h |

**Binary Variables (0/1):**

| Variable | Description |
|----------|-------------|
| `X[k,p,t]` | Tank k contains product p at time t |
| `Y_clean[k,t]` | Tank k is being cleaned at time t |
| `Z_berth[j,t]` | Vessel j is at berth at time t |

**Integer Variables:**

| Variable | Description |
|----------|-------------|
| `N_wagons[t]` | Number of wagons in operation at time t |
| `N_batches[d]` | Number of rail batches on day d |

### 2.3 Core Equations

#### Material Balance (Tank Inventory)

For each tank k, product p, time t:

```
S[k,p,t] = S[k,p,t-1] + Q_in[k,p,t] - Q_out[k,p,t]
```

**Initial Condition:**

```
S[k,p,0] = Initial_Inventory[k,p]
```

#### Capacity Constraint

```
0 ≤ S[k,p,t] ≤ V_max[k] × (1 - d[p])
```

Where `(1 - d[p])` accounts for deadstock that cannot be used.

#### Product Exclusivity

A tank can only contain one product at a time:

```
∑(p ∈ P) X[k,p,t] ≤ 1  for all k, t
```

#### Linking Continuous and Binary Variables

```
S[k,p,t] ≤ V_max[k] × X[k,p,t]
```

If `X[k,p,t] = 0`, then `S[k,p,t] = 0` (tank doesn't contain product p).

### 2.4 Vessel Cargo Plan Structure {H}

For a palm vessel j with n cargo holds:

```
Vessel[j] = {(H_1, fraction_1, volume_1), (H_2, fraction_2, volume_2), ..., (H_n, fraction_n, volume_n)}
```

**Example:**

```
Vessel "Victoria" with palm cargo:
H_1: Palm Oil, 12,000t
H_2: Palm Oil, 8,000t
H_3: Olein, 3,500t
H_4: Olein, 2,000t
H_5: Stearin, 1,500t
H_6: PFAD, 1,000t
Total: 28,000t
```

**Discharge Constraint:**

Fraction f from hold H_i can be discharged only if:

1. Hold H_i is accessible (not blocked by vessel structure)
2. A shore pipeline (Line1 or Line2) is available
3. A shore tank or rail capacity is available

### 2.5 Swing Tank (RVS-5) State Machine

**States:**

```
States(RVS_5) = {Empty, Sunflower, Palm, Cleaning}
```

**Transition Rules:**

If switching from sunflower to palm:

```
IF X[RVS_5, sunflower, t-1] = 1 AND X[RVS_5, palm, t] = 1
THEN:
    FOR τ ∈ [t - T_clean, t-1]:
        Y_clean[RVS_5, τ] = 1
        Q_in[RVS_5, *, τ] = 0
        Q_out[RVS_5, *, τ] = 0
```

Where `T_clean ∈ {48, 72, 168}` hours depending on product types.

### 2.6 Parallel Lines Model (Palm Discharge)

**Line 1 (Main):**

```
Ship → {RVS-3 OR RVS-5}
Rate: 900 t/h
```

**Line 2 (Auxiliary):**

```
Ship → {SHT OR Direct_to_Rail}
Rate: 500 t/h (to SHT) OR 146 t/h (direct)
```

**SHT Mutex Constraint:**

Cannot simultaneously fill and discharge SHT:

```
NOT (Q_ship→SHT[t] > 0 AND Q_SHT→rail[t] > 0)
```

**SHT Priority Rule:**

When SHT is >74% full (2,000t), prioritize discharging to rail:

```
IF S[SHT, t] > 2000:
    Priority(Q_SHT→rail) = MAXIMUM
    PAUSE Q_ship→SHT (if possible)
```

### 2.7 Wagon Circulation Model (Markov Chain)

**Wagon States:**

```
States = {Loading, EnRoute, Stuck, AtClient, Returning, Available}
```

**Transition Matrix Example:**

```
           Load  EnRt  Stuck AtCli Retr  Avbl
Loading  [  0    0.9   0.1    0     0     0  ]
EnRoute  [  0    0.6   0.15  0.25   0     0  ]
Stuck    [  0    0.5   0.4   0.1    0     0  ]
AtClient [  0     0     0    0.8   0.2    0  ]
Returning[  0     0     0     0    0.7   0.3 ]
Available[ 1.0    0     0     0     0     0  ]
```

**State Evolution:**

```
π(t+1) = π(t) × P
```

Where:

- `π(t)` = state distribution vector at time t
- `P` = transition probability matrix

**Forecast Available Wagons:**

```
E[N_available, t] = N_total × π_Available[t]
```

For conservative planning, use P90 quantile instead of expected value.

### 2.8 Objective Functions

#### Stage I: Minimize Time (Makespan)

```
min T_makespan = max over j ∈ J of (T_departure[j] - T_arrival[j])
```

**Goal:** Complete all vessel operations as quickly as possible.

#### Stage II: Minimize Cost

```
min Z = ∑(j ∈ J) C_dem[j] × weight[j] × Delay[j]
       + ∑(t ∈ T) C_ext × N_ext_wagons[t]
       + ∑(d ∈ D) C_batch_extra × max(0, N_batches[d] - 4)
       + ∑(c ∈ C) C_penalty[c] × Unmet[c]
```

**Cost Components:**

| Component | Weight | Description |
|-----------|---------|-------------|
| `C_dem` | 100,000 RUB/h | Demurrage (vessel delay) |
| `C_ext` | 50,000 RUB/wagon | External wagon rental |
| `C_batch_extra` | 50,000-150,000 RUB | Extra rail batch penalty |
| `C_penalty` | Client-dependent | Unmet demand penalty |

**Note:** Demurrage cost dominates (~800× other costs), so Stage I usually finds near-optimal Cost solution.

---

## 3. Algorithms

### 3.1 Heuristic Sequence Generation

For palm vessel discharge, allocate fractions using these rules:

**Rule 1: Large to Main Line**

```
FOR each fraction f in cargo_plan:
    IF volume[f] > 5,000 tonnes:
        Assign f → Line1 → {RVS-3 OR RVS-5}
    ELSE:
        Assign f → Line2 → {SHT OR Direct_to_Rail}
```

**Rule 2: SHT Priority**

```
WHILE ship_discharge_in_progress:
    IF S[SHT, t] > 2,000 tonnes:
        PAUSE Line2 ship discharge (if flexible)
        FORCE QT_SHT→rail[t] to maximum
    ELSE:
        RESUME Line2 discharge
```

**Rule 3: RVS-5 Allocation (Minimize Cleaning)**

```
IF total_sunflower > capacity(RVS_1 + RVS_2):  # 19,800t
    USE RVS-5 for sunflower
ELSE:
    PREFER keep RVS-5 for palm (avoid cleaning)
```

**Rule 4: Palm Fraction Priority**

Based on operational efficiency and client priority:

```
Priority Order:
1. palm_olein_low3mcpd  (highest quality)
2. palm_olein
3. palm_oil_low3mcpd
4. palm_oil
5. palm_stearin
6. palm_pfad  (lowest priority)
```

### 3.2 Flow-Through Logic (Sunflower Export)

For continuous loading while receiving rail deliveries.

**Critical Point Calculation:**

```
S_start = V_ship - (Rate_rail × T_loading)

Where:
T_loading = V_ship / Rate_ship_load
```

**Example:**

```
Given:
V_ship = 38,000 tonnes (vessel capacity)
Rate_ship = 700 t/h (ship loading rate)
Rate_rail = 195 t/h (rail delivery rate, summer)

Calculate:
T_loading = 38,000 / 700 = 54.3 hours
Rail_inflow_during_loading = 195 × 54.3 = 10,589 tonnes
S_start_required = 38,000 - 10,589 = 27,411 tonnes

With 10% safety margin:
S_start_safe = 27,411 × 1.10 = 30,152 tonnes

Check against capacity:
Capacity(RVS_1 + RVS_2) = 2 × 9,900 × 0.90 = 17,820 tonnes
Capacity(RVS_1 + RVS_2 + RVS_5) = 17,820 + 2,430 = 20,250 tonnes

Result: INSUFFICIENT! Need alternative:
Option A: Reduce ship_loading_rate to 600 t/h
Option B: Increase rail_delivery_rate (extra batches)
Option C: Start with higher initial inventory
```

### 3.3 Wagon Looping Algorithm

After discharging sunflower, wagons can be reused for palm loading.

**Transformation:**

```
W_palm_ready[t] = W_discharged[t - T_prep] × (1 - K_reject)

Where:
T_prep = 1.5 hours (inspection + washing + maneuvering)
K_reject = 0.12 (12% wagons fail inspection)
```

**Buy-or-Wait Decision:**

```
Gap[t] = Demand_palm[t] - (W_own_available[t] + W_returning[t])

IF Gap[t] > 0:
    Cost_wait = P(delay) × C_demurrage × E[Delay_hours]
    Cost_buy = Gap[t] × C_external_wagon
    
    IF Cost_buy < Cost_wait:
        Order external wagons
    ELSE:
        Accept risk and wait for own wagons
```

### 3.4 Sequence Validation Algorithm

After generating a sequence, validate feasibility:

**Validation Steps:**

1. **Capacity Check:**

   ```
   FOR each tank k, time t:
       IF S[k, t] > effective_capacity[k]:
           RAISE CapacityViolation
   ```

2. **Product Compatibility:**

   ```
   FOR each operation changing tank product:
       IF cleaning_required AND no_cleaning_operation_scheduled:
           RAISE CleaningRequired
   ```

3. **Resource Exclusivity:**

   ```
   FOR each pair of operations (i, j) on same resource:
       IF overlaps(i, j):
           RAISE ResourceConflict
   ```

4. **Precedence:**

   ```
   FOR each operation with dependencies:
       IF any_dependency_completes_after_operation_starts:
           RAISE PrecedenceViolation
   ```

5. **Railway Limit:**

   ```
   FOR each day d:
       IF N_batches[d] > 4:
           RAISE RailwayLimitExceeded
   ```

---

## 4. Constraints

### 4.1 Hard Constraints (Cannot Violate)

**1. Tank Capacity**

```
0 ≤ S[k,p,t] ≤ V_max[k] × (1 - deadstock[p])
```

*Violation = Solution is infeasible*

**2. Product Exclusivity**

```
∑(p) X[k,p,t] ≤ 1
```

*A tank cannot hold multiple products simultaneously*

**3. Flow Conservation**

```
S[k,t] = S[k,t-1] + ∑Q_in - ∑Q_out
```

*Matter cannot be created or destroyed*

**4. Resource Exclusivity**

```
For operations i,j on resource r:
end_time[i] ≤ start_time[j] OR end_time[j] ≤ start_time[i]
```

*No two operations on same resource simultaneously*

**5. Precedence**

```
IF operation B depends on A:
start[B] ≥ end[A]
```

*Dependent operations must be ordered correctly*

**6. Railway Batch Limit**

```
N_batches[d] ≤ 4 for all days d
```

*Contractual and physical constraint*

**7. SHT Mutex**

```
NOT (Q_in[SHT, t] > 0 AND Q_out[SHT, t] > 0)
```

*Cannot fill and discharge SHT simultaneously*

### 4.2 Soft Constraints (Penalties if Violated)

**1. Preferred Tank Usage**

```
Penalty = opportunity_cost if RVS-5 used for sunflower when palm vessel expected
```

**2. Client Prioritization**

```
Penalty = C_priority[client] × delay_hours
```

Where strategic clients have higher penalty costs.

**3. Batch Preference**

```
Penalty = C_batch_extra × max(0, N_batches[d] - 4)
```

Prefer 4 batches/day, but allow more at cost.

### 4.3 Conditional Constraints

**1. Cleaning Requirement**

```
IF X[k,p1,t-1] = 1 AND X[k,p2,t] = 1 AND p1 ≠ p2:
    THEN Y_clean[k,τ] = 1 for τ ∈ [t - T_clean, t-1]
    AND Q_in[k,*,τ] = Q_out[k,*,τ] = 0
```

**2. Analysis Blocking**

```
IF tank.state = "analysis":
    THEN Q_out[k,*,t] = 0
    UNTIL analysis_complete AND result = "pass"
```

---

## 5. Assumptions and Limitations

### 5.1 Model Assumptions

**Flow Rates:**

- Ship discharge rates are constant during an operation
- Rail discharge rate averages across batches
- No pump degradation or maintenance downtime modeled

**Timing:**

- All times are deterministic (no stochastic disruptions in operations)
- Analysis always takes exactly 72 hours
- Cleaning times are fixed by product compatibility

**Products:**

- Each product is homogeneous within its type
- No quality degradation during storage
- Temperature management is assumed sufficient (not modeled explicitly)

**Wagons:**

- Wagon availability follows Markov chain (stationary distribution)
- Reject rate is constant at 12%
- Prep time is fixed at 1.5 hours per wagon

**Weather:**

- Season affects rates (summer/winter) but is fixed during planning horizon
- No storms or extreme weather disruptions

### 5.2 Simplifications

**Not Modeled:**

1. **Intra-tank mixing**: Assume perfect mixing within tanks
2. **Pipeline switching time**: Assumes instantaneous (reality: ~15 minutes)
3. **Pump selection**: Uses average rates, not specific pump characteristics
4. **Tank heating/cooling**: Assumes temperature control is automatic
5. **Quality sampling**: Analysis time is fixed, no sampling sequences
6. **Document processing**: Berthing includes all paperwork, simplified to 24h
7. **Crew availability**: Assumes 24/7 operations possible

### 5.3 Known Limitations

**Optimization:**

- Heuristic sequence generation (not guaranteed optimal)
- Stage I and Stage II are decoupled (not global optimum)
- No backtracking or multi-start search

**Scalability:**

- Planning horizon: Practical limit ~60 days
- Vessels per scenario: Recommended ≤10
- Fractions per vessel: Tested up to 8

**Stochastic Elements:**

- Markov chain uses historical data (may not predict future perfectly)
- No scenario trees or robust optimization
- No learning/adaptation from past forecast errors

**Data Quality:**

- Assumes input data is accurate
- No outlier detection or data cleaning
- Manual input errors can propagate

---

## 6. Validation Rules

### 6.1 Input Validation

**Vessel Data:**

```python
def validate_vessel(vessel):
    errors = []
    
    # Total volume
    if vessel.total_volume <= 0:
        errors.append(f"Total volume must be positive")
    
    # Cargo plan (for palm)
    if vessel.cargo_type == "palm":
        if not vessel.cargo_plan:
            errors.append(f"Palm vessel must have cargo plan")
        
        plan_total = sum(vol for _, vol in vessel.cargo_plan.values())
        tolerance = vessel.total_volume * 0.01
        
        if abs(plan_total - vessel.total_volume) > tolerance:
            errors.append(f"Cargo plan ({plan_total}t) doesn't match total ({vessel.total_volume}t)")
    
    return errors
```

**Tank State:**

```python
def validate_tank_state(tank):
    errors = []
    
    # Capacity
    if tank.current_volume > tank.capacity:
        errors.append(f"Volume ({tank.current_volume}) exceeds capacity ({tank.capacity})")
    
    # Product compatibility
    if tank.current_product and not tank.can_store_product(tank.current_product):
        errors.append(f"Product {tank.current_product} not allowed in tank {tank.tank_id}")
    
    # State consistency
    if tank.state == "cleaning" and tank.current_volume > 0:
        errors.append(f"Tank in cleaning state but not empty")
    
    return errors
```

**Rail Schedule:**

```python
def validate_rail_schedule(schedule):
    errors = []
    
    for date, batches in schedule.group_by_date():
        if len(batches) > 4:
            errors.append(f"Date {date}: {len(batches)} batches exceeds maximum of 4")
        
        for batch in batches:
            if batch.wagons % 18 != 0:
                errors.append(f"Batch size {batch.wagons} not multiple of 18")
    
    return errors
```

### 6.2 Solution Validation

**Material Balance:**

```python
def validate_material_balance(operations, tanks_initial, horizon):
    """
    Verify that tank balances are consistent with operations.
    """
    balances = calculate_hourly_balances(operations, tanks_initial, horizon)
    
    violations = []
    for hour, tank_balances in balances.items():
        for tank_id, volume in tank_balances.items():
            tank = tanks[tank_id]
            effective_cap = tank.get_effective_capacity(tank.current_product)
            
            if volume < 0:
                violations.append(f"{hour}: {tank_id} negative volume {volume}")
            
            if volume > effective_cap:
                violations.append(f"{hour}: {tank_id} overfill {volume} > {effective_cap}")
    
    return violations
```

**Precedence:**

```python
def validate_precedence(operations):
    """
    Check that all operation dependencies are satisfied.
    """
    completed = {}
    violations = []
    
    for op in sorted(operations, key=lambda o: o.start_time):
        for dep_id in op.dependencies:
            if dep_id not in completed:
                violations.append(f"{op.op_id} depends on {dep_id} which hasn't completed")
            elif completed[dep_id] > op.start_time:
                violations.append(f"{op.op_id} starts before {dep_id} completes")
        
        completed[op.op_id] = op.end_time
    
    return violations
```

**Resource Conflicts:**

```python
def validate_resource_conflicts(operations):
    """
    Ensure no two operations use the same resource simultaneously.
    """
    conflicts = []
    resources = {}  # resource_id -> list of (start, end, op_id)
    
    for op in operations:
        resource = extract_resource(op)  # e.g., tank_id, line, berth
        
        if resource not in resources:
            resources[resource] = []
        
        for other_start, other_end, other_id in resources[resource]:
            if overlaps((op.start_time, op.end_time), (other_start, other_end)):
                conflicts.append(f"{op.op_id} and {other_id} both use {resource}")
        
        resources[resource].append((op.start_time, op.end_time, op.op_id))
    
    return conflicts
```

---

## Appendix A: Product Transition Matrix

Cleaning hours required when switching products:

|  | Sunflower | Palm Standard | Palm Low3MCPD |
|---|---|---|---|
| **From Sunflower** | 0 | 48 | 72 |
| **From Palm Standard** | 48 | 0-12 | 72 |
| **From Palm Low3MCPD** | 168 | 168 | 0-12 |

**Notes:**

- Within same family (e.g., olein → stearin): 12h light cleaning
- Cross-family (sunflower ↔ palm): 48h standard cleaning
- Involving Low3MCPD: 72-168h deep cleaning

---

## Appendix B: References

**Optimization Techniques:**

- Constraint Programming (CP) for scheduling
- Mixed-Integer Linear Programming (MILP) for cost optimization
- Markov Chain Monte Carlo for stochastic forecasting

**Related Literature:**

- Tank farm scheduling: Liu & Karimi (2007), Maravelias & Grossmann (2004)
- Berth allocation: Imai et al. (2001), Cordeau et al. (2005)
- Wagon routing: Cordeau et al. (1998)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-12-19 | Initial methodology documentation |

---

**End of Methodology Document**
