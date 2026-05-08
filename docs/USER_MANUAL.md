# User Manual: Terminal Optimizer

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Input Data](#input-data)
4. [Understanding Results](#understanding-results)
5. [Editing Sequences](#editing-sequences)
6. [Troubleshooting](#troubleshooting)

---

## Installation

### System Requirements

**Operating System:**

- Windows 10 or later
- Windows Server 2016 or later

**Software:**

- Microsoft Excel 2016 or later (with VBA support)
- Python 3.9 or higher

**Hardware:**

- Minimum: 4 GB RAM, 2 GHz processor
- Recommended: 8 GB RAM, 2.5 GHz processor
- Disk Space: 500 MB free space

### Step-by-Step Installation

#### 1. Install Python

1. Download Python 3.9+ from [python.org](https://python.org) official website
2. Run the installer with these options:
   - ✅ **Check "Add Python to PATH"** (critical!)
   - ✅ Install for all users
   - Choose "Customize installation"
   - Select all optional features
3. Verify installation:

   ```cmd
   python --version
   ```

   You should see: `Python 3.9.x` or higher

#### 2. Install Terminal Optimizer

**Option A: Quick Installation (Windows)**

1. Extract the downloaded archive to a folder (e.g., `C:\TerminalOptimizer`)
2. Double-click [`install.bat`](../install.bat)
3. Wait for the installation to complete
4. You should see: "✓ Installation completed successfully"

**Option B: Manual Installation**

1. Open Command Prompt (cmd)
2. Navigate to the Terminal Optimizer folder:

   ```cmd
   cd C:\TerminalOptimizer
   ```

3. Create a virtual environment:

   ```cmd
   python -m venv venv
   ```

4. Activate the virtual environment:

   ```cmd
   venv\Scripts\activate
   ```

5. Install dependencies:

   ```cmd
   pip install -r requirements.txt
   ```

#### 3. Verify Installation

Run the verification script:

```cmd
python -m terminal_optimizer --version
```

You should see:

```
Terminal Optimizer v1.0
All dependencies installed correctly
```

---

## Quick Start

### Opening the Template

1. Navigate to the [`templates/`](../templates/) folder
2. Open [`terminal_template.xlsx`](../templates/terminal_template.xlsx) in Excel
3. Enable macros if prompted (required for the Calculate button)

### Basic Workflow

![Quick Start Workflow](quickstart_diagram.png)

#### Step 1: Fill Vessel Information

Navigate to the **Input_Vessels** sheet:

| Column | Description | Example |
|--------|-------------|---------|
| `vessel_id` | Unique ship name/ID | "Victoria" |
| `eta` | Expected arrival date/time | 2024-10-15 08:00 |
| `cargo_type` | "palm" or "sunflower" | "palm" |
| `total_volume` | Total cargo in tonnes | 28000 |
| `demurrage_rate` | Cost per hour delay (RUB) | 100000 |
| `strategic_weight` | Priority multiplier (1.0-2.0) | 1.5 |

**For Palm Vessels**, also fill the **Input_CargoPlan** sheet:

| Column | Description | Example |
|--------|-------------|---------|
| `vessel_id` | Must match Input_Vessels | "Victoria" |
| `hold_id` | Ship's cargo hold number | "H1" |
| `fraction` | Palm product type | "palm_olein" |
| `volume` | Volume in tonnes | 3500 |

**Available Palm Fractions:**

- `palm_oil` - Palm Oil (RBD)
- `palm_olein` - Palm Olein (RBD)
- `palm_stearin` - Palm Stearin
- `palm_pfad` - Palm Fatty Acid Distillate
- `palm_oil_low3mcpd` - Low 3-MCPD Palm Oil
- `palm_olein_low3mcpd` - Low 3-MCPD Palm Olein

#### Step 2: Set Current Tank State

Navigate to **Input_CurrentState** sheet:

| Tank | Current Volume (t) | Current Product | State |
|------|-------------------|-----------------|-------|
| RVS_1 | 8500 | sunflower | idle |
| RVS_2 | 7200 | sunflower | idle |
| RVS_3 | 0 | (empty) | idle |
| RVS_5 | 0 | (empty) | idle |
| SHT | 0 | (empty) | idle |

**States:**

- `idle` - Available for operations
- `analysis` - Quality testing (72h before use)
- `cleaning` - Cleaning between products

#### Step 3: Input Rail Schedule (Optional)

Navigate to **Input_Rail** sheet for incoming sunflower deliveries:

| Date | Wagons | Product | Source |
|------|--------|---------|--------|
| 2024-10-15|18|sunflower|own_production|
| 2024-10-16|36|sunflower|own_production|

**Constraints:**

- Maximum 4 batches per day
- Each batch = 18 wagons
- Each wagon = 65 tonnes

#### Step 4: Calculate

1. **Configure Settings:** Go to the **Settings** sheet and select your Run Mode (default: All) and Optimization preference.
2. Click the **"Calculate Plan"** button on the main sheet (Instructions).
3. Wait for the progress indicator (typically 10-60 seconds).
4. Review the generated output sheets.

**Alternative (Command Line):**

```cmd
cd C:\TerminalOptimizer
venv\Scripts\activate
python -m terminal_optimizer.main templates\terminal_template.xlsx results.xlsx --mode all --optimize
```

#### Step 5: Review Results

The calculator generates these output sheets:

- **Output_Operations** - Detailed operation sequence
- **Output_TankBalance** - Hourly tank inventory
- **Output_RailSchedule** - Railway wagon timing
- **Output_Warnings** - Risk alerts and recommendations

---

## Input Data

### 3.1 Vessels Sheet (Input_Vessels)

**Mandatory Fields:**

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `vessel_id` | Text | Unique vessel identifier | No duplicates |
| `eta` | DateTime | Expected arrival | Format: YYYY-MM-DD HH:MM |
| `cargo_type` | Text | "palm" or "sunflower" | Exact match |
| `total_volume` | Number | Total cargo (tonnes) | > 0 |

**Optional Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `demurrage_rate` | Number | 100000 | Cost per hour (RUB) |
| `strategic_weight` | Number | 1.0 | Priority (1.0 = normal, 2.0 = high) |
| `Active` | Text | "Yes" | Set to "No" to exclude vessel from simulation |
| `notes` | Text | "" | Any additional comments |

**Example:**

```
vessel_id: "Victoria"
eta: 2024-10-15 08:00
cargo_type: palm
total_volume: 28000
demurrage_rate: 120000
strategic_weight: 1.5
Active: Yes
notes: "High priority client"
```

### 3.2 Cargo Plan Sheet (Input_CargoPlan)

**For Palm Vessels Only** - lists each ship hold with its product and volume.

**Fields:**

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `vessel_id` | Text | Must match Input_Vessels | "Victoria" |
| `hold_id` | Text | Ship's hold identifier | "H1", "H2", ... |
| `fraction` | Text | Palm product type | "palm_olein" |
| `volume` | Number | Volume in tonnes | 3500 |

**Important:**

- Sum of all hold volumes must equal `total_volume` from Input_Vessels (±1% tolerance)
- Each hold can contain only one fraction
- A vessel can have up to 8 different holds

**Example for a 28,000 tonne palm vessel:**

```
vessel_id | hold_id | fraction              | volume
----------|---------|----------------------|-------
Victoria  | H1      | palm_oil             | 12000
Victoria  | H2      | palm_oil             | 8000
Victoria  | H3      | palm_olein           | 3500
Victoria  | H4      | palm_olein           | 2000
Victoria  | H5      | palm_stearin         | 1500
Victoria  | H6      | palm_pfad            | 1000
```

### 3.3 Current State Sheet (Input_CurrentState)

Describes the current tank inventory at planning start.

**Fields:**

| Field | Tank ID | Description |
|-------|---------|-------------|
| `tank_id` | Text | RVS_1, RVS_2, RVS_3, RVS_5, or SHT |
| `current_volume` | Number | Current inventory (tonnes) |
| `current_product` | Text | Product currently in tank (or empty) |
| `state` | Text | idle / analysis / cleaning / filling |
| `state_entry_time` | DateTime | When state started (for analysis/cleaning) |

**Tank Specifications:**

| Tank | Capacity (t) | Allowed Products |
|------|--------------|------------------|
| RVS_1 | 9,900 | sunflower only |
| RVS_2 | 9,900 | sunflower only |
| RVS_3 | 9,900 | palm fractions only |
| RVS_5 | 2,700 | sunflower OR palm (swing tank) |
| SHT | 2,700 | palm fractions only |

**Deadstock** (unusable bottom layer):

- Sunflower: 10% of capacity
- Palm (standard): 10% of capacity
- Palm (low3mcpd): 15% of capacity

### 3.4 Rail Schedule Sheet (Input_Rail)

Incoming sunflower deliveries by rail.

**Fields:**

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `date` | Date | Arrival date | 2024-10-15 |
| `wagons` | Number | Number of wagons | 18, 36, 54, 72 |
| `product` | Text | Usually "sunflower" | sunflower |
| `source` | Text | Origin | own_production / trading |

**Important Rules:**

- Maximum 4 batches per day (72 wagons)
- Batch size: 18 wagons each
- Discharge rate: 195 t/h (summer) or 146 t/h (winter)
- Wagon capacity: 65 tonnes each

### 3.5 Demand Sheet (Input_Demand)

Client demand for outgoing shipments (future feature).

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `week` | Number | ISO week number |
| `client` | Text | Client name |
| `product` | Text | Product type |
| `volume` | Number | Requested tonnes |
| `priority` | Text | HIGH / MEDIUM / LOW |

### 3.6 Settings Sheet (Settings)

Configuration for the calculation run.

**Fields:**

| Parameter | Value | Description |
|-----------|-------|-------------|
| `Run Mode` | All / Palm Only / Sunflower Only | Filter which vessels to process |
| `Optimize Sequence` | Yes / No | Automatically reorder vessels to minimize costs |
| `Vessel Filter` | (Vessel ID) | Run simulation for a single vessel only |

---

## Understanding Results

### 4.1 Operations Sequence (Output_Operations)

This sheet shows every operation in chronological order.

**Columns:**

| Column | Description |
|--------|-------------|
| `op_id` | Unique operation identifier (e.g., "BERTH_Victoria_001") |
| `vessel_id` | Associated vessel (if any) |
| `op_type` | Type: berthing, discharge, load, transfer, cleaning, analysis |
| `start_time` | When operation starts (datetime) |
| `duration` | How long it takes (hours) |
| `end_time` | When operation ends (datetime) |
| `source` | Where product comes from (Ship/Rail/Tank) |
| `target` | Where product goes to (Tank/Ship/Rail) |
| `product` | Product type being moved |
| `volume` | Volume in tonnes |
| `line` | Pipeline used (Line1/Line2 for palm) |
| `wagons` | Number of railway wagons (if rail operation) |
| `notes` | Additional information |

**Operation Types Explained:**

1. **BERTHING** - Vessel arrives and documents are processed (24h minimum)
2. **DISCHARGE** - Unloading product from ship to shore tanks
   - Palm: via Line1 (→ RVS-3/5) or Line2 (→ SHT or direct to rail)
   - Rate: 900 t/h (Line1), 500 t/h (Line2 to tank), 146 t/h (Line2 to rail)
3. **LOAD** - Loading product from shore tanks to ship
   - For sunflower export
   - Rate: 500-900 t/h depending on product
4. **TRANSFER** - Moving product between shore tanks
5. **CLEANING** - Cleaning tank between incompatible products
   - Sunflower ↔ Palm: 48 hours
   - Low3MCPD products: 72-168 hours
6. **ANALYSIS** - Quality testing period (72 hours standard)
7. **RAIL_BATCH** - Railway wagon loading/unloading
   - Batch size: 18 wagons (1,170 tonnes)

**Example Reading:**

```
op_id: DISCHARGE_Victoria_H1_001
vessel_id: Victoria
op_type: discharge
start_time: 2024-10-16 08:00
duration: 22.22
end_time: 2024-10-17 06:13
source: Ship_Victoria_H1
target: RVS_3
product: palm_oil
volume: 20000
line: Line1
notes: Main line to large tank
```

**Interpretation:** Starting Oct 16 at 8:00, we discharge 20,000 tonnes of Palm Oil from Victoria's Hold H1 to RVS-3 tank via Line1. This takes 22.22 hours (20,000t ÷ 900 t/h), finishing Oct 17 at 06:13.

### 4.2 Tank Balance Chart (Output_TankBalance)

Hour-by-hour inventory for each tank.

**Columns:**

- `hour` - Time stamp (datetime)
- `RVS_1` - Inventory in RVS-1 (tonnes)
- `RVS_2` - Inventory in RVS-2 (tonnes)
- `RVS_3` - Inventory in RVS-3 (tonnes)
- `RVS_5` - Inventory in RVS-5 (tonnes)
- `SHT` - Inventory in SHT (tonnes)
- `total` - Total across all tanks

**Color Coding (in Excel template):**

- 🟢 Green: 0-50% capacity (safe)
- 🟡 Yellow: 50-85% capacity (moderate)
- 🟠 Orange: 85-95% capacity (near full)
- 🔴 Red: 95-100% capacity (critical)

**How to Read:**

Look for:

- **Overfill warnings** - Any tank exceeding effective capacity
- **Capacity issues** - Tanks staying near maximum for extended periods
- **Swing tank usage** - RVS-5 switching between sunflower and palm (check for cleaning periods)
- **SHT oscillation** - Shore tank filling and emptying (should not stay full too long)

**Example:**

```
hour              | RVS_1 | RVS_2 | RVS_3 | RVS_5 | SHT  | total
------------------|-------|-------|-------|-------|------|-------
2024-10-16 08:00  | 8500  | 7200  |    0  |    0  |   0  | 15700
2024-10-16 09:00  | 8500  | 7200  |  900  |    0  |   0  | 16600
2024-10-16 10:00  | 8500  | 7200  | 1800  |    0  |   0  | 17500
```

### 4.3 Railway Schedule (Output_RailSchedule)

Detailed wagon movement timeline.

**Columns:**

| Column | Description |
|--------|-------------|
| `date` | Calendar date |
| `shift` | Day / Evening / Night |
| `time` | Exact time |
| `operation` | What to do (подать/убрать/отправить) |
| `wagons` | Number of wagons |
| `product` | Product type |
| `destination` | Where wagons go |
| `notes` | Status or warnings |

**Shifts:**

- **Day shift**: 08:00 - 16:00
- **Evening shift**: 16:00 - 00:00
- **Night shift**: 00:00 - 08:00

**Example:**

```
date       | shift   | time  | operation      | wagons | product   | destination | notes
-----------|---------|-------|----------------|--------|-----------|-------------|-------
2024-10-15 | Day     | 08:00 | Подать под слив| 18     | sunflower | RVS_1       | Batch 1
2024-10-15 | Day     | 14:00 | Убрать пустые  | 18     | -         | Prep area   | 1.5h
2024-10-15 | Evening | 18:00 | Подать под налив|18     | palm_olein| Client A    | Batch 2
2024-10-15 | Night   | 02:00 | Отправить      | 18     | palm_olein| Client A    | Loaded
```

**Key Points:**

- Maximum 4 batches shown per day
- Wagon "looping": sunflower wagons can be cleaned and reused for palm loading
- Prep time: 1-6 hours between discharge and loading
- Reject rate: ~12% of wagons may not pass inspection

### 4.4 Risk Warnings & Recommendations (Output_Warnings)

Automatically generated alerts for potential issues.

**Columns:**

| Column | Description |
|--------|-------------|
| `date` | When risk occurs |
| `risk_type` | Category of risk |
| `severity` | HIGH / MEDIUM / LOW |
| `probability` | Likelihood (%) |
| `impact` | Cost or delay (RUB or hours) |
| `description` | What the risk is |
| `recommendation` | Suggested action |

**Risk Types:**

1. **WAGON_SHORTAGE** - Not enough wagons available

   ```
   date: 2024-10-18
   risk_type: WAGON_SHORTAGE
   severity: HIGH
   probability: 65%
   impact: 2,400,000 RUB
   description: "Need 120 wagons but only 70 expected available"
   recommendation: "Order 50 external wagons by Day 16"
   ```

2. **SHT_OVERFLOW** - Shore tank filling too quickly

   ```
   risk_type: SHT_OVERFLOW
   severity: MEDIUM
   probability: 40%
   impact: Operational disruption
   description: "SHT may reach capacity during H3 discharge"
   recommendation: "Shift H3 discharge start +4 hours"
   ```

3. **RAILWAY_DELAY** - Train arrival delays forecasted

   ```
   risk_type: RAILWAY_DELAY
   severity: MEDIUM
   probability: 25%
   impact: 1,200,000 RUB
   description: "High probability of 2-day rail delay based on season"
   recommendation: "Increase RVS safety stock by 2000t"
   ```

4. **CLEANING_CONFLICT** - Tank cleaning blocking operations

   ```
   risk_type: CLEANING_CONFLICT
   severity: LOW
   probability: 30%
   impact: 12 hours delay
   description: "RVS-5 cleaning overlaps with planned palm discharge"
   recommendation: "Use only RVS-3 for palm, avoid RVS-5 cleaning"
   ```

5. **CAPACITY_VIOLATION** - Tank overfill risk

   ```
   risk_type: CAPACITY_VIOLATION
   severity: HIGH
   probability: 90%
   impact: CANNOT EXECUTE
   description: "Operation would exceed RVS-3 capacity by 500t"
   recommendation: "Split discharge between RVS-3 and RVS-5"
   ```

**How to Use:**

1. Sort by severity (HIGH first)
2. Address all HIGH severity issues before executing plan
3. Monitor MEDIUM severity during execution
4. LOW severity = informational

---

## Editing Sequences

### 5.1 Viewing the Generated Sequence

After calculation, the **Output_Operations** sheet contains all operations in order.

**Understanding Dependencies:**

- Some operations depend on others completing first
- Example: Cannot discharge to RVS-3 while it's being cleaned
- Example: Cannot move wagons until previous batch clears

### 5.2 Manual Sequence Adjustments

**To change operation order:**

1. In the **Output_Operations** sheet, find the operation to modify
2. Change its `start_time` to the new desired time
3. Mark `user_locked` column as TRUE
4. Click **"Recalculate"** button

The system will:

- Keep your locked operation at the specified time
- Adjust dependent operations automatically
- Validate that the new sequence is feasible
- Show errors if conflicts exist

**Example:**

```
Original:
op_id: DISCHARGE_H3
start_time: 2024-10-16 18:00
user_locked: FALSE

Modified:
op_id: DISCHARGE_H3
start_time: 2024-10-17 06:00  ← Changed
user_locked: TRUE              ← Locked
```

### 5.3 Swapping Operations

To swap two operations (e.g., discharge H2 before H1):

1. Find both operations in Output_Operations
2. Note their current `start_time` values
3. Swap the two start times
4. Set `user_locked = TRUE` for both
5. Click **"Recalculate"**

The system validates:

- ✅ No resource conflicts (tank/pipeline availability)
- ✅ No capacity violations
- ✅ Dependencies still satisfied

If validation fails, you'll see an error message explaining why.

### 5.4 Blocking an Operation

To prevent an operation (e.g., don't use RVS-5):

1. In Input_CurrentState, set RVS_5 state to "blocked"
2. Click **"Calculate Plan"** again
3. System will generate sequence avoiding RVS-5

### 5.5 Recalculation Logic

When you recalculate after manual edits:

**Locked operations:**

- Times are fixed, won't change
- Used as constraints for other operations

**Unlocked operations:**

- Re-optimized around locked ones
- May get new start times
- Respect all constraints

**Partial recomputation:**

- Only operations "downstream" from your edit are recalculated
- Faster than full recalculation

---

## Troubleshooting

### 6.1 Common Errors

#### Error: "Cargo plan total doesn't match vessel total"

**Problem:** Sum of cargo_plan volumes ≠ vessel total_volume

**Solution:**

1. Go to Input_CargoPlan sheet
2. Sum the `volume` column for your vessel
3. Compare to `total_volume` in Input_Vessels
4. Adjust volumes so they match (±1% tolerance allowed)

**Example:**

```
vessel_id: Victoria
total_volume: 28000

Cargo plan:
H1: 12000
H2: 8000
H3: 3500
H4: 2000
H5: 1500
H6: 1000
Total: 28000 ✓ Matches
```

#### Error: "Tank capacity exceeded"

**Problem:** Operation would overfill a tank

**Solution:**

1. Check Output_TankBalance for the problematic time
2. Options:
   - Split the discharge between two tanks
   - Reduce the operation volume
   - Ensure previous operations have cleared space

**Example:**

```
RVS-3 capacity: 9900t
Effective (90%): 8910t
Current: 6000t
Available: 2910t

Trying to add: 3500t  ← TOO MUCH
Solution: Put 2910t in RVS-3, 590t in RVS-5
```

#### Error: "Railway batch limit exceeded"

**Problem:** More than 4 rail batches scheduled in one day

**Solution:**

1. Check Output_RailSchedule for the problem day
2. Reduce wagon count for that day, or
3. Shift some operations to adjacent days

**Constraint:** Maximum 4 batches/day × 18 wagons = 72 wagons/day

#### Error: "Product incompatibility"

**Problem:** Trying to put palm in а tank that has sunflower (without cleaning)

**Solution:**

1. Add a CLEANING operation first (48-72 hours)
2. Or use a different tank
3. Check Input_CurrentState for tank contents

**Cleaning Matrix:**

- Sunflower → Palm: 48 hours
- Palm → Sunflower: 48 hours
- Standard → Low3MCPD: 72 hours
- Low3MCPD → Standard: 168 hours

#### Error: "Module not found" (Python)

**Problem:** Dependencies not installed correctly

**Solution:**

```cmd
cd C:\TerminalOptimizer
venv\Scripts\activate
pip install --upgrade -r requirements.txt
```

#### Error: "No module named 'terminal_optimizer'"

**Problem:** Running from wrong directory or venv not activated

**Solution:**

```cmd
cd C:\TerminalOptimizer
venv\Scripts\activate
```

### 6.2 Time Buffers

The system now automatically adds a buffer time between operations to absorb minor delays.
- **Default Buffer:** 2.0 hours (for ship operations)
- **Rail Buffer:** 0.5 hours (between rail batches, to maintain daily capacity)
- **Configuration:** Can be adjusted in `config.yaml` under `time.buffer` and `time.rail_buffer`.

### 6.3 Wagon Optimization

Small wagon demands are automatically grouped into full batches to optimize costs and rail logistics.
- **Logic:** Demands for the same day are combined into batches of 18 wagons.
- **Reporting:** The `Output_Wagons_Summary` sheet details the composition of each batch (e.g., "Batch 1: 10 Sunflower, 5 Palm").
- **Note:** This is a **post-processing analysis**. The main operations schedule (`Output_Operations`) reflects the raw input demands to ensure traceability, while the Wagon Report shows the optimized logistical view.

### 6.4 Monte Carlo Simulation

To assess the robustness of your plan against real-world variability (e.g., vessel delays, flow rate fluctuations), you can run a Monte Carlo simulation.

**Usage:**
Run from the command line with the `--simulate` flag:

```cmd
python -m terminal_optimizer.main input.xlsx output.xlsx --simulate
```

**Output:**
The simulation runs 50 iterations with random variations:
- Vessel ETA: +/- 12 hours
- Flow Rates: +/- 10%

It reports a **Confidence Score** (0.0 - 1.0) and **Success Rate** (%). A low score indicates the plan is fragile and likely to fail in practice.

### 6.5 Advanced Features

#### Sequence Optimization
When `Optimize Sequence` is set to **Yes**, the system will:
1. Analyze all possible vessel arrival sequences (for small numbers) or use heuristics (for large numbers).
2. Calculate the total cost for each sequence, including:
   - **Demurrage:** Cost of vessels waiting at anchor.
   - **Cleaning Downtime:** Time lost cleaning lines/tanks between incompatible products.
3. Select the sequence with the lowest total cost.
4. Reorder the operations accordingly.

**Note:** This may change the processing order from the original ETA order if it saves significant money/time.

#### Operational Patterns (Run Modes)
You can filter the simulation to focus on specific operations:
- **All:** Process everything (default).
- **Palm Only:** Ignore sunflower vessels and rail. Focus on Palm discharge and line cleaning.
- **Sunflower Only:** Ignore palm vessels. Focus on Sunflower loading and rail accumulation.

#### Strict Segregation & Line Cleaning
The system now enforces strict segregation for pipelines (`Line1`, `Line2`):
- If a pipeline switches between incompatible products (e.g., Stearin → Low3MCPD), a **CLEANING** operation is automatically inserted.
- This ensures product quality but adds downtime.
- The optimizer tries to group compatible products to minimize this cleaning.

### 6.6 Performance Issues

#### Calculator is slow (>5 minutes)

**Causes:**

- Very long planning horizon (>60 days)
- Many vessels (>5 vessels)
- Complex cargo plans (>6 fractions per vessel)

**Solutions:**

1. Reduce horizon_days in parameters
2. Split scenario into smaller time windows
3. Use "Quick Calculate" mode (heuristic, not optimal)

#### Excel freezes when clicking Calculate

**Causes:**

- VBA macro security blocking execution
- Python not in PATH

**Solutions:**

1. Enable macros: File → Options → Trust Center → Macro Settings → Enable all
2. Check Python installation:

   ```cmd
   python --version
   ```

3. Use command-line mode instead of Excel button

### 6.3 Unexpected Results

#### Operations seem inefficient

**Check:**

1. Are there user-locked operations forcing suboptimal paths?
   - Clear `user_locked` column and recalculate
2. Is the system using conservative assumptions?
   - Review Input_Parameters (flow rates, downtime estimates)
3. Are there capacity constraints you're not aware of?
   - Review Output_Warnings for underlying issues

#### Wagons are not looping (sunflower → palm)

**Causes:**

- Insufficient prep time between operations
- Different clients or timing windows
- Wagon availability forecast too conservative

**Solution:**

- Check Input_Parameters: `wagon_prep_time` (increase if needed)
- Check `wagon_reject_rate` (higher = less reuse)
- Review Output_RailSchedule timing

#### SHT constantly full

**Problem:** Shore tank not discharging fast enough to rail

**Solution:**

1. Increase rail batch frequency (if under 4/day)
2. Use "direct to rail" discharge (Line2 → Rail, skipping SHT)
3. Reduce Line2 discharge rate to match rail capacity:
   - Line2 at 500 t/h might overwhelm rail at 146 t/h
   - Consider throttling Line2 or increasing rail batches

### 6.4 Contact Support

If you cannot resolve an issue:

**Gather this information:**

1. Screenshot of the error message
2. Input file (templates/terminal_template.xlsx with your data)
3. Steps you took before the error occurred
4. Output of:

   ```cmd
   python --version
   pip list
   ```

## Appendix A: Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+C` | Calculate plan |
| `Ctrl+Shift+R` | Recalculate with edits |
| `Ctrl+Shift+V` | Validate inputs |
| `Ctrl+Shift+X` | Export to PDF report |
| `F1` | Help |
| `F5` | Refresh outputs |

---

## Appendix B: Flow Rate Reference

| Operation | Line | Rate (t/h) | Notes |
|-----------|------|-----------|-------|
| Ship discharge (palm) | Line1 | 900 | To RVS-3, RVS-5 |
| Ship discharge (palm) | Line2 | 500 | To SHT |
| Ship discharge (direct) | Line2 | 146 | Direct to rail |
| Ship loading (sunflower) | Main | 500-900 | Variable by product |
| Rail discharge (summer) | - | 195 | 4 batches/day |
| Rail discharge (winter) | - | 146 | 3 batches/day |
| Tank transfer | - | 500 | Between shore tanks |

---

## Appendix C: Tank Compatibility Matrix

| From → To | Sunflower | Palm Standard | Palm Low3MCPD |
|-----------|-----------|---------------|---------------|
| **Sunflower** | 0h | 48h | 72h |
| **Palm Standard** | 48h | 0-12h | 72h |
| **Palm Low3MCPD** | 168h | 168h | 0-12h |

**Notes:**

- 0h = No cleaning needed (same product family)
- 12h = Light cleaning (within palm family)
- 48h = Standard cleaning (product type change)
- 72h = Deep cleaning (low3MCPD contamination risk)
- 168h = Full week cleaning (from low3MCPD)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | 2026-01-09 | Added Monte Carlo simulation, Sequence Editor, and updated documentation |
| 1.0 | 2024-12-19 | Initial release |

---

**End of User Manual**
