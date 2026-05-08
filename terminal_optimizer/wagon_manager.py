"""
Wagon Manager Module

This module handles railway wagon calculations, distribution, and looping logic.

Classes:
    WagonManager: Main class for wagon requirement calculations and scheduling
    WagonBatch: Represents a single wagon batch delivery
    WagonPool: Tracks available wagons across time with looping from sunflower to palm
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
import math

from terminal_optimizer.domain_models import Operation, OperationType


from .constants import (
    WAGON_CAPACITY,
    WAGONS_PER_BATCH,
    MAX_BATCHES_PER_DAY_SUMMER,
    MAX_BATCHES_PER_DAY_WINTER,
    WAGON_PREP_TIME_HOURS,
    WAGON_REJECT_RATE,
)


@dataclass
class WagonBatch:
    """
    Represents a single batch of railway wagons.
    
    Attributes:
        batch_id: Unique batch identifier
        product: Product being transported
        wagons: Number of wagons in batch
        volume: Total volume (tonnes)
        arrival_time: When batch arrives at terminal
        completion_time: When batch discharge is complete
        origin: Source of wagons ("external", "pool", "sunflower_loop")
        notes: Additional information
    """
    batch_id: str
    product: str
    wagons: int
    volume: float
    arrival_time: datetime
    completion_time: Optional[datetime] = None
    origin: str = "external"
    notes: str = ""
    composition: Dict[str, int] = field(default_factory=dict)


@dataclass
class WagonAvailability:
    """
    Tracks available wagons at a specific time.
    
    Attributes:
        time: Point in time
        clean_wagons: Number of ready-to-use wagons
        dirty_wagons: Number of wagons needing prep
        source: String describing wagon source
    """
    time: datetime
    clean_wagons: int
    dirty_wagons: int = 0
    source: str = "initial"


class WagonManager:
    """
    Manages railway wagon calculations and scheduling.
    
    Key features:
    - Calculate wagon requirements for operations
    - Distribute wagons to daily batches
    - Track wagon looping from sunflower to palm
    - Identify gaps and external wagon needs
    """
    
    def __init__(
        self,
        total_wagon_fleet: Optional[int] = None,
        fleet_size: Optional[int] = None,
        season: str = "summer",
        wagon_capacity: Optional[float] = None,
        parameters: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize wagon manager.
        
        Args:
            total_wagon_fleet: Total wagons available (preferred parameter name)
            fleet_size: Alias for total_wagon_fleet (for backward compatibility)
            season: "summer" or "winter" (affects batch limits)
            wagon_capacity: Wagon capacity in tonnes (for compatibility, not used)
            parameters: Additional parameters
        """
        # Support both total_wagon_fleet and fleet_size parameters
        if total_wagon_fleet is not None:
            self.total_wagon_fleet = total_wagon_fleet
        elif fleet_size is not None:
            self.total_wagon_fleet = fleet_size
        else:
            self.total_wagon_fleet = 500  # Default
        
        self.season = season
        self.parameters = parameters or {}
        
        # Maximum batches per day based on season
        self.max_batches_per_day = (
            MAX_BATCHES_PER_DAY_SUMMER if season == "summer"
            else MAX_BATCHES_PER_DAY_WINTER
        )
        
        # Wagon pool tracking
        self.wagon_pool: Dict[datetime, WagonAvailability] = {}
        self.external_orders: List[Tuple[datetime, int, str]] = []
    
    @property
    def fleet_size(self) -> int:
        """Alias for total_wagon_fleet for backward compatibility."""
        return self.total_wagon_fleet
    
    def calculate_requirement(self, operation: Operation) -> int:
        """
        Calculate wagon requirement for a single operation.
        
        Args:
            operation: Operation needing wagons
            
        Returns:
            Number of wagons needed
        """
        if operation.volume <= 0:
            return 0
        
        wagons = math.ceil(operation.volume / WAGON_CAPACITY)
        
        # Check fill rate (minimum 53% efficiency)
        actual_fill = operation.volume / (wagons * WAGON_CAPACITY)
        if actual_fill < 0.53 and wagons > 1:
            # Consider reducing wagons but accept lower fill
            pass
        
        return wagons
    
    def distribute_to_days(
        self,
        operations: List[Operation]
    ) -> Dict[date, List[Tuple[Operation, int]]]:
        """
        Distribute operations and their wagon requirements to days.
        
        Args:
            operations: List of operations needing wagons
            
        Returns:
            Dict mapping date to list of (operation, wagons_needed) tuples
        """
        daily_requirements: Dict[date, List[Tuple[Operation, int]]] = defaultdict(list)
        
        for op in operations:
            # Only consider operations involving rail
            if "rail" not in op.source.lower() and "rail" not in op.target.lower():
                continue
            
            if op.start_time is None:
                continue
            
            wagons = self.calculate_requirement(op)
            if wagons > 0:
                day = op.start_time.date()
                daily_requirements[day].append((op, wagons))
        
        return daily_requirements
    
    def distribute_to_batches(
        self,
        daily_requirements: Dict[date, List[Tuple[Operation, int]]]
    ) -> Tuple[List[WagonBatch], List[str]]:
        """
        Distribute daily wagon requirements into batches.
        
        Args:
            daily_requirements: Dict of date to (operation, wagons) list
            
        Returns:
            Tuple of (batch_list, warnings)
        """
        batches = []
        warnings = []
        batch_counter = 0
        
        for day, ops_wagons in sorted(daily_requirements.items()):
            total_wagons = sum(w for _, w in ops_wagons)
            
            # Check product types
            products = set(op.product for op, _ in ops_wagons if op.product)
            
            # Determine max wagons per day based on product
            max_wagons_per_day = WAGONS_PER_BATCH * self.max_batches_per_day
            if "sunflower" in products:
                max_wagons_per_day = 72  # 4 batches * 18 wagons
            elif any("palm" in p for p in products):
                max_wagons_per_day = 54  # 3 batches * 18 wagons
            
            if total_wagons > max_wagons_per_day:
                warnings.append(
                    f"Day {day}: {total_wagons} wagons needed exceeds "
                    f"daily limit of {max_wagons_per_day}. Operations may need rescheduling."
                )
            
            # Create batches by filling them operation by operation
            current_batch_wagons = 0
            current_batch_composition: Dict[str, int] = {}
            batch_num = 0
            
            # Helper to finalize and append a batch
            def finalize_batch(wagons: int, composition: Dict[str, int]) -> None:
                nonlocal batch_counter, batch_num
                if wagons == 0:
                    return
                
                batch_counter += 1
                batch_volume = wagons * WAGON_CAPACITY
                
                # Determine primary product (one with most wagons)
                primary_product = max(composition.items(), key=lambda x: x[1])[0] if composition else "unknown"
                
                # Create notes listing composition
                comp_str = ", ".join(f"{k}: {v}" for k, v in composition.items())
                
                # Create batch - ensure hour stays within 0-23
                batch_hour = min(8 + batch_num * 6, 23)
                batch_time = datetime.combine(day, datetime.min.time().replace(hour=batch_hour))
                
                batch = WagonBatch(
                    batch_id=f"BATCH_{batch_counter:04d}",
                    product=primary_product,
                    wagons=wagons,
                    volume=batch_volume,
                    arrival_time=batch_time,
                    notes=f"Batch {batch_num + 1} of day {day} ({comp_str})",
                    composition=composition
                )
                batches.append(batch)
                batch_num += 1

            # Iterate through operations and fill batches
            for op, wagons_needed in ops_wagons:
                while wagons_needed > 0:
                    if batch_num >= self.max_batches_per_day:
                        # Exceeded daily limit, stop scheduling for this day
                        # (Warning already added above)
                        break
                    
                    space = WAGONS_PER_BATCH - current_batch_wagons
                    
                    if space == 0:
                        # Current batch full, finalize it
                        finalize_batch(current_batch_wagons, current_batch_composition)
                        current_batch_wagons = 0
                        current_batch_composition = {}
                        space = WAGONS_PER_BATCH
                    
                    take = min(wagons_needed, space)
                    current_batch_wagons += take
                    wagons_needed -= take
                    
                    # Update composition
                    key = str(op.product) if op.product else "unknown"
                    current_batch_composition[key] = current_batch_composition.get(key, 0) + take
            
            # Finalize last partial batch
            if current_batch_wagons > 0 and batch_num < self.max_batches_per_day:
                finalize_batch(current_batch_wagons, current_batch_composition)
        
        return batches, warnings
    
    def track_wagon_transformation(
        self,
        operations: List[Operation]
    ) -> Dict[datetime, WagonAvailability]:
        """
        Track wagon availability through sunflower discharge operations.
        
        When sunflower is discharged from wagons, those wagons become available
        for palm loading after preparation time and accounting for rejects.
        
        Args:
            operations: All operations in sequence
            
        Returns:
            Dict mapping time to wagon availability
        """
        availability_timeline: Dict[datetime, WagonAvailability] = {}
        
        for op in operations:
            # Look for sunflower discharge operations
            if op.product == "sunflower" and op.op_type == OperationType.RAIL_BATCH:
                if op.wagons and op.end_time:
                    dirty_wagons = op.wagons
                    
                    # After preparation time, wagons are ready
                    prep_hours = self.parameters.get("wagon_prep_time", WAGON_PREP_TIME_HOURS)
                    ready_time = op.end_time + timedelta(hours=prep_hours)
                    
                    # Account for rejection rate
                    clean_wagons = int(dirty_wagons * (1 - WAGON_REJECT_RATE))
                    rejected = dirty_wagons - clean_wagons
                    
                    if ready_time not in availability_timeline:
                        availability_timeline[ready_time] = WagonAvailability(
                            time=ready_time,
                            clean_wagons=clean_wagons,
                            dirty_wagons=rejected,
                            source=f"sunflower_loop_{op.op_id}"
                        )
                    else:
                        availability_timeline[ready_time].clean_wagons += clean_wagons
                        availability_timeline[ready_time].dirty_wagons += rejected
        
        return availability_timeline
    
    def check_wagon_availability(
        self,
        operation: Operation,
        wagon_pool: Dict[datetime, WagonAvailability]
    ) -> Tuple[bool, int]:
        """
        Check if sufficient wagons are available for an operation.
        
        Args:
            operation: Palm loading operation needing wagons
            wagon_pool: Wagon availability timeline
            
        Returns:
            Tuple of (sufficient, gap)
            - sufficient: True if enough wagons available
            - gap: Shortfall if insufficient
        """
        if not operation.start_time or not operation.wagons:
            return True, 0
        
        # Count available wagons before operation start
        available = 0
        for time, avail in wagon_pool.items():
            if time <= operation.start_time:
                available += avail.clean_wagons
        
        needed = operation.wagons
        
        if available >= needed:
            return True, 0
        else:
            gap = needed - available
            return False, gap
    
    def calculate_external_order(
        self,
        gaps: Dict[datetime, int],
        lead_time_days: int = 3
    ) -> List[Tuple[datetime, int, float]]:
        """
        Calculate external wagon orders needed to fill gaps.
        
        Args:
            gaps: Dict mapping operation time to wagon shortfall
            lead_time_days: Days needed to receive external wagons
            
        Returns:
            List of (order_date, wagons, cost) tuples
        """
        external_orders = []
        wagon_external_cost = self.parameters.get("wagon_external_cost", 50000.0)
        
        for need_date, gap in gaps.items():
            if gap <= 0:
                continue
            
            # Order must be placed lead_time days before
            order_date = need_date - timedelta(days=lead_time_days)
            
            # Cost calculation
            cost = gap * wagon_external_cost
            
            external_orders.append((order_date, gap, cost))
        
        return external_orders
    
    def generate_wagon_report(
        self,
        operations: List[Operation]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive wagon analysis report.
        
        Args:
            operations: All operations in sequence
            
        Returns:
            Dict containing:
            - daily_requirements: Wagon needs by day
            - batches: Planned wagon batches
            - looping_availability: Wagons from sunflower loop
            - gaps: Shortfalls requiring external wagons
            - external_orders: Required external orders
            - warnings: Any issues found
        """
        # Step 1: Calculate daily requirements
        daily_reqs = self.distribute_to_days(operations)
        
        # Step 2: Distribute to batches
        batches, batch_warnings = self.distribute_to_batches(daily_reqs)
        
        # Step 3: Track wagon looping
        wagon_pool = self.track_wagon_transformation(operations)
        
        # Step 4: Identify gaps
        gaps: Dict[datetime, int] = {}
        gap_warnings = []
        
        for op in operations:
            # Check palm loading operations
            if (op.product and "palm" in op.product and
                op.op_type in [OperationType.TRANSFER, OperationType.RAIL_BATCH] and
                "rail" in op.target.lower()):
                
                sufficient, gap = self.check_wagon_availability(op, wagon_pool)
                if not sufficient and op.start_time is not None:
                    gaps[op.start_time] = gap
                    gap_warnings.append(
                        f"Operation {op.op_id} ({op.start_time}): "
                        f"Wagon shortfall of {gap} units"
                    )
        
        # Step 5: Calculate external orders
        external_orders = self.calculate_external_order(gaps)
        
        # Compile warnings
        all_warnings = batch_warnings + gap_warnings
        
        return {
            "daily_requirements": dict(daily_reqs),
            "batches": batches,
            "looping_availability": wagon_pool,
            "gaps": gaps,
            "external_orders": external_orders,
            "warnings": all_warnings,
            "total_external_cost": sum(cost for _, _, cost in external_orders)
        }
    
    def optimize_batch_timing(
        self,
        batches: List[WagonBatch],
        operations: List[Operation]
    ) -> List[WagonBatch]:
        """
        Optimize batch arrival times to match operation needs.
        
        Args:
            batches: Initial batch schedule
            operations: Operations requiring wagons
            
        Returns:
            Optimized batch list
        """
        # This is a placeholder for more sophisticated optimization
        # For now, just ensure batches arrive before operations need them
        
        optimized = []
        for batch in batches:
            # Find operations on batch day
            day = batch.arrival_time.date()
            day_ops = [op for op in operations if op.start_time and op.start_time.date() == day]
            
            if day_ops:
                # Set batch arrival to earliest operation start minus buffer
                # Filter above ensures all operations have non-None start_time
                earliest_op = min(day_ops, key=lambda x: x.start_time)  # type: ignore[arg-type, type-var]
                buffer_hours = 2.0  # Arrive 2 hours before first operation
                
                # Since day_ops filter ensures start_time is not None, this is safe
                assert earliest_op.start_time is not None
                optimal_time = earliest_op.start_time - timedelta(hours=buffer_hours)
                
                # Keep batch on same day
                if optimal_time.date() == day:
                    batch.arrival_time = optimal_time
            
            optimized.append(batch)
        
        return optimized


class WagonForecaster:
    """
    Forecasts future wagon availability based on current status and operations.
    
    Attributes:
        wagon_manager: Reference to WagonManager instance
    """
    
    def __init__(self, wagon_manager: WagonManager):
        """Initialize forecaster with wagon manager."""
        self.wagon_manager = wagon_manager
    
    def forecast(self, days_ahead: int = 30) -> Dict[str, Any]:
        """
        Forecast wagon availability for specified days ahead.
        
        Args:
            days_ahead: Number of days to forecast
            
        Returns:
            Dictionary with forecast data including:
            - days_ahead: Forecast horizon
            - daily_availability: List of daily wagon availability
            - total_wagons: Total wagons in fleet
        """
        forecast_data = {
            "days_ahead": days_ahead,
            "daily_availability": [],
            "total_wagons": self.wagon_manager.total_wagon_fleet,
        }
        
        # Simple forecast: assume stable wagon availability
        # In a real implementation, this would model looping dynamics
        base_date = datetime.now()
        
        for day in range(days_ahead):
            forecast_date = base_date + timedelta(days=day)
            forecast_data["daily_availability"].append({
                "date": forecast_date.date().isoformat(),
                "wagons_available": self.wagon_manager.total_wagon_fleet,
                "wagons_in_use": 0,
                "wagons_returning": 0,
            })
        
        return forecast_data
