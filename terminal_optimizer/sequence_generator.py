"""
Sequence Generator Module

This module generates operational sequences for vessel cargo handling.
It contains specialized logic for palm oil fractions and sunflower oil operations.

Classes:
    PalmSequenceGenerator: Handles palm fraction discharge sequencing
    SunflowerHandler: Handles sunflower loading with accumulation logic
    SequenceCoordinator: Merges and resolves conflicts between sequences
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Set
from collections import defaultdict
import math

from terminal_optimizer.domain_models import (
    Tank, Vessel, Operation, Scenario, CargoType, OperationType
)


from .constants import (
    PALM_FRACTION_PRIORITIES,
    LARGE_FRACTION_THRESHOLD,
    DIRECT_DISCHARGE_THRESHOLD,
    DEFAULT_SAFETY_MARGIN,
    RATE_SHIP_DISCHARGE_LINE1,
    RATE_SHIP_DISCHARGE_LINE2_TANK,
    RATE_SHIP_DISCHARGE_LINE2_DIRECT,
    RATE_RAIL_DISCHARGE_SUMMER,
    RATE_SHIP_LOAD_MIN,
    RATE_SHIP_LOAD_MAX,
    RATE_SHT_TRANSFER,
    WAGON_CAPACITY,
    WAGONS_PER_BATCH,
    DEFAULT_BERTH_SHIFT_TIME,
    DEFAULT_UNBERTH_DURATION,
    DEFAULT_BUFFER_TIME,
    RAIL_BUFFER_TIME,
    MAX_CONFLICT_ITERATIONS,
    BERTH_PALM,
    BERTH_SUNFLOWER,
    CLEANING_LINE_DEFAULT,
    CLEANING_LINE_DIFFERENT_PALM,
    CLEANING_LINE_PALM_TO_SUNFLOWER,
)

# For backward compatibility
DEFAULT_LINE1_DISCHARGE_RATE = RATE_SHIP_DISCHARGE_LINE1
DEFAULT_LINE2_TANK_DISCHARGE_RATE = RATE_SHIP_DISCHARGE_LINE2_TANK
DEFAULT_LINE2_DIRECT_DISCHARGE_RATE = RATE_SHIP_DISCHARGE_LINE2_DIRECT
DEFAULT_RAIL_DISCHARGE_RATE = RATE_RAIL_DISCHARGE_SUMMER
DEFAULT_SHIP_LOAD_RATE_MIN = RATE_SHIP_LOAD_MIN
DEFAULT_SHIP_LOAD_RATE_MAX = RATE_SHIP_LOAD_MAX
DEFAULT_SHT_TRANSFER_RATE = RATE_SHT_TRANSFER
WAGON_CAPACITY_TONNES = WAGON_CAPACITY
DEFAULT_WAGONS_PER_BATCH = WAGONS_PER_BATCH


@dataclass
class FractionAllocation:
    """Represents allocation of a fraction to a specific line and tank."""
    hold_id: str
    fraction: str
    volume: float
    line: str  # Line1 or Line2
    tank: str  # Tank ID
    is_direct: bool = False  # True if bypassing shore tank (Line2 only)
    priority: int = 0
    
    def __repr__(self) -> str:
        direct_str = " (direct)" if self.is_direct else ""
        return f"{self.hold_id}: {self.fraction} {self.volume}t -> {self.line} -> {self.tank}{direct_str}"


class PalmSequenceGenerator:
    """
    Generates operational sequences for palm oil vessel discharge.
    
    Handles:
    - Classification of fractions by size
    - Allocation to Line1 (900 t/h) or Line2 (500 t/h or 146 t/h direct)
    - Tank assignment (RVS-3, RVS-5, SHT)
    - Cleaning operations between incompatible products
    """
    
    def __init__(self, tanks: Dict[str, Tank], parameters: Optional[Dict[str, Any]] = None):
        """
        Initialize palm sequence generator.
        
        Args:
            tanks: Dictionary of available tanks
            parameters: Scenario parameters
        """
        self.tanks = tanks
        self.parameters = parameters or {}
        self.operation_counter = 0
    
    def _next_op_id(self, prefix: str = "OP") -> str:
        """Generate next operation ID."""
        self.operation_counter += 1
        return f"{prefix}_{self.operation_counter:04d}"
    
    def classify_fractions(
        self,
        vessel: Vessel
    ) -> Tuple[List[FractionAllocation], List[FractionAllocation]]:
        """
        Classify fractions into large (>5000t) and small (<=5000t).
        
        Args:
            vessel: Palm vessel with cargo plan
            
        Returns:
            Tuple of (large_fractions, small_fractions)
        """
        large = []
        small = []
        
        fractions = vessel.get_fractions()
        
        for hold_id, fraction, volume in fractions:
            priority = PALM_FRACTION_PRIORITIES.get(fraction, 0)
            
            allocation = FractionAllocation(
                hold_id=hold_id,
                fraction=fraction,
                volume=volume,
                line="",  # Will be assigned later
                tank="",  # Will be assigned later
                priority=priority
            )
            
            if volume > LARGE_FRACTION_THRESHOLD:
                large.append(allocation)
            else:
                small.append(allocation)
        
        # Sort by priority (descending)
        large.sort(key=lambda x: x.priority, reverse=True)
        small.sort(key=lambda x: x.priority, reverse=True)
        
        return large, small
    
    def allocate_lines(
        self,
        large_fractions: List[FractionAllocation],
        small_fractions: List[FractionAllocation]
    ) -> Dict[str, List[FractionAllocation]]:
        """
        Allocate fractions to Line1 (large) and Line2 (small).
        
        Args:
            large_fractions: Large fractions (>5000t)
            small_fractions: Small fractions (<=5000t)
            
        Returns:
            Dict with keys 'line1' and 'line2' containing allocated fractions
        """
        line1_ops = []
        line2_ops = []
        
        # Large fractions go to Line1 (900 t/h)
        for alloc in large_fractions:
            alloc.line = "Line1"
            line1_ops.append(alloc)
        
        # Small fractions go to Line2 (500 t/h via tank or 146 t/h direct)
        for alloc in small_fractions:
            alloc.line = "Line2"
            # Very small fractions can go direct to rail
            if alloc.volume < DIRECT_DISCHARGE_THRESHOLD:
                alloc.is_direct = True
            line2_ops.append(alloc)
        
        return {
            "line1": line1_ops,
            "line2": line2_ops
        }
    
    def allocate_tanks(
        self,
        line_allocations: Dict[str, List[FractionAllocation]],
        current_inventory: Dict[str, Dict[str, Any]]
    ) -> List[FractionAllocation]:
        """
        Allocate specific tanks to each fraction.
        
        Args:
            line_allocations: Fractions allocated to Line1 and Line2
            current_inventory: Current state of tanks
            
        Returns:
            List of all allocations with tank assignments
        """
        all_allocations = []
        
        # Track current tank states
        tank_states = {}
        for tank_id, info in current_inventory.items():
            tank_states[tank_id] = {
                "product": info.get("current_product"),
                "volume": info.get("current_volume", 0.0)
            }
        
        # Allocate Line1 fractions to RVS-3 or RVS-5
        for alloc in line_allocations["line1"]:
            # Prefer RVS-3 (dedicated palm tank)
            if self._can_use_tank("RVS_3", alloc, tank_states):
                alloc.tank = "RVS_3"
                tank_states["RVS_3"]["product"] = alloc.fraction
            elif self._can_use_tank("RVS_5", alloc, tank_states):
                alloc.tank = "RVS_5"
                tank_states["RVS_5"]["product"] = alloc.fraction
            else:
                # If neither available, queue for RVS-3
                alloc.tank = "RVS_3"
            
            all_allocations.append(alloc)
        
        # Allocate Line2 fractions
        for alloc in line_allocations["line2"]:
            if alloc.is_direct:
                # Direct to rail, no tank needed
                alloc.tank = "DIRECT_RAIL"
            else:
                # Use Shore Tank (SHT)
                alloc.tank = "SHT"
            
            all_allocations.append(alloc)
        
        return all_allocations
    
    def _can_use_tank(
        self,
        tank_id: str,
        alloc: FractionAllocation,
        tank_states: Dict[str, Dict[str, Any]]
    ) -> bool:
        """Check if a tank can be used for this fraction."""
        tank = self.tanks.get(tank_id)
        if not tank:
            return False
        
        # Check if product is allowed
        if not tank.can_store_product(alloc.fraction):
            return False
        
        state = tank_states.get(tank_id, {})
        current_product = state.get("product")
        current_volume = state.get("volume", 0.0)
        
        # If tank is empty or has same product, OK
        if not current_product or current_volume == 0:
            return True
        
        if current_product == alloc.fraction:
            return True
        
        # Different product - would need cleaning
        # For now, return False (will handle cleaning in sequence generation)
        return False
    
    def generate_sequence(
        self,
        vessel: Vessel,
        allocations: List[FractionAllocation],
        current_inventory: Dict[str, Dict[str, Any]],
        start_time: datetime,
        line_status: Optional[Dict[str, Optional[str]]] = None
    ) -> List[Operation]:
        """
        Generate complete operation sequence for palm vessel.
        
        Args:
            vessel: Palm vessel
            allocations: Tank allocations for each fraction
            current_inventory: Current tank states
            start_time: When vessel operations can begin
            line_status: Optional dict tracking last product on 'Line1' and 'Line2'
            
        Returns:
            List of Operation objects in chronological order
        """
        operations = []
        current_time = start_time
        
        # Track tank states through operations
        tank_products = {
            tank_id: info.get("current_product")
            for tank_id, info in current_inventory.items()
        }
        
        # Track line states
        line_products = line_status.copy() if line_status else {}
        
        # 1. Berthing operation
        berth_op = Operation(
            op_id=self._next_op_id("BERTH"),
            vessel_id=vessel.vessel_id,
            op_type=OperationType.BERTHING,
            target=BERTH_PALM,
            start_time=start_time,
            duration=self.parameters.get("berth_shift_time", DEFAULT_BERTH_SHIFT_TIME),
            notes=f"Berthing {vessel.vessel_id} at {BERTH_PALM}"
        )
        operations.append(berth_op)
        
        # Apply buffer after berthing
        buffer_hours = self.parameters.get("buffer_time", DEFAULT_BUFFER_TIME)
        if berth_op.end_time is None:
            raise ValueError(f"Operation {berth_op.op_id} has no end time")
        current_time = berth_op.end_time + timedelta(hours=buffer_hours)
        
        # 2. Process each allocation
        line1_ops = [a for a in allocations if a.line == "Line1"]
        line2_ops = [a for a in allocations if a.line == "Line2"]
        
        # Line1 and Line2 can operate in parallel
        line1_time = current_time
        line2_time = current_time
        
        # Generate Line1 operations
        for alloc in line1_ops:
            # Check if Line1 needs cleaning
            last_line1_product = line_products.get("Line1")
            if last_line1_product and last_line1_product != alloc.fraction:
                # Determine cleaning duration
                cleaning_duration = CLEANING_LINE_DEFAULT
                if "palm" in last_line1_product and "palm" in alloc.fraction:
                    cleaning_duration = CLEANING_LINE_DIFFERENT_PALM
                
                cleaning_op = Operation(
                    op_id=self._next_op_id("CLEAN_L1"),
                    vessel_id=vessel.vessel_id,
                    op_type=OperationType.CLEANING,
                    target="Line1",
                    start_time=line1_time,
                    duration=cleaning_duration,
                    notes=f"Cleaning Line1 from {last_line1_product} to {alloc.fraction}"
                )
                operations.append(cleaning_op)
                if cleaning_op.end_time is None:
                    raise ValueError(f"Operation {cleaning_op.op_id} has no end time")
                line1_time = cleaning_op.end_time + timedelta(hours=0.5) # Small buffer after cleaning
                line_products["Line1"] = None # Cleaned

            # Check if tank cleaning needed
            tank_cleaning_op = None
            if tank_products.get(alloc.tank) and tank_products[alloc.tank] != alloc.fraction:
                tank = self.tanks[alloc.tank]
                current_product = tank_products[alloc.tank]
                # Ensure current_product is not None before calling get_cleaning_duration
                if current_product is None:
                    cleaning_hours = 0.0
                else:
                    cleaning_hours = tank.get_cleaning_duration(current_product, alloc.fraction)
                
                tank_cleaning_op = Operation(
                    op_id=self._next_op_id("CLEAN"),
                    vessel_id=vessel.vessel_id,
                    op_type=OperationType.CLEANING,
                    target=alloc.tank,
                    start_time=line1_time,
                    duration=cleaning_hours,
                    notes=f"Cleaning {alloc.tank} from {tank_products[alloc.tank]} to {alloc.fraction}"
                )
                operations.append(tank_cleaning_op)
                if tank_cleaning_op.end_time is None:
                    raise ValueError(f"Operation {tank_cleaning_op.op_id} has no end time")
                line1_time = tank_cleaning_op.end_time + timedelta(hours=buffer_hours)
                tank_products[alloc.tank] = None  # Tank is clean
            
            # Discharge operation
            rate = self.parameters.get("ship_discharge_line1", DEFAULT_LINE1_DISCHARGE_RATE)
            duration = alloc.volume / rate
            
            deps = []
            if tank_cleaning_op:
                deps.append(tank_cleaning_op.op_id)
            
            discharge_op = Operation(
                op_id=self._next_op_id("DISCH"),
                vessel_id=vessel.vessel_id,
                op_type=OperationType.DISCHARGE,
                product=alloc.fraction,
                source=f"Ship_{vessel.vessel_id}_{alloc.hold_id}",
                target=alloc.tank,
                volume=alloc.volume,
                start_time=line1_time,
                duration=duration,
                line="Line1",
                dependencies=deps,
                notes=f"Discharge {alloc.hold_id}: {alloc.fraction}"
            )
            operations.append(discharge_op)
            if discharge_op.end_time is None:
                raise ValueError(f"Operation {discharge_op.op_id} has no end time")
            line1_time = discharge_op.end_time + timedelta(hours=buffer_hours)
            tank_products[alloc.tank] = alloc.fraction
            line_products["Line1"] = alloc.fraction
       
        # Generate Line2 operations
        sht_last_product = tank_products.get("SHT")
        
        for alloc in line2_ops:
            # Check if Line2 needs cleaning
            last_line2_product = line_products.get("Line2")
            if last_line2_product and last_line2_product != alloc.fraction:
                # Determine cleaning duration
                cleaning_duration = CLEANING_LINE_DEFAULT
                if "palm" in last_line2_product and "palm" in alloc.fraction:
                    cleaning_duration = CLEANING_LINE_DIFFERENT_PALM
                
                cleaning_op = Operation(
                    op_id=self._next_op_id("CLEAN_L2"),
                    vessel_id=vessel.vessel_id,
                    op_type=OperationType.CLEANING,
                    target="Line2",
                    start_time=line2_time,
                    duration=cleaning_duration,
                    notes=f"Cleaning Line2 from {last_line2_product} to {alloc.fraction}"
                )
                operations.append(cleaning_op)
                if cleaning_op.end_time is None:
                    raise ValueError(f"Operation {cleaning_op.op_id} has no end time")
                line2_time = cleaning_op.end_time + timedelta(hours=0.5)
                line_products["Line2"] = None

            if alloc.is_direct:
                # Direct discharge to rail
                rate = self.parameters.get("ship_discharge_line2_direct", DEFAULT_LINE2_DIRECT_DISCHARGE_RATE)
                duration = alloc.volume / rate
                
                discharge_op = Operation(
                    op_id=self._next_op_id("DISCH"),
                    vessel_id=vessel.vessel_id,
                    op_type=OperationType.DISCHARGE,
                    product=alloc.fraction,
                    source=f"Ship_{vessel.vessel_id}_{alloc.hold_id}",
                    target="DIRECT_RAIL",
                    volume=alloc.volume,
                    start_time=line2_time,
                    duration=duration,
                    line="Line2",
                    wagons=math.ceil(alloc.volume / WAGON_CAPACITY_TONNES),
                    notes=f"Direct discharge {alloc.hold_id}: {alloc.fraction}"
                )
                operations.append(discharge_op)
                if discharge_op.end_time is None:
                    raise ValueError(f"Operation {discharge_op.op_id} has no end time")
                line2_time = discharge_op.end_time + timedelta(hours=buffer_hours)
                line_products["Line2"] = alloc.fraction
            else:
                # Discharge to shore tank
                rate = self.parameters.get("ship_discharge_line2_tank", DEFAULT_LINE2_TANK_DISCHARGE_RATE)
                duration = alloc.volume / rate
                
                # Check if SHT needs emptying first
                # Note: current_inventory is the INITIAL state, we need to track dynamic volume
                # But for simplicity, we assume SHT is emptied after each use in this loop
                # So we only check initial volume once, or track it properly.
                # Actually, the logic below empties it immediately after filling.
                # So SHT should be empty here unless it had initial inventory.
                
                # If this is the first operation and SHT has initial inventory
                if sht_last_product and tank_products.get("SHT") is not None:
                    sht_volume = current_inventory.get("SHT", {}).get("current_volume", 0.0)
                    if sht_volume > 0:
                        # Need to empty SHT to rail first
                        empty_rate = DEFAULT_SHT_TRANSFER_RATE
                        empty_duration = sht_volume / empty_rate
                        
                        empty_op = Operation(
                            op_id=self._next_op_id("XFER"),
                            op_type=OperationType.TRANSFER,
                            product=sht_last_product,
                            source="SHT",
                            target="Rail",
                            volume=sht_volume,
                            start_time=line2_time,
                            duration=empty_duration,
                            wagons=math.ceil(sht_volume / WAGON_CAPACITY_TONNES),
                            notes="Empty SHT before new discharge"
                        )
                        operations.append(empty_op)
                        if empty_op.end_time is None:
                            raise ValueError(f"Operation {empty_op.op_id} has no end time")
                        line2_time = empty_op.end_time + timedelta(hours=buffer_hours)
                        tank_products["SHT"] = None
                        # Update current_inventory to reflect it's empty so we don't empty it again
                        if "SHT" in current_inventory:
                            current_inventory["SHT"]["current_volume"] = 0.0
                
                # Check if cleaning is needed for SHT
                sht_cleaning_op = None
                if sht_last_product and sht_last_product != alloc.fraction:
                    tank = self.tanks.get("SHT")
                    if tank:
                        cleaning_hours = tank.get_cleaning_duration(sht_last_product, alloc.fraction)
                        if cleaning_hours > 0:
                            sht_cleaning_op = Operation(
                                op_id=self._next_op_id("CLEAN"),
                                vessel_id=vessel.vessel_id,
                                op_type=OperationType.CLEANING,
                                target="SHT",
                                start_time=line2_time,
                                duration=cleaning_hours,
                                notes=f"Cleaning SHT from {sht_last_product} to {alloc.fraction}"
                            )
                            operations.append(sht_cleaning_op)
                            if sht_cleaning_op.end_time is None:
                                raise ValueError(f"Operation {sht_cleaning_op.op_id} has no end time")
                            line2_time = sht_cleaning_op.end_time + timedelta(hours=buffer_hours)
                            sht_last_product = None # Cleaned
                
                deps = []
                if sht_cleaning_op:
                    deps.append(sht_cleaning_op.op_id)

                discharge_op = Operation(
                    op_id=self._next_op_id("DISCH"),
                    vessel_id=vessel.vessel_id,
                    op_type=OperationType.DISCHARGE,
                    product=alloc.fraction,
                    source=f"Ship_{vessel.vessel_id}_{alloc.hold_id}",
                    target="SHT",
                    volume=alloc.volume,
                    start_time=line2_time,
                    duration=duration,
                    line="Line2",
                    dependencies=deps,
                    notes=f"Discharge {alloc.hold_id}: {alloc.fraction} to SHT"
                )
                operations.append(discharge_op)
                if discharge_op.end_time is None:
                    raise ValueError(f"Operation {discharge_op.op_id} has no end time")
                line2_time = discharge_op.end_time + timedelta(hours=buffer_hours)
                tank_products["SHT"] = alloc.fraction
                sht_last_product = alloc.fraction
                line_products["Line2"] = alloc.fraction
                
                # Then transfer from SHT to rail
                xfer_duration = alloc.volume / DEFAULT_SHT_TRANSFER_RATE
                xfer_op = Operation(
                    op_id=self._next_op_id("XFER"),
                    op_type=OperationType.TRANSFER,
                    product=alloc.fraction,
                    source="SHT",
                    target="Rail",
                    volume=alloc.volume,
                    start_time=line2_time,
                    duration=xfer_duration,
                    wagons=math.ceil(alloc.volume / WAGON_CAPACITY_TONNES),
                    dependencies=[discharge_op.op_id],
                    notes=f"Transfer {alloc.fraction} from SHT to rail"
                )
                operations.append(xfer_op)
                if xfer_op.end_time is None:
                    raise ValueError(f"Operation {xfer_op.op_id} has no end time")
                line2_time = xfer_op.end_time + timedelta(hours=buffer_hours)
                tank_products["SHT"] = None  # SHT is empty again
        
        # 3. Unberthing - after both lines complete
        # Ensure we have valid times (end_time should never be None if operations were created properly)
        if line1_time is None or line2_time is None:
            completion_time = current_time
        else:
            completion_time = max(line1_time, line2_time)
        
        unberth_op = Operation(
            op_id=self._next_op_id("UNBERTH"),
            vessel_id=vessel.vessel_id,
            op_type=OperationType.UNBERTHING,
            target=BERTH_PALM,
            start_time=completion_time,
            duration=DEFAULT_UNBERTH_DURATION,
            notes=f"Unberthing {vessel.vessel_id} from {BERTH_PALM}"
        )
        operations.append(unberth_op)
        
        return operations


class SunflowerHandler:
    """
    Handles sunflower oil loading operations with accumulation logic.
    
    Implements the "critical point" method for calculating required
    tank accumulation before ship loading can begin.
    """
    
    def __init__(self, tanks: Dict[str, Tank], parameters: Optional[Dict[str, Any]] = None):
        """
        Initialize sunflower handler.
        
        Args:
            tanks: Dictionary of available tanks
            parameters: Scenario parameters
        """
        self.tanks = tanks
        self.parameters = parameters or {}
        self.operation_counter = 0
    
    def _next_op_id(self, prefix: str = "OP") -> str:
        """Generate next operation ID."""
        self.operation_counter += 1
        return f"{prefix}_{self.operation_counter:04d}"
    
    def calculate_critical_start_point(
        self,
        vessel_volume: float,
        rail_rate: float,
        ship_rate: float,
        safety_margin: float = DEFAULT_SAFETY_MARGIN
    ) -> float:
        """
        Calculate critical starting volume needed in tanks before ship loading begins.
        
        The critical point is the minimum volume that must be accumulated to ensure
        continuous loading, accounting for parallel rail contributions.
        
        Args:
            vessel_volume: Total volume to load (tonnes)
            rail_rate: Rail discharge rate (t/h)
            ship_rate: Ship loading rate (t/h)
            safety_margin: Safety factor (default 10%)
            
        Returns:
            Required starting volume in tanks (tonnes)
        """
        # Time to load entire vessel
        t_loading = vessel_volume / ship_rate
        
        # Volume contributed by rail during loading
        rail_contribution = rail_rate * t_loading
        
        # Required starting volume (before loading starts)
        s_start = vessel_volume - rail_contribution
        
        # Apply safety margin
        s_start_safe = s_start * (1 + safety_margin)
        
        return max(0, s_start_safe)
    
    def check_capacity_available(
        self,
        s_start_needed: float,
        current_inventory: Dict[str, Dict[str, Any]]
    ) -> Tuple[bool, float, bool]:
        """
        Check if sufficient tank capacity is available for accumulation.
        
        Args:
            s_start_needed: Required starting volume
            current_inventory: Current tank states
            
        Returns:
            Tuple of (is_feasible, gap, uses_rvs5)
            - is_feasible: True if capacity is sufficient
            - gap: Shortfall if not feasible, 0 otherwise
            - uses_rvs5: True if RVS-5 is needed
        """
        # Calculate available capacity in dedicated sunflower tanks
        rvs1 = self.tanks.get("RVS_1")
        rvs2 = self.tanks.get("RVS_2")
        rvs5 = self.tanks.get("RVS_5")
        
        if not rvs1 or not rvs2:
            return False, s_start_needed, False
        
        # Effective capacity (accounting for deadstock)
        cap_rvs1 = rvs1.get_effective_capacity("sunflower")
        cap_rvs2 = rvs2.get_effective_capacity("sunflower")
        
        # Current volumes (only count sunflower)
        inv_rvs1 = current_inventory.get("RVS_1", {})
        inv_rvs2 = current_inventory.get("RVS_2", {})
        
        vol_rvs1 = inv_rvs1.get("current_volume", 0.0) if inv_rvs1.get("current_product") == "sunflower" else 0.0
        vol_rvs2 = inv_rvs2.get("current_volume", 0.0) if inv_rvs2.get("current_product") == "sunflower" else 0.0
        
        # Calculate: existing sunflower + available space
        existing_sunflower = vol_rvs1 + vol_rvs2
        avail_rvs1 = cap_rvs1 - vol_rvs1
        avail_rvs2 = cap_rvs2 - vol_rvs2
        total_capacity_without_rvs5 = existing_sunflower + avail_rvs1 + avail_rvs2
        
        if s_start_needed <= total_capacity_without_rvs5:
            return True, 0.0, False
        
        # Check if RVS-5 can help
        if rvs5 and rvs5.can_store_product("sunflower"):
            inv_rvs5 = current_inventory.get("RVS_5", {})
            rvs5_product = inv_rvs5.get("current_product")
            
            # Only use RVS-5 if it's empty or has sunflower
            if rvs5_product is None or rvs5_product == "sunflower":
                cap_rvs5 = rvs5.get_effective_capacity("sunflower")
                vol_rvs5 = inv_rvs5.get("current_volume", 0.0) if rvs5_product == "sunflower" else 0.0
                avail_rvs5 = cap_rvs5 - vol_rvs5
                existing_in_rvs5 = vol_rvs5 if rvs5_product == "sunflower" else 0.0
                
                total_capacity_with_rvs5 = total_capacity_without_rvs5 + existing_in_rvs5 + avail_rvs5
                
                if s_start_needed <= total_capacity_with_rvs5:
                    return True, 0.0, True
                else:
                    gap = s_start_needed - total_capacity_with_rvs5
                    return False, gap, True
        
        gap = s_start_needed - total_capacity_without_rvs5
        return False, gap, False
    
    def generate_accumulation_plan(
        self,
        s_start_needed: float,
        rail_schedule: List[Dict[str, Any]],
        current_inventory: Dict[str, Dict[str, Any]],
        start_time: datetime
    ) -> List[Operation]:
        """
        Generate rail discharge operations to accumulate required volume.
        
        Args:
            s_start_needed: Required starting volume in tanks
            rail_schedule: Incoming rail deliveries
            current_inventory: Current tank states
            start_time: When accumulation should begin
            
        Returns:
            List of rail discharge operations
        """
        operations = []
        
        # Calculate current sunflower in tanks
        current_total = 0.0
        for tank_id in ["RVS_1", "RVS_2", "RVS_5"]:
            inv = current_inventory.get(tank_id, {})
            if inv.get("current_product") == "sunflower":
                current_total += inv.get("current_volume", 0.0)
        
        # Calculate deficit
        deficit = s_start_needed - current_total
        
        if deficit <= 0:
            return operations  # Already have enough
        
        # Generate rail discharge operations
        accumulated = 0.0
        current_time = start_time
        batch_num = 0
        
        # Typical batch size: DEFAULT_WAGONS_PER_BATCH * WAGON_CAPACITY_TONNES = 1170t
        batch_size = DEFAULT_WAGONS_PER_BATCH * WAGON_CAPACITY_TONNES
        rate = self.parameters.get("rail_discharge_rate", DEFAULT_RAIL_DISCHARGE_RATE)
        
        # Fill RVS-1, then RVS-2, then RVS-5 if needed
        tank_order = ["RVS_1", "RVS_2", "RVS_5"]
        tank_idx = 0
        
        while accumulated < deficit and tank_idx < len(tank_order):
            tank_id = tank_order[tank_idx]
            tank = self.tanks.get(tank_id)
            
            if not tank or not tank.can_store_product("sunflower"):
                tank_idx += 1
                continue
            
            # Available space in this tank
            inv = current_inventory.get(tank_id, {})
            current_vol = inv.get("current_volume", 0.0)
            effective_cap = tank.get_effective_capacity("sunflower")
            available = effective_cap - current_vol
            
            if available <= 0:
                tank_idx += 1
                continue
            
            # Determine batch volume (don't exceed tank space or remaining deficit)
            remaining_deficit = deficit - accumulated
            batch_volume = min(batch_size, available, remaining_deficit)
            
            # Create rail discharge operation
            duration = batch_volume / rate
            wagons = math.ceil(batch_volume / WAGON_CAPACITY_TONNES)
            
            rail_op = Operation(
                op_id=self._next_op_id("RAIL"),
                op_type=OperationType.RAIL_BATCH,
                product="sunflower",
                source="Rail",
                target=tank_id,
                volume=batch_volume,
                start_time=current_time,
                duration=duration,
                wagons=wagons,
                notes=f"Accumulation batch {batch_num + 1} for sunflower loading"
            )
            operations.append(rail_op)
            
            accumulated += batch_volume
            # Use specific rail buffer
            buffer_hours = self.parameters.get("rail_buffer_time", RAIL_BUFFER_TIME)
            if rail_op.end_time is None:
                raise ValueError(f"Operation {rail_op.op_id} has no end time")
            current_time = rail_op.end_time + timedelta(hours=buffer_hours)
            batch_num += 1
            
            # Update current volume for next iteration
            inv["current_volume"] = current_vol + batch_volume
        
        return operations
    
    def generate_loading_plan(
        self,
        vessel: Vessel,
        tank_status: Dict[str, Dict[str, Any]],
        start_time: datetime,
        use_direct_variant: bool = False
    ) -> List[Operation]:
        """
        Generate ship loading operations.
        
        Args:
            vessel: Sunflower vessel to load
            tank_status: Current tank states (after accumulation)
            start_time: When loading can begin
            use_direct_variant: If True, use parallel rail-to-ship loading
            
        Returns:
            List of loading operations
        """
        operations = []
        
        # Berthing
        berth_op = Operation(
            op_id=self._next_op_id("BERTH"),
            vessel_id=vessel.vessel_id,
            op_type=OperationType.BERTHING,
            target=BERTH_SUNFLOWER,
            start_time=start_time,
            duration=self.parameters.get("berth_shift_time", DEFAULT_BERTH_SHIFT_TIME),
            notes=f"Berthing {vessel.vessel_id} at {BERTH_SUNFLOWER}"
        )
        operations.append(berth_op)
        
        buffer_hours = self.parameters.get("buffer_time", DEFAULT_BUFFER_TIME)
        if berth_op.end_time is None:
            raise ValueError(f"Operation {berth_op.op_id} has no end time")
        load_start = berth_op.end_time + timedelta(hours=buffer_hours)
        
        # Loading operation
        if use_direct_variant:
            # Parallel loading: Tank + Rail -> Ship
            pump_rate = self.parameters.get("ship_load_rate_min", DEFAULT_SHIP_LOAD_RATE_MIN)
            rail_rate = self.parameters.get("rail_discharge_rate", DEFAULT_RAIL_DISCHARGE_RATE)
            combined_rate = min(
                pump_rate + rail_rate,
                self.parameters.get("ship_load_rate_max", DEFAULT_SHIP_LOAD_RATE_MAX)
            )
            
            duration = vessel.total_volume / combined_rate
            
            load_op = Operation(
                op_id=self._next_op_id("LOAD"),
                vessel_id=vessel.vessel_id,
                op_type=OperationType.LOAD,
                product="sunflower",
                source="RVS_1+RVS_2+Rail",
                target=f"Ship_{vessel.vessel_id}",
                volume=vessel.total_volume,
                start_time=load_start,
                duration=duration,
                notes="Loading with direct rail booster"
            )
            operations.append(load_op)
        else:
            # Standard loading from tanks only
            rate = (
                self.parameters.get("ship_load_rate_min", DEFAULT_SHIP_LOAD_RATE_MIN) +
                self.parameters.get("ship_load_rate_max", DEFAULT_SHIP_LOAD_RATE_MAX)
            ) / 2
            duration = vessel.total_volume / rate
            
            load_op = Operation(
                op_id=self._next_op_id("LOAD"),
                vessel_id=vessel.vessel_id,
                op_type=OperationType.LOAD,
                product="sunflower",
                source="RVS_1+RVS_2",
                target=f"Ship_{vessel.vessel_id}",
                volume=vessel.total_volume,
                start_time=load_start,
                duration=duration,
                notes="Standard tank loading"
            )
            operations.append(load_op)
        
        # Unberthing
        unberth_op = Operation(
            op_id=self._next_op_id("UNBERTH"),
            vessel_id=vessel.vessel_id,
            op_type=OperationType.UNBERTHING,
            target=BERTH_SUNFLOWER,
            start_time=load_op.end_time,
            duration=DEFAULT_UNBERTH_DURATION,
            notes=f"Unberthing {vessel.vessel_id} from {BERTH_SUNFLOWER}"
        )
        operations.append(unberth_op)
        
        return operations


class SequenceCoordinator:
    """
    Coordinates and merges operational sequences for multiple vessels.
    
    Handles:
    - Merging palm and sunflower sequences
    - Detecting resource conflicts
    - Resolving conflicts through rescheduling
    """
    
    def __init__(self, tanks: Dict[str, Tank], parameters: Optional[Dict[str, Any]] = None):
        """
        Initialize sequence coordinator.
        
        Args:
            tanks: Dictionary of available tanks
            parameters: Scenario parameters
        """
        self.tanks = tanks
        self.parameters = parameters or {}
    
    def merge_sequences(
        self,
        sequences: List[List[Operation]]
    ) -> List[Operation]:
        """
        Merge multiple operation sequences into one.
        
        Args:
            sequences: List of operation sequences to merge
            
        Returns:
            Combined list of operations (may need conflict resolution)
        """
        merged = []
        for seq in sequences:
            merged.extend(seq)
        
        # Sort by start time
        merged.sort(key=lambda op: op.start_time if op.start_time else datetime.max)
        
        return merged
    
    def check_conflicts(
        self,
        operations: List[Operation]
    ) -> List[Tuple[Operation, Operation, str]]:
        """
        Detect conflicts between operations.
        
        Args:
            operations: List of operations to check
            
        Returns:
            List of (op1, op2, conflict_type) tuples
        """
        conflicts = []
        
        # Check for resource conflicts
        # Group operations by resource (tank, berth, rail platform)
        resource_ops: Dict[str, List[Operation]] = defaultdict(list)
        
        for op in operations:
            # Track tank usage
            if op.target in self.tanks:
                resource_ops[op.target].append(op)
            if op.source in self.tanks:
                resource_ops[op.source].append(op)
            
            # Track berth usage
            if op.op_type in [OperationType.BERTHING, OperationType.UNBERTHING,
                             OperationType.DISCHARGE, OperationType.LOAD]:
                if op.vessel_id:
                    # Determine which berth is being used
                    if op.target == BERTH_PALM or op.source == BERTH_PALM:
                        resource_ops[BERTH_PALM].append(op)
                    elif op.target == BERTH_SUNFLOWER or op.source == BERTH_SUNFLOWER:
                        resource_ops[BERTH_SUNFLOWER].append(op)
                    elif op.product and "palm" in op.product.lower():
                        resource_ops[BERTH_PALM].append(op)
                    elif op.product and "sunflower" in op.product.lower():
                        resource_ops[BERTH_SUNFLOWER].append(op)
                    else:
                        # Fallback for unknown product/target
                        resource_ops["BERTH_GENERIC"].append(op)
            
            # Track rail platform
            if "Rail" in op.source or "Rail" in op.target:
                resource_ops["RAIL_PLATFORM"].append(op)
        
        # Check each resource for overlaps
        for resource, ops in resource_ops.items():
            # Sort by start time
            sorted_ops = sorted(
                [o for o in ops if o.start_time is not None and o.end_time is not None],
                key=lambda x: x.start_time if x.start_time is not None else datetime.min
            )
            
            # Check consecutive operations for overlap
            for i in range(len(sorted_ops) - 1):
                op1 = sorted_ops[i]
                op2 = sorted_ops[i + 1]
                
                if op1.overlaps_with(op2):
                    # Ignore berth conflicts for the same vessel
                    if "BERTH" in str(resource) and op1.vessel_id == op2.vessel_id:
                        continue
                        
                    conflicts.append((op1, op2, f"resource_conflict_{resource}"))
        
        return conflicts
    
    def resolve_conflict(
        self,
        op1: Operation,
        op2: Operation,
        conflict_type: str
    ) -> Operation:
        """
        Resolve a conflict by delaying the lower priority operation.
        
        Args:
            op1: First operation
            op2: Second operation
            conflict_type: Type of conflict
            
        Returns:
            The operation that was rescheduled
        """
        # Determine priority (locked operations have highest priority)
        # Ensure end_time is not None before passing to _delay_operation
        if op1.end_time is None or op2.end_time is None:
            raise ValueError(
                f"Cannot resolve conflict: operations {op1.op_id} or {op2.op_id} "
                "have no end_time"
            )
        
        if op1.user_locked and not op2.user_locked:
            # Delay op2
            return self._delay_operation(op2, op1.end_time)
        elif op2.user_locked and not op1.user_locked:
            # Delay op1
            return self._delay_operation(op1, op2.end_time)
        else:
            # Delay the later operation
            # Ensure start_time is not None before comparison
            if op1.start_time is None or op2.start_time is None:
                raise ValueError(
                    f"Cannot resolve conflict: operations {op1.op_id} or {op2.op_id} "
                    "have no start_time"
                )
            
            if op1.start_time <= op2.start_time:
                return self._delay_operation(op2, op1.end_time)
            else:
                return self._delay_operation(op1, op2.end_time)
    
    def _delay_operation(self, op: Operation, new_start: datetime) -> Operation:
        """Delay an operation to a new start time."""
        if op.start_time and new_start > op.start_time:
            op.update_timing(new_start)
        return op
    
    def _propagate_dependencies(self, operation: Operation, all_operations: List[Operation]) -> None:
        """
        Propagate timing changes to dependent operations.
        
        Args:
            operation: Operation that was modified
            all_operations: List of all operations to check for dependencies
        """
        if not operation.end_time:
            return

        for op in all_operations:
            if operation.op_id in op.dependencies:
                # Ensure dependent starts after this operation ends
                if op.start_time and op.start_time < operation.end_time:
                    op.update_timing(operation.end_time, op.duration)
                    # Recursively propagate
                    self._propagate_dependencies(op, all_operations)

    def resolve_all_conflicts(
        self,
        operations: List[Operation],
        max_iterations: int = MAX_CONFLICT_ITERATIONS
    ) -> Tuple[List[Operation], List[str]]:
        """
        Iteratively resolve all conflicts.
        
        Args:
            operations: List of operations
            max_iterations: Maximum resolution attempts
            
        Returns:
            Tuple of (resolved_operations, warnings)
        """
        warnings = []
        
        for iteration in range(max_iterations):
            conflicts = self.check_conflicts(operations)
            
            if not conflicts:
                break  # All conflicts resolved
            
            # Resolve each conflict
            for op1, op2, conflict_type in conflicts:
                rescheduled = self.resolve_conflict(op1, op2, conflict_type)
                self._propagate_dependencies(rescheduled, operations)
                warnings.append(
                    f"Iteration {iteration + 1}: Rescheduled {rescheduled.op_id} "
                    f"due to {conflict_type}"
                )
        
        # Check if any conflicts remain
        remaining = self.check_conflicts(operations)
        if remaining:
            warnings.append(
                f"WARNING: {len(remaining)} conflicts could not be resolved after "
                f"{max_iterations} iterations"
            )
        
        return operations, warnings
