"""
Critical Point Calculator for Terminal Optimizer

This module provides functions for calculating optimal vessel loading timing,
capacity checks, and accumulation/loading plan generation.

Functions:
    - calculate_critical_start_point: Calculate minimum stock needed before ship loading
    - check_sunflower_capacity: Verify if terminal can accumulate required stock
    - generate_accumulation_operations: Create rail-to-tank filling operations
    - generate_loading_plan: Create ship loading operations with direct variant
"""

from __future__ import annotations
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from terminal_optimizer.domain_models import (
    Tank, Vessel, Operation, OperationType, CargoType
)
from terminal_optimizer.constants import (
    RATE_RAIL_DISCHARGE_SUMMER,
    RATE_SHIP_LOAD_MIN,
    RATE_SHIP_LOAD_MAX,
    DEFAULT_SAFETY_MARGIN,
    WAGONS_PER_BATCH,
    WAGON_CAPACITY,
    MAX_BATCHES_PER_DAY_SUMMER,
    DEFAULT_BATCHES_PER_DAY,
    BATCH_DURATION_HOURS,
    MIN_TANK_VOLUME_THRESHOLD,
    DEFAULT_SHIP_LOAD_RATE,
    DEFAULT_PUMP_RATE,
    DEFAULT_RAIL_RATE,
)
from terminal_optimizer.config import config


@dataclass
class CriticalPointResult:
    """Result of critical point calculation."""
    vessel_id: str
    vessel_volume: float
    critical_start: float  # Minimum stock at loading start
    rail_contribution: float  # Volume from rail during loading
    loading_duration: float  # Hours
    feasible: bool
    notes: str


@dataclass
class CapacityCheckResult:
    """Result of capacity check."""
    feasible: bool
    required_stock: float
    available_capacity: float
    gap: float
    uses_rvs_5: bool
    tank_allocation: Dict[str, float]
    notes: str


@dataclass
class AccumulationPlan:
    """Plan for accumulating stock before ship loading."""
    operations: List[Operation]
    accumulation_days: float
    daily_rate: float
    deficit: float
    start_date: datetime
    end_date: datetime


# =============================================================================
# SECTION 5.1: Critical Point Calculator
# =============================================================================

def calculate_critical_start_point(
    vessel_volume: float,
    rail_rate: float = None,  # type: ignore
    ship_rate: float = None,  # type: ignore
    safety_margin: float = None,  # type: ignore
) -> CriticalPointResult:
    """
    Calculate critical starting stock level for vessel loading.
    
    The critical point is the minimum stock level required in tanks at the START
    of ship loading, accounting for simultaneous rail discharge during loading.
    
    Formula:
        T_loading = vessel_volume / ship_rate
        Rail_contribution = rail_rate × T_loading
        S_start = vessel_volume - Rail_contribution
        S_start_safe = S_start × (1 + safety_margin)
    
    Args:
        vessel_volume: Total vessel capacity in tonnes
        rail_rate: Rail discharge rate in tonnes/hour
        ship_rate: Ship loading rate in tonnes/hour
        safety_margin: Safety factor (0.10 = 10% buffer)
        
    Returns:
        CriticalPointResult with calculated values
        
    Example:
        >>> result = calculate_critical_start_point(35000, 195, 700, 0.10)
        >>> print(f"Need {result.critical_start:.0f}t at loading start")
        Need 24475t at loading start
    """
    # Use config defaults if not provided
    if rail_rate is None:
        rail_rate = config.get('rates.rail_discharge.summer', 195.0)
    if ship_rate is None:
        ship_rate = (config.get('rates.ship_load.min', 500.0) + config.get('rates.ship_load.max', 900.0)) / 2
    if safety_margin is None:
        safety_margin = config.get('safety.margin', 0.10)

    if vessel_volume <= 0:
        raise ValueError(f"Vessel volume must be positive, got {vessel_volume}")
    if rail_rate < 0:
        raise ValueError(f"Rail rate cannot be negative, got {rail_rate}")
    if ship_rate <= 0:
        raise ValueError(f"Ship rate must be positive, got {ship_rate}")
    if safety_margin < 0:
        raise ValueError(f"Safety margin cannot be negative, got {safety_margin}")
    
    # Calculate loading duration
    loading_duration = vessel_volume / ship_rate
    
    # Calculate rail contribution during loading
    rail_contribution = rail_rate * loading_duration
    
    # Calculate minimum starting stock (before safety margin)
    s_start = vessel_volume - rail_contribution
    
    # Apply safety margin
    s_start_safe = s_start * (1 + safety_margin)
    
    # Determine feasibility (critical start should be positive)
    feasible = s_start > 0
    
    notes = []
    if not feasible:
        notes.append("Rail rate exceeds ship rate - loading cannot proceed")
    elif s_start_safe > 40000:
        notes.append("WARNING: Required stock exceeds typical terminal capacity")
    
    return CriticalPointResult(
        vessel_id="",
        vessel_volume=vessel_volume,
        critical_start=s_start_safe,
        rail_contribution=rail_contribution,
        loading_duration=loading_duration,
        feasible=feasible,
        notes="; ".join(notes) if notes else "OK"
    )


# =============================================================================
# SECTION 5.2: Capacity Check
# =============================================================================

def check_sunflower_capacity(
    s_start_needed: float,
    current_inventory: Dict[str, float],
    tanks: Dict[str, Tank],
    allow_rvs_5: bool = True
) -> CapacityCheckResult:
    """
    Check if terminal has capacity to accumulate required sunflower stock.
    
    Checks available capacity in:
    - RVS_1 (dedicated sunflower, 9900t capacity, 10% deadstock)
    - RVS_2 (dedicated sunflower, 9900t capacity, 10% deadstock)
    - RVS_5 (swing tank, 2700t capacity, 10% deadstock) - optional
    
    Args:
        s_start_needed: Required stock level in tonnes
        current_inventory: Current stock in each tank
        tanks: Tank configuration dictionary
        allow_rvs_5: Whether RVS_5 can be used (if not occupied by palm)
        
    Returns:
        CapacityCheckResult with feasibility and allocation
        
    Example:
        >>> result = check_sunflower_capacity(25000, {"RVS_1": 5000, "RVS_2": 3000}, tanks)
        >>> print(f"Feasible: {result.feasible}, Uses RVS_5: {result.uses_rvs_5}")
        Feasible: True, Uses RVS_5: True
    """
    # Get sunflower tanks
    rvs_1 = tanks.get("RVS_1")
    rvs_2 = tanks.get("RVS_2")
    rvs_5 = tanks.get("RVS_5")
    
    if not rvs_1 or not rvs_2:
        return CapacityCheckResult(
            feasible=False,
            required_stock=s_start_needed,
            available_capacity=0.0,
            gap=s_start_needed,
            uses_rvs_5=False,
            tank_allocation={},
            notes="ERROR: RVS_1 or RVS_2 not found in tank configuration"
        )
    
    # Calculate effective capacities (accounting for deadstock)
    rvs_1_capacity = rvs_1.get_effective_capacity("sunflower")
    rvs_2_capacity = rvs_2.get_effective_capacity("sunflower")
    
    # Get current inventory
    rvs_1_current = current_inventory.get("RVS_1", 0.0)
    rvs_2_current = current_inventory.get("RVS_2", 0.0)
    rvs_5_current = current_inventory.get("RVS_5", 0.0)
    
    # Calculate available space
    rvs_1_available = max(0, rvs_1_capacity - rvs_1_current)
    rvs_2_available = max(0, rvs_2_capacity - rvs_2_current)
    
    # Total available without RVS_5
    available_without_rvs5 = rvs_1_available + rvs_2_available + rvs_1_current + rvs_2_current
    
    uses_rvs_5 = False
    tank_allocation = {}
    
    # Check if we can fit without RVS_5
    if s_start_needed <= available_without_rvs5:
        # Allocate to RVS_1 and RVS_2
        remaining = s_start_needed
        
        # Fill RVS_1 first
        rvs_1_target = min(remaining, rvs_1_capacity)
        tank_allocation["RVS_1"] = rvs_1_target
        remaining -= rvs_1_target
        
        # Fill RVS_2 next
        if remaining > 0:
            rvs_2_target = min(remaining, rvs_2_capacity)
            tank_allocation["RVS_2"] = rvs_2_target
            remaining -= rvs_2_target
        
        return CapacityCheckResult(
            feasible=True,
            required_stock=s_start_needed,
            available_capacity=available_without_rvs5,
            gap=0.0,
            uses_rvs_5=False,
            tank_allocation=tank_allocation,
            notes="Sufficient capacity in RVS_1 and RVS_2"
        )
    
    # Need RVS_5
    if not allow_rvs_5:
        gap = s_start_needed - available_without_rvs5
        return CapacityCheckResult(
            feasible=False,
            required_stock=s_start_needed,
            available_capacity=available_without_rvs5,
            gap=gap,
            uses_rvs_5=False,
            tank_allocation={},
            notes=f"Insufficient capacity. RVS_5 not available. Gap: {gap:.0f}t"
        )
    
    if not rvs_5:
        gap = s_start_needed - available_without_rvs5
        return CapacityCheckResult(
            feasible=False,
            required_stock=s_start_needed,
            available_capacity=available_without_rvs5,
            gap=gap,
            uses_rvs_5=False,
            tank_allocation={},
            notes=f"RVS_5 not found. Gap: {gap:.0f}t"
        )
    
    # Check if RVS_5 can store sunflower
    if not rvs_5.can_store_product("sunflower"):
        gap = s_start_needed - available_without_rvs5
        return CapacityCheckResult(
            feasible=False,
            required_stock=s_start_needed,
            available_capacity=available_without_rvs5,
            gap=gap,
            uses_rvs_5=False,
            tank_allocation={},
            notes=f"RVS_5 cannot store sunflower. Gap: {gap:.0f}t"
        )
    
    # Calculate RVS_5 capacity
    rvs_5_capacity = rvs_5.get_effective_capacity("sunflower")
    rvs_5_available = max(0, rvs_5_capacity - rvs_5_current)
    
    total_available = available_without_rvs5 + rvs_5_available
    
    if s_start_needed <= total_available:
        # Allocate across all three tanks
        remaining = s_start_needed
        
        # Fill RVS_1 first
        rvs_1_target = min(remaining, rvs_1_capacity)
        tank_allocation["RVS_1"] = rvs_1_target
        remaining -= rvs_1_target
        
        # Fill RVS_2 next
        if remaining > 0:
            rvs_2_target = min(remaining, rvs_2_capacity)
            tank_allocation["RVS_2"] = rvs_2_target
            remaining -= rvs_2_target
        
        # Fill RVS_5 last
        if remaining > 0:
            rvs_5_target = min(remaining, rvs_5_capacity)
            tank_allocation["RVS_5"] = rvs_5_target
            remaining -= rvs_5_target
        
        return CapacityCheckResult(
            feasible=True,
            required_stock=s_start_needed,
            available_capacity=total_available,
            gap=0.0,
            uses_rvs_5=True,
            tank_allocation=tank_allocation,
            notes="Requires RVS_5 (swing tank)"
        )
    else:
        # Even with RVS_5, not enough capacity
        gap = s_start_needed - total_available
        return CapacityCheckResult(
            feasible=False,
            required_stock=s_start_needed,
            available_capacity=total_available,
            gap=gap,
            uses_rvs_5=True,
            tank_allocation={},
            notes=f"Insufficient capacity even with RVS_5. Gap: {gap:.0f}t"
        )


# =============================================================================
# SECTION 5.3: Accumulation Plan
# =============================================================================

def generate_accumulation_operations(
    s_start_needed: float,
    current_inventory: Dict[str, float],
    rail_schedule: List[Dict[str, Any]],
    tanks: Dict[str, Tank],
    start_date: datetime,
    daily_rail_rate: float = None,  # type: ignore
) -> AccumulationPlan:
    """
    Generate rail-to-tank operations for stock accumulation.
    
    Creates Operation objects for each rail batch, distributing volume
    across tanks in priority order: RVS_1 → RVS_2 → RVS_5.
    
    Args:
        s_start_needed: Target stock level in tonnes
        current_inventory: Current stock levels
        rail_schedule: List of scheduled rail deliveries
        tanks: Tank configurations
        start_date: Start date for accumulation
        daily_rail_rate: Maximum daily rail intake (tonnes/day)
        
    Returns:
        AccumulationPlan with generated operations
        
    Example:
        >>> plan = generate_accumulation_operations(25000, {"RVS_1": 5000}, rail_schedule, tanks, start_date)
        >>> print(f"Need {plan.accumulation_days:.1f} days")
        Need 10.3 days
    """
    # Use config default if not provided
    if daily_rail_rate is None:
        batches_per_day = config.get('wagon.max_batches_per_day.summer', 4)
        wagons_per_batch = config.get('wagon.per_batch', 18)
        wagon_capacity = config.get('wagon.capacity', 65.0)
        daily_rail_rate = batches_per_day * wagons_per_batch * wagon_capacity

    # Calculate current total
    current_total = sum(current_inventory.get(tid, 0.0) for tid in ["RVS_1", "RVS_2", "RVS_5"])

    # Calculate deficit
    deficit = max(0, s_start_needed - current_total)

    if deficit == 0:
        return AccumulationPlan(
            operations=[],
            accumulation_days=0.0,
            daily_rate=daily_rail_rate,
            deficit=0.0,
            start_date=start_date,
            end_date=start_date,
        )
    
    # Calculate accumulation duration
    accumulation_days = deficit / daily_rail_rate
    end_date = start_date + timedelta(days=accumulation_days)
    
    # Generate operations from rail schedule
    operations = []
    accumulated = current_total
    tank_levels = current_inventory.copy()
    
    # Track which tank to fill next
    fill_order = ["RVS_1", "RVS_2", "RVS_5"]
    
    operation_date = start_date
    op_counter = 1
    
    # Process rail batches (assume 4 per day max)
    batches_per_day = DEFAULT_BATCHES_PER_DAY
    batch_volume = WAGONS_PER_BATCH * WAGON_CAPACITY  # wagons × capacity
    
    while accumulated < s_start_needed:
        for batch_num in range(batches_per_day):
            if accumulated >= s_start_needed:
                break
            
            # Determine target tank
            target_tank = None
            for tank_id in fill_order:
                if tank_id not in tanks:
                    continue
                
                tank = tanks[tank_id]
                current_level = tank_levels.get(tank_id, 0.0)
                capacity = tank.get_effective_capacity("sunflower")
                
                if current_level < capacity:
                    target_tank = tank_id
                    break
            
            if not target_tank:
                # All tanks full
                break
            
            # Calculate volume for this batch
            volume_needed = s_start_needed - accumulated
            volume_this_batch = min(batch_volume, volume_needed)
            
            # Check tank space
            tank = tanks[target_tank]
            current_level = tank_levels.get(target_tank, 0.0)
            capacity = tank.get_effective_capacity("sunflower")
            available_space = capacity - current_level
            volume_this_batch = min(volume_this_batch, available_space)
            
            # Create operation
            op_start = operation_date + timedelta(hours=batch_num * BATCH_DURATION_HOURS)  # Batches every BATCH_DURATION_HOURS
            duration = volume_this_batch / (batch_volume / BATCH_DURATION_HOURS)  # Duration per batch
            
            op = Operation(
                op_id=f"RAIL_ACC_{op_counter:03d}",
                op_type=OperationType.RAIL_BATCH,
                product="sunflower",
                source="Rail",
                target=target_tank,
                volume=volume_this_batch,
                start_time=op_start,
                duration=duration,
                wagons=18,
                notes=f"Accumulation for vessel loading"
            )
            
            operations.append(op)
            
            # Update tracking
            accumulated += volume_this_batch
            tank_levels[target_tank] = tank_levels.get(target_tank, 0.0) + volume_this_batch
            op_counter += 1
        
        # Move to next day
        operation_date += timedelta(days=1)
        
        # Safety check
        if operation_date > start_date + timedelta(days=60):
            break
    
    return AccumulationPlan(
        operations=operations,
        accumulation_days=(operation_date - start_date).days,
        daily_rate=daily_rail_rate,
        deficit=deficit,
        start_date=start_date,
        end_date=operation_date,
    )


# =============================================================================
# SECTION 5.4: Loading Plan with Direct Variant
# =============================================================================

def generate_loading_plan(
    vessel: Vessel,
    tank_status: Dict[str, float],
    tanks: Dict[str, Tank],
    loading_start: datetime,
    ship_load_rate: float = DEFAULT_SHIP_LOAD_RATE,
    pump_rate: float = DEFAULT_PUMP_RATE,
    rail_rate: float = DEFAULT_RAIL_RATE,
    use_direct_variant: Optional[bool] = None
) -> List[Operation]:
    """
    Generate ship loading operations with optional direct rail-to-ship variant.
    
    If tank pump rate is insufficient for ship loading rate, enables direct
    rail-to-ship transfer to supplement tank discharge.
    
    Direct Variant Conditions:
    - pump_rate < ship_load_rate
    - Combined rate = pump_rate + direct_rail_rate
    - Direct rail synchronized with tank discharge
    
    Args:
        vessel: Vessel to load
        tank_status: Current tank levels
        tanks: Tank configurations
        loading_start: Loading start time
        ship_load_rate: Ship loading rate (t/h)
        pump_rate: Tank pump rate (t/h)
        rail_rate: Rail discharge rate (t/h)
        use_direct_variant: Force enable/disable (auto if None)
        
    Returns:
        List of loading operations
        
    Example:
        >>> ops = generate_loading_plan(vessel, tank_status, tanks, start_time)
        >>> for op in ops:
        ...     print(f"{op.op_type}: {op.volume}t")
        LOAD: 35000t
    """
    operations = []
    
    # Determine if direct variant is needed
    if use_direct_variant is None:
        use_direct_variant = pump_rate < ship_load_rate
    
    # Calculate loading parameters
    vessel_volume = vessel.total_volume
    
    if use_direct_variant:
        # Direct variant: Tank + Rail → Ship
        direct_rate = min(rail_rate, ship_load_rate - pump_rate)
        combined_rate = pump_rate + direct_rate
        
        # Ensure combined rate doesn't exceed ship max
        if combined_rate > ship_load_rate:
            combined_rate = ship_load_rate
            direct_rate = ship_load_rate - pump_rate
        
        loading_duration = vessel_volume / combined_rate
        
        # Volume from tanks
        tank_volume = pump_rate * loading_duration
        
        # Volume direct from rail
        direct_volume = direct_rate * loading_duration
        
        # Create tank discharge operation
        primary_tank = None
        for tank_id in ["RVS_1", "RVS_2", "RVS_5"]:
            if tank_id in tank_status and tank_status[tank_id] > MIN_TANK_VOLUME_THRESHOLD:
                primary_tank = tank_id
                break
        
        if primary_tank:
            tank_op = Operation(
                op_id=f"LOAD_TANK_{vessel.vessel_id}",
                vessel_id=vessel.vessel_id,
                op_type=OperationType.LOAD,
                product="sunflower",
                source=primary_tank,
                target="Ship",
                volume=tank_volume,
                start_time=loading_start,
                duration=loading_duration,
                notes=f"Tank discharge for {vessel.vessel_id}"
            )
            operations.append(tank_op)
        
        # Create direct rail-to-ship operation
        direct_op = Operation(
            op_id=f"LOAD_DIRECT_{vessel.vessel_id}",
            vessel_id=vessel.vessel_id,
            op_type=OperationType.DISCHARGE,
            product="sunflower",
            source="Rail",
            target="Ship",
            volume=direct_volume,
            start_time=loading_start,
            duration=loading_duration,
            line="Line2",
            notes=f"Direct rail-to-ship for {vessel.vessel_id}"
        )
        operations.append(direct_op)
        
    else:
        # Standard variant: Tank → Ship only
        loading_duration = vessel_volume / pump_rate
        
        # Select primary source tank
        primary_tank = None
        for tank_id in ["RVS_1", "RVS_2", "RVS_5"]:
            if tank_id in tank_status and tank_status[tank_id] > MIN_TANK_VOLUME_THRESHOLD:
                primary_tank = tank_id
                break
        
        if primary_tank:
            tank_op = Operation(
                op_id=f"LOAD_{vessel.vessel_id}",
                vessel_id=vessel.vessel_id,
                op_type=OperationType.LOAD,
                product="sunflower",
                source=primary_tank,
                target="Ship",
                volume=vessel_volume,
                start_time=loading_start,
                duration=loading_duration,
                notes=f"Ship loading {vessel.vessel_id}"
            )
            operations.append(tank_op)
    
    return operations
