# Quick Reference Card: Terminal Optimizer

**One-page guide for daily operations**

---

## Pre-Calculation Checklist

Before clicking "Calculate Plan", ensure you have filled:

- [ ] **Input_Vessels** - At least one vessel with valid ETA and volume
- [ ] **Input_CargoPlan** - For palm vessels: all holds with fractions
- [ ] **Input_CurrentState** - Current tank volumes and products
- [ ] **Input_Rail** (optional) - Incoming sunflower deliveries
- [ ] **Input_Demand** (optional) - Client orders

---

## Key Buttons & Actions

| Button | Action | Time |
|--------|--------|------|
| **Calculate Plan** | Generate full operational sequence | 10-60 sec |
| **Recalculate** | Update after manual edits (locked operations) | 5-30 sec |
| **Validate Inputs** | Check data completeness before calculation | 2 sec |
| **Export Report** | Save results to PDF | 5 sec |
| **Reset** | Clear all output sheets | instant |

---

## Tank Quick Reference

| Tank | Capacity (t) | Products | Notes |
|------|-------------|----------|-------|
| **RVS-1** | 9,900 | Sunflower only | Dedicated |
| **RVS-2** | 9,900 | Sunflower only | Dedicated |
| **RVS-3** | 9,900 | Palm only | Dedicated |
| **RVS-5** | 2,700 | Sun OR Palm | **Swing** (needs cleaning) |
| **SHT** | 2,700 | Palm only | Shore tank (buffer) |

**Effective Capacity** = Capacity × (1 - deadstock)
- Sunflower: 90% (10% deadstock)
- Palm: 85-90% (10-15% deadstock)

---

## Flow Rates Reference

| Operation | Line/Route | Rate (t/h) |
|-----------|------------|-----------|
| Palm discharge (large) | Line1 → RVS-3/5 | **900** |
| Palm discharge (small) | Line2 → SHT | **500** |
| Palm direct to rail | Line2 → Rail | **146** |
| Sunflower loading | Tank → Ship | **500-900** |
| Rail discharge (summer) | Rail → Tank | **195** |
| Rail discharge (winter) | Rail → Tank | **146** |

---

## Railway Constraints

- **Max batches/day:** 4
- **Wagons per batch:** 18
- **Wagon capacity:** 65 tonnes
- **Max daily capacity:** 4 × 18 × 65 = **4,680 tonnes**

**Wagon Looping:**
- Sunflower wagons → 1.5h prep → Palm wagons
- Reject rate: ~12% fail inspection

---

## Cleaning Times (Hours)

|  | → Sunflower | → Palm | → Low3MCPD |
|---|------------|--------|------------|
| **From Sunflower** | 0 | 48 | 72 |
| **From Palm** | 48 | 0-12 | 72 |
| **From Low3MCPD** | 168 | 168 | 0-12 |

**Tip:** Avoid using RVS-5 for palm if sunflower operations are frequent (saves 48h cleaning).

---

## Where to Look First in Results

### 1. Output_Warnings (Priority: HIGH)
**Check for:**
- 🔴 CAPACITY_VIOLATION - Overfill risk
- 🔴 WAGON_SHORTAGE - Not enough wagons
- 🟡 SHT_OVERFLOW - Shore tank issues
- 🟡 RAILWAY_DELAY - Train delays forecasted

**Action:** Address all HIGH severity before executing.

### 2. Output_Operations
**Verify:**
- Vessel BERTHING starts at/after ETA
- Discharge order makes sense (large fractions first)
- No unexpected CLEANINGs (check why needed)
- UNBERTHING time is acceptable

### 3. Output_TankBalance
**Look for:**
- 🔴 Red cells - Near capacity (>95%)
- 🟠 Orange cells - High utilization (85-95%)
- Oscillations in SHT (filling/emptying is normal)
- RVS-5 product switches (should have cleaning between)

### 4. Output_RailSchedule
**Confirm:**
- No more than 4 batches per day
- Looping timing looks reasonable (1.5h+ between discharge and loading)
- Batch sizes are multiples of 18 wagons

---

## Common Quick Fixes

### Problem: "Cargo plan total doesn't match vessel total"
✅ **Fix:** Sum volumes in Input_CargoPlan, adjust to match vessel total_volume

### Problem: "Tank capacity exceeded"
✅ **Fix:** Split discharge between two tanks OR reduce operation volume

### Problem: "Railway batch limit exceeded"
✅ **Fix:** Reduce wagons for that day OR shift operations to adjacent days

### Problem: "Product incompatibility"
✅ **Fix:** Add CLEANING operation first OR use different tank

### Problem: "Calculation takes too long (>5 min)"
✅ **Fix:** Reduce horizon_days OR use "Quick Calculate" mode (heuristic)

---

## Palm Fraction Priority (Operational Best Practice)

Discharge in this order for optimal tank usage:

1. **palm_olein_low3mcpd** (highest quality, keep separate)
2. **palm_olein** (large volumes)
3. **palm_oil_low3mcpd** (high quality)
4. **palm_oil** (bulk)
5. **palm_stearin** (moderate)
6. **palm_pfad** (lowest priority)

**Why?** Minimizes cleaning, maximizes compatibility between consecutive operations.

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+C` | Calculate Plan |
| `Ctrl+Shift+R` | Recalculate |
| `Ctrl+Shift+V` | Validate Inputs |
| `Ctrl+Shift+X` | Export Report |
| `F1` | Help |
| `F5` | Refresh Outputs |
| `Esc` | Cancel calculation |

---

## Emergency Contacts

**Technical Support:**
- Email: support@terminaloptimizer.local
- Phone: +7 (XXX) XXX-XX-XX
- Hours: Mon-Fri 9:00-18:00 MSK

**For Critical Issues:**
- Calculation errors halting operations
- Data corruption
- Installation problems

**Response Time:** Within 2 hours during business hours

---

## Version: 1.0 | Updated: 2024-12-19

---

**Print this page and keep at your workstation!**
