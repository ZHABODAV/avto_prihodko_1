# Terminal Optimizer - Quick Start Guide

## Your First Calculation in 5 Minutes

This guide will walk you through running your first terminal optimization calculation.

### Prerequisites

✓ You have completed installation (`install.bat` ran successfully)
✓ You have Microsoft Excel 2016 or later
✓ You have vessel schedule data ready

---

## Step 1: Open the Template (30 seconds)

1. Navigate to your installation folder
2. Double-click `terminal_template.xlsx`
3. Excel will open the template

**You should see these sheets:**
- `Input_Vessels` - Where you enter vessel data
- `Input_CurrentState` - Current tank inventory
- `Input_Rail` - Railway delivery schedule
- `Input_Demand` - Client demand (optional)

---

## Step 2: Enter Vessel Data (2-3 minutes)

### Example: Loading Sunflower Oil

Click on `Input_Vessels` sheet and fill ONE row:

| VesselID | ETA | CargoType | TotalVolume | DemurrageRate | Priority |
|----------|-----|-----------|-------------|---------------|----------|
| NS-VICTOR | 2025-01-15 08:00 | sunflower | 25000 | 15000 | HIGH |

**Field explanations:**
- `VesselID`: Any unique name (e.g., "NS-VICTOR")
- `ETA`: Arrival date and time (format: YYYY-MM-DD HH:MM)
- `CargoType`: Either "sunflower" or "palm"
- `TotalVolume`: Total cargo in tonnes
- `DemurrageRate`: Cost per hour of delay (USD/hour)
- `Priority`: HIGH, MEDIUM, or LOW

### Example: Discharging Palm Oil

| VesselID | ETA | CargoType | TotalVolume | DemurrageRate | Priority |
|----------|-----|-----------|-------------|---------------|----------|
| MV-PALMOIL1| 2025-01-16 14:00 | palm | 18000 | 12000 | MEDIUM |

**For palm oil, you also need cargo plan:**

Go to `Input_CargoPlan` sheet (if exists) or add holds in `Input_Vessels`:

| VesselID | Hold | Fraction | Volume |
|----------|------|----------|--------|
| MV-PALMOIL1 | H1 | Stearin | 5000 |
| MV-PALMOIL1 | H2 | Olein | 8000 |
| MV-PALMOIL1 | H3 | LOW3MCPD | 5000 |

---

## Step 3: Check Current Tank State (1 minute)

Click on `Input_CurrentState` sheet.

**Default values:** (Usually start with empty tanks for new scenarios)

| TankID | CurrentVolume | CurrentProduct | State |
|--------|---------------|----------------|-------|
| RVS-1 | 0 | - | idle |
| RVS-2 | 0 | - | idle |
| RVS-3 | 0 | - | idle |
| RVS-5 | 0 | - | idle |
| SHT | 0 | - | idle |

**If tanks have inventory:**

| TankID | CurrentVolume | CurrentProduct | State |
|--------|---------------|----------------|-------|
| RVS-1 | 5000 | sunflower | idle |
| RVS-2 | 3000 | sunflower | idle |

---

## Step 4: Enter Railway Schedule (1 minute - Optional)

Click on `Input_Rail` sheet.

**Example rail deliveries:**

| Date | Product | Volume | Batches |
|------|---------|--------|---------|
| 2025-01-10 | sunflower | 1200 | 1 |
| 2025-01-11 | sunflower | 2400 | 2 |
| 2025-01-12 | sunflower | 3600 | 3 |

**Notes:**
- Each batch = 18 wagons × 65 tonnes = 1170 tonnes
- Maximum 4 batches per day = 4680 tonnes/day
- Leave empty if no rail deliveries

---

## Step 5: Save Your File

1. Click **File → Save As**
2. Save as: `my_scenario.xlsx`
3. Choose a location you'll remember

---

## Step 6: Run the Calculation (30 seconds)

### Method 1: Using run.bat (Recommended)

1. Open Command Prompt in installation folder
   - Hold Shift + Right-click in folder → "Open PowerShell window here"
2. Type: `run.bat my_scenario.xlsx`
3. Press Enter
4. Wait for "Optimization completed successfully!"

### Method 2: Direct Python command

```cmd
venv\Scripts\activate
python -m terminal_optimizer.main my_scenario.xlsx
```

**What happens:**
- Program reads your Excel file
- Generates optimal operation sequence
- Calculates tank balances
- Checks for violations
- Creates output file: `my_scenario_optimized.xlsx`

---

## Step 7: Review Results (2-3 minutes)

The program automatically opens: `my_scenario_optimized.xlsx`

### Key Output Sheets:

#### `Output_Operations` - Operation Timeline
Shows all planned operations in chronological order:
- Berthing, discharge, loading, transfers
- Start/end times
- Durations
- Resource assignments

**Look for:**
- Is vessel processing time reasonable?
- Are operations in logical order?

#### `Output_Balances` - Tank Levels Over Time
Hour-by-hour tank inventory levels.

**Look for:**
- Red cells = Capacity violations (overfill)
- Negative values = Errors
- Smooth transitions = Good plan

#### `Output_Railway` - Wagon Schedule
Railway dispatcher schedule showing:
- Batch timings
- Wagon counts
- Product types

**Look for:**
- Max 4 batches per day
- Realistic timing

#### `Output_Summary` - Key Metrics
High-level statistics:
- Total demurrage cost
- Operation count
- Resource utilization
- Violations (if any)

---

## Common First-Time Issues

### Issue: "No vessels defined in scenario"

**Solution:** You forgot to fill `Input_Vessels` sheet OR you misspelled ship headers.

### Issue: "Capacity violation detected"

**Solution:** Your vessel volume exceeds available tank capacity. Options:
1. Reduce vessel volume
2. Add rail deliveries beforehand (for sunflower)
3. Clear existing tank inventory

### Issue: "File not found"

**Solution:** 
1. Make sure you saved your Excel file
2. Check file path in run.bat command
3. Run command from correct directory

### Issue: Python module errors

**Solution:**
1. Run `install.bat` again
2. Make sure virtual environment is activated
3. Check `requirements.txt` installed correctly

---

## Next Steps

### Learn More
- **User Manual:** `docs/USER_MANUAL.md` - Complete reference
- **Methodology:** `docs/METHODOLOGY.md` - How it works
- **Examples:** `examples/` folder - Sample scenarios

### Try Advanced Features
1. **Multiple vessels:** Add more rows in Input_Vessels
2. **Cargo plans:** Define complex palm fraction mixes
3. **Risk analysis:** Review Output_Risks sheet
4. **Edit sequences:** Manually adjust operations and recalculate

### Customize
1. **Tank configuration:** Edit `templates/tank_config.csv`
2. **Product compatibility:** Edit `templates/product_compatibility_matrix.csv`
3. **Operation standards:** Edit `templates/operation_time_standards.csv`

---

## Tips for Success

✓ **Start Simple:** First calculation should be ONE vessel, preferably sunflower
✓ **Check Input:** Verify all dates are in correct format
✓ **Review Logs:** If errors occur, check `logs/` directory
✓ **Save Often:** Save your Excel file before running
✓ **Compare Results:** Run same scenario twice to verify consistency

---

## Real-World Workflow

### Monthly Planning Process

1. **Monday:** Get vessel schedule from agent
2. **Monday:** Enter vessels in template
3. **Monday:** Run first calculation
4. **Tuesday:** Review with operations team
5. **Tuesday-Friday:** Adjust as needed, rerun
6. **Friday:** Finalize plan, distribute to dispatcher

---

## Getting Help

1. **Error Messages:** Usually self-explanatory, read carefully
2. **Log Files:** Check `logs/terminal_optimizer_*.log`
3. **Documentation:** `docs/USER_MANUAL.md` has troubleshooting section
4. **Support:** Contact technical support with:
   - Your input Excel file
   - Error message
   - Log file

---

**Quick Start Guide v1.1**
Last Updated: January 9, 2026

Ready to optimize
