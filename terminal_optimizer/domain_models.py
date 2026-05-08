"""
Domain Models for Terminal Optimizer

This module contains the core domain classes representing the physical
and operational entities of the oil terminal.

Classes:
    Tank: Storage tank with capacity, allowed products, and state management
    Vessel: Ship with cargo plan, ETA, and demurrage information
    Operation: A single operation in the terminal schedule
    Scenario: Container for all input data for a planning scenario
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from enum import Enum
import math

from .constants import (
    DEFAULT_COMPATIBILITY_MATRIX,
    RATE_SHIP_DISCHARGE_LINE1,
    RATE_SHIP_DISCHARGE_LINE2_TANK,
    RATE_SHIP_DISCHARGE_LINE2_DIRECT,
    RATE_SHIP_LOAD_MIN,
    RATE_SHIP_LOAD_MAX,
    RATE_RAIL_DISCHARGE_SUMMER,
    RATE_RAIL_DISCHARGE_WINTER,
    WAGON_CAPACITY,
    WAGONS_PER_BATCH,
    MAX_BATCHES_PER_DAY_SUMMER,
    DEFAULT_PARAMETERS,
    CLEANING_LOW3MCPD_TO_STANDARD,
    CLEANING_STANDARD_TO_LOW3MCPD,
    CLEANING_PALM_TO_SUNFLOWER,
    CLEANING_DIFFERENT_PALM_FRACTIONS,
    CLEANING_DEFAULT,
)


class TankState(Enum):
    """Possible states of a storage tank."""
    IDLE = "idle"
    FILLING = "filling"
    DISCHARGING = "discharging"
    ANALYSIS = "analysis"
    CLEANING = "cleaning"
    AVAILABLE = "available"


class CargoType(Enum):
    """Types of cargo handled by the terminal."""
    SUNFLOWER = "sunflower"
    PALM = "palm"


class OperationType(Enum):
    """Types of operations in the terminal."""
    BERTHING = "berthing"
    UNBERTHING = "unberthing"
    DISCHARGE = "discharge"
    LOAD = "load"
    TRANSFER = "transfer"
    CLEANING = "cleaning"
    ANALYSIS = "analysis"
    RAIL_BATCH = "rail_batch"


class Priority(Enum):
    """Priority levels for clients and operations."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"




@dataclass
class Tank:
    """
    Represents a storage tank at the terminal.
    
    Attributes:
        tank_id: Unique identifier (e.g., "RVS_1", "RVS_5", "SHT")
        capacity: Maximum capacity in tonnes
        allowed_products: List of product types that can be stored
        is_swing: Whether this is a swing tank (can switch between product types)
        deadstock_ratio: Dict mapping product type to deadstock ratio (0.0-1.0)
        current_volume: Current volume of product in tonnes
        current_product: Currently stored product type (None if empty)
        state: Current operational state of the tank
        state_entry_time: When the current state was entered
        temperature: Current temperature (relevant for palm products)
    """
    tank_id: str
    capacity: float
    allowed_products: List[str]
    is_swing: bool = False
    deadstock_ratio: Dict[str, float] = field(default_factory=dict)
    current_volume: float = 0.0
    current_product: Optional[str] = None
    state: TankState = TankState.IDLE
    state_entry_time: Optional[datetime] = None
    temperature: Optional[float] = None
    
    # Reference to compatibility matrix (can be overridden)
    _compatibility_matrix: Dict[Tuple[str, str], int] = field(
        default_factory=lambda: DEFAULT_COMPATIBILITY_MATRIX.copy(),
        repr=False
    )
    
    def __post_init__(self):
        """Validate tank configuration after initialization."""
        if self.capacity <= 0:
            raise ValueError(f"Tank capacity must be positive, got {self.capacity}")
        if self.current_volume < 0:
            raise ValueError(f"Current volume cannot be negative, got {self.current_volume}")
        if self.current_volume > self.capacity:
            raise ValueError(
                f"Current volume ({self.current_volume}) exceeds capacity ({self.capacity})"
            )
        # Set default deadstock ratios if not provided
        for product in self.allowed_products:
            if product not in self.deadstock_ratio:
                if product == "sunflower":
                    self.deadstock_ratio[product] = 0.10
                elif product.startswith("palm"):
                    self.deadstock_ratio[product] = 0.15 if "low3mcpd" in product else 0.10
                else:
                    self.deadstock_ratio[product] = 0.10
    
    def get_effective_capacity(self, product: str) -> float:
        """
        Calculate effective capacity accounting for deadstock.
        
        Args:
            product: Product type to calculate capacity for
            
        Returns:
            Effective capacity in tonnes (capacity * (1 - deadstock_ratio))
            
        Raises:
            ValueError: If product is not allowed in this tank
        """
        if not self.can_store_product(product):
            raise ValueError(f"Product '{product}' not allowed in tank {self.tank_id}")
        
        ratio = self.deadstock_ratio.get(product, 0.10)
        return self.capacity * (1 - ratio)
    
    def can_store_product(self, product: str) -> bool:
        """
        Check if a product type is allowed in this tank.
        
        Args:
            product: Product type to check
            
        Returns:
            True if product can be stored
        """
        # Normalize product
        product_lower = product.lower()
        
        # Check direct match
        if product in self.allowed_products or product_lower in self.allowed_products:
            return True
        
        # Check wildcard (e.g., "palm_*" matches all palm products)
        for allowed in self.allowed_products:
            if allowed.endswith("*"):
                prefix = allowed[:-1]
                if product_lower.startswith(prefix):
                    return True
        
        return False
    
    def can_accept(self, product: str, volume: float) -> Tuple[bool, str]:
        """
        Check if tank can accept a given volume of product.
        
        Args:
            product: Product type to add
            volume: Volume in tonnes to add
            
        Returns:
            Tuple of (can_accept: bool, reason: str)
        """
        # Check product compatibility
        if not self.can_store_product(product):
            return False, f"Product '{product}' not allowed in tank {self.tank_id}"
        
        # Check if tank is in a state that allows filling
        if self.state not in [TankState.IDLE, TankState.AVAILABLE, TankState.FILLING]:
            return False, f"Tank {self.tank_id} is in state {self.state.value}, cannot accept product"
        
        # Check product segregation (if tank has different product)
        if self.current_product is not None and self.current_volume > 0:
            if self.current_product != product:
                return False, f"Tank {self.tank_id} contains {self.current_product}, cannot mix with {product}"
        
        # Check capacity
        effective_capacity = self.get_effective_capacity(product)
        available_space = effective_capacity - self.current_volume
        
        if volume > available_space:
            return False, f"Insufficient space: need {volume}t, only {available_space:.1f}t available"
        
        return True, "OK"
    
    def get_available_space(self, product: Optional[str] = None) -> float:
        """
        Get available space in the tank.
        
        Args:
            product: Product type (uses current_product if None)
            
        Returns:
            Available space in tonnes
        """
        if product is None:
            product = self.current_product
        
        if product is None:
            # If no product specified and tank is empty, use minimum deadstock
            return self.capacity * 0.90  # Assume 10% deadstock
        
        effective_capacity = self.get_effective_capacity(product)
        return max(0, effective_capacity - self.current_volume)
    
    def requires_cleaning(self, new_product: str) -> bool:
        """
        Check if cleaning is required before storing a new product.
        
        Args:
            new_product: Product type to be stored
            
        Returns:
            True if cleaning is required
        """
        # No cleaning needed if tank is empty
        if self.current_product is None or self.current_volume == 0:
            return False
        
        # Same product doesn't need cleaning
        if self.current_product == new_product:
            return False
        
        # Check compatibility matrix
        cleaning_hours = self.get_cleaning_duration(self.current_product, new_product)
        return cleaning_hours > 0
    
    def get_cleaning_duration(self, from_product: str, to_product: str) -> float:
        """
        Get required cleaning duration for product transition.
        
        Args:
            from_product: Current product type
            to_product: New product type
            
        Returns:
            Cleaning duration in hours
        """
        key = (from_product, to_product)
        if key in self._compatibility_matrix:
            return float(self._compatibility_matrix[key])
        
        # Default cleaning times based on product families
        if from_product == to_product:
            return 0.0
        
        # Normalize for logic checks
        from_lower = from_product.lower()
        to_lower = to_product.lower()
        
        from_is_palm = from_lower.startswith("palm") or "palm" in from_lower
        to_is_palm = to_lower.startswith("palm") or "palm" in to_lower
        from_is_low3mcpd = "low3mcpd" in from_lower
        to_is_low3mcpd = "low3mcpd" in to_lower
        
        # Low3MCPD transitions require longest cleaning
        if from_is_low3mcpd and not to_is_low3mcpd:
            return CLEANING_LOW3MCPD_TO_STANDARD
        if not from_is_low3mcpd and to_is_low3mcpd:
            return CLEANING_STANDARD_TO_LOW3MCPD

        # Palm to sunflower or vice versa
        if from_is_palm != to_is_palm:
            return CLEANING_PALM_TO_SUNFLOWER

        # Different palm fractions
        if from_is_palm and to_is_palm:
            return CLEANING_DIFFERENT_PALM_FRACTIONS

        # Default
        return CLEANING_DEFAULT
    
    def fill(self, product: str, volume: float) -> None:
        """
        Add product to the tank.
        
        Args:
            product: Product type to add
            volume: Volume in tonnes to add
            
        Raises:
            ValueError: If tank cannot accept the product/volume
        """
        can_accept, reason = self.can_accept(product, volume)
        if not can_accept:
            raise ValueError(reason)
        
        self.current_volume += volume
        if self.current_product is None:
            self.current_product = product
        # For simple synchronous fill operations, keep tank in previous state
        # Only scheduled operations with explicit state management should use FILLING
        # If tank was IDLE or AVAILABLE, keep it that way (ready for next operation)
        if self.state == TankState.IDLE:
            pass  # Keep IDLE
        elif self.state == TankState.AVAILABLE:
            pass  # Keep AVAILABLE
    
    def discharge(self, volume: float) -> float:
        """
        Remove product from the tank.
        
        Args:
            volume: Volume in tonnes to remove
            
        Returns:
            Actual volume discharged (may be less if tank doesn't have enough)
            
        Raises:
            ValueError: If tank is in wrong state
        """
        if self.state not in [TankState.IDLE, TankState.AVAILABLE, TankState.DISCHARGING]:
            raise ValueError(f"Tank {self.tank_id} is in state {self.state.value}, cannot discharge")
        
        actual_volume = min(volume, self.current_volume)
        self.current_volume -= actual_volume
        
        if self.current_volume <= 0:
            self.current_volume = 0
            self.current_product = None
            self.state = TankState.IDLE
        else:
            self.state = TankState.DISCHARGING
        
        return actual_volume
    
    def start_cleaning(self, entry_time: datetime) -> None:
        """Start cleaning operation on the tank."""
        if self.current_volume > 0:
            raise ValueError(f"Cannot start cleaning: tank {self.tank_id} is not empty")
        self.state = TankState.CLEANING
        self.state_entry_time = entry_time
        self.current_product = None
    
    def finish_cleaning(self) -> None:
        """Complete cleaning operation."""
        if self.state != TankState.CLEANING:
            raise ValueError(f"Tank {self.tank_id} is not in cleaning state")
        self.state = TankState.IDLE
        self.state_entry_time = None
    
    def start_analysis(self, entry_time: datetime) -> None:
        """Start analysis period for the tank contents."""
        self.state = TankState.ANALYSIS
        self.state_entry_time = entry_time
    
    def finish_analysis(self) -> None:
        """Complete analysis period."""
        if self.state != TankState.ANALYSIS:
            raise ValueError(f"Tank {self.tank_id} is not in analysis state")
        self.state = TankState.AVAILABLE
        self.state_entry_time = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tank to dictionary representation."""
        return {
            "tank_id": self.tank_id,
            "capacity": self.capacity,
            "allowed_products": self.allowed_products,
            "is_swing": self.is_swing,
            "deadstock_ratio": self.deadstock_ratio,
            "current_volume": self.current_volume,
            "current_product": self.current_product,
            "state": self.state.value,
            "state_entry_time": self.state_entry_time.isoformat() if self.state_entry_time else None,
            "temperature": self.temperature,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Tank":
        """Create tank from dictionary representation."""
        state_value = data.get("state", "idle")
        state = TankState(state_value) if isinstance(state_value, str) else state_value
        
        entry_time = data.get("state_entry_time")
        if isinstance(entry_time, str):
            entry_time = datetime.fromisoformat(entry_time)
        
        return cls(
            tank_id=data["tank_id"],
            capacity=data["capacity"],
            allowed_products=data["allowed_products"],
            is_swing=data.get("is_swing", False),
            deadstock_ratio=data.get("deadstock_ratio", {}),
            current_volume=data.get("current_volume", 0.0),
            current_product=data.get("current_product"),
            state=state,
            state_entry_time=entry_time,
            temperature=data.get("temperature"),
        )


@dataclass
class Vessel:
    """
    Represents a ship arriving at the terminal.
    
    Attributes:
        vessel_id: Unique identifier for the vessel
        eta: Expected time of arrival
        cargo_type: Type of cargo (sunflower for export, palm for import)
        total_volume: Total cargo volume in tonnes
        cargo_plan: For palm vessels, mapping of hold_id to (fraction, volume)
        demurrage_rate: Cost per hour of delay in RUB
        strategic_weight: Priority multiplier (1.0 = normal, 2.0 = high priority)
        notes: Additional information about the vessel
        actual_arrival: Actual arrival time (if arrived)
        actual_departure: Actual departure time (if departed)
    """
    vessel_id: str
    eta: datetime
    cargo_type: CargoType
    total_volume: float
    cargo_plan: Dict[str, Tuple[str, float]] = field(default_factory=dict)
    demurrage_rate: float = 100000.0  # RUB per hour
    strategic_weight: float = 1.0
    notes: str = ""
    is_active: bool = True
    actual_arrival: Optional[datetime] = None
    actual_departure: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate vessel configuration."""
        if self.total_volume <= 0:
            raise ValueError(f"Total volume must be positive, got {self.total_volume}")
        if self.demurrage_rate < 0:
            raise ValueError(f"Demurrage rate cannot be negative, got {self.demurrage_rate}")
        if self.strategic_weight <= 0:
            raise ValueError(f"Strategic weight must be positive, got {self.strategic_weight}")
        
        # Convert string cargo_type to enum
        if isinstance(self.cargo_type, str):
            self.cargo_type = CargoType(self.cargo_type.lower())
    
    def get_fractions(self) -> List[Tuple[str, str, float]]:
        """
        Get list of fractions from cargo plan.
        
        Returns:
            List of (hold_id, fraction_name, volume) tuples
        """
        if not self.cargo_plan:
            return []
        
        result = []
        for hold_id, (fraction, volume) in self.cargo_plan.items():
            result.append((hold_id, fraction, volume))
        
        # Sort by hold_id
        result.sort(key=lambda x: x[0])
        return result
    
    def get_fraction_count(self) -> int:
        """Get number of distinct fractions in cargo plan."""
        if not self.cargo_plan:
            return 0
        
        fractions = set(fraction for fraction, _ in self.cargo_plan.values())
        return len(fractions)
    
    def get_total_by_fraction(self) -> Dict[str, float]:
        """
        Get total volume grouped by fraction type.
        
        Returns:
            Dict mapping fraction name to total volume
        """
        totals: Dict[str, float] = {}
        for fraction, volume in self.cargo_plan.values():
            totals[fraction] = totals.get(fraction, 0) + volume
        return totals
    
    def validate_cargo_plan(self) -> Tuple[bool, str]:
        """
        Validate that cargo plan volumes sum to total volume.
        
        Returns:
            Tuple of (is_valid, message)
        """
        if not self.cargo_plan:
            if self.cargo_type == CargoType.PALM:
                return False, "Palm vessel must have a cargo plan"
            return True, "OK"
        
        plan_total = sum(volume for _, volume in self.cargo_plan.values())
        tolerance = self.total_volume * 0.01  # 1% tolerance
        
        if abs(plan_total - self.total_volume) > tolerance:
            return False, (
                f"Cargo plan total ({plan_total:.1f}t) doesn't match "
                f"vessel total ({self.total_volume:.1f}t)"
            )
        
        return True, "OK"
    
    def calculate_demurrage(self, hours_delayed: float) -> float:
        """
        Calculate demurrage cost for delay.
        
        Args:
            hours_delayed: Number of hours vessel was delayed
            
        Returns:
            Total demurrage cost in RUB
        """
        if hours_delayed <= 0:
            return 0.0
        
        return self.demurrage_rate * self.strategic_weight * hours_delayed
    
    def get_expected_duration(self, discharge_rate: float = 900.0) -> float:
        """
        Get expected operation duration in hours.
        
        Args:
            discharge_rate: Rate in tonnes per hour
            
        Returns:
            Expected duration in hours
        """
        return self.total_volume / discharge_rate
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert vessel to dictionary representation."""
        return {
            "vessel_id": self.vessel_id,
            "eta": self.eta.isoformat(),
            "cargo_type": self.cargo_type.value,
            "total_volume": self.total_volume,
            "cargo_plan": {
                hold_id: {"fraction": frac, "volume": vol}
                for hold_id, (frac, vol) in self.cargo_plan.items()
            },
            "demurrage_rate": self.demurrage_rate,
            "strategic_weight": self.strategic_weight,
            "notes": self.notes,
            "is_active": self.is_active,
            "actual_arrival": self.actual_arrival.isoformat() if self.actual_arrival else None,
            "actual_departure": self.actual_departure.isoformat() if self.actual_departure else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Vessel":
        """Create vessel from dictionary representation."""
        eta = data["eta"]
        if isinstance(eta, str):
            eta = datetime.fromisoformat(eta)
        
        cargo_plan = {}
        if "cargo_plan" in data and data["cargo_plan"]:
            for hold_id, info in data["cargo_plan"].items():
                if isinstance(info, dict):
                    cargo_plan[hold_id] = (info["fraction"], info["volume"])
                else:
                    cargo_plan[hold_id] = info
        
        actual_arrival = data.get("actual_arrival")
        if isinstance(actual_arrival, str):
            actual_arrival = datetime.fromisoformat(actual_arrival)
        
        actual_departure = data.get("actual_departure")
        if isinstance(actual_departure, str):
            actual_departure = datetime.fromisoformat(actual_departure)
        
        return cls(
            vessel_id=data["vessel_id"],
            eta=eta,
            cargo_type=data["cargo_type"],
            total_volume=data["total_volume"],
            cargo_plan=cargo_plan,
            demurrage_rate=data.get("demurrage_rate", 100000.0),
            strategic_weight=data.get("strategic_weight", 1.0),
            notes=data.get("notes", ""),
            is_active=data.get("is_active", True),
            actual_arrival=actual_arrival,
            actual_departure=actual_departure,
        )


@dataclass
class Operation:
    """
    Represents a single operation in the terminal schedule.
    
    Attributes:
        op_id: Unique operation identifier
        vessel_id: Associated vessel (if any)
        op_type: Type of operation
        product: Product being handled (if applicable)
        source: Source of product (e.g., "Ship", "Rail", "RVS_1")
        target: Destination of product (e.g., "RVS_3", "Ship", "Rail")
        volume: Volume in tonnes (if applicable)
        start_time: Scheduled start time
        duration: Duration in hours
        end_time: Scheduled end time (calculated from start + duration)
        line: Pipeline line used (Line1/Line2 for palm operations)
        wagons: Number of railway wagons (if rail operation)
        user_locked: Whether user has locked this operation from changes
        dependencies: List of operation IDs that must complete before this one
        notes: Additional information
    """
    op_id: str
    vessel_id: Optional[str] = None
    op_type: OperationType = OperationType.DISCHARGE
    product: Optional[str] = None
    source: str = ""
    target: str = ""
    volume: float = 0.0
    start_time: Optional[datetime] = None
    duration: float = 0.0  # hours
    end_time: Optional[datetime] = None
    line: Optional[str] = None
    wagons: Optional[int] = None
    user_locked: bool = False
    dependencies: List[str] = field(default_factory=list)
    notes: str = ""
    
    # Flow rate constants (tonnes per hour)
    RATE_SHIP_DISCHARGE_LINE1 = RATE_SHIP_DISCHARGE_LINE1
    RATE_SHIP_DISCHARGE_LINE2_TANK = RATE_SHIP_DISCHARGE_LINE2_TANK
    RATE_SHIP_DISCHARGE_LINE2_DIRECT = RATE_SHIP_DISCHARGE_LINE2_DIRECT
    RATE_SHIP_LOAD_MIN = RATE_SHIP_LOAD_MIN
    RATE_SHIP_LOAD_MAX = RATE_SHIP_LOAD_MAX
    RATE_RAIL_DISCHARGE_SUMMER = RATE_RAIL_DISCHARGE_SUMMER
    RATE_RAIL_DISCHARGE_WINTER = RATE_RAIL_DISCHARGE_WINTER

    # Wagon constants
    WAGON_CAPACITY = WAGON_CAPACITY
    WAGONS_PER_BATCH = WAGONS_PER_BATCH
    MAX_BATCHES_PER_DAY = MAX_BATCHES_PER_DAY_SUMMER
    
    def __post_init__(self):
        """Calculate derived fields."""
        # Calculate end_time if not provided
        if self.start_time is not None and self.duration >= 0 and self.end_time is None:
            self.end_time = self.start_time + timedelta(hours=self.duration)
        
        # Calculate wagons if not provided and this is a rail operation
        if self.wagons is None and self.volume > 0:
            if "rail" in self.source.lower() or "rail" in self.target.lower():
                self.wagons = self.calculate_wagons()
    
    def calculate_duration(
        self,
        rate: float = None,  # type: ignore
        season: str = "summer"
    ) -> float:
        """
        Calculate operation duration based on type and volume.

        Args:
            rate: Override flow rate (tonnes/hour)
            season: "summer" or "winter" for rail operations

        Returns:
            Duration in hours
        """
        if rate is not None:
            if rate <= 0:
                raise ValueError(f"Rate must be positive, got {rate}")
            return self.volume / rate

        # Initialize rate with default
        rate = 500.0  # Default rate

        if self.op_type == OperationType.DISCHARGE:
            if self.line == "Line1":
                rate = self.RATE_SHIP_DISCHARGE_LINE1
            elif self.line == "Line2":
                if "direct" in self.notes.lower() or "rail" in self.target.lower():
                    rate = self.RATE_SHIP_DISCHARGE_LINE2_DIRECT
                else:
                    rate = self.RATE_SHIP_DISCHARGE_LINE2_TANK
            else:
                rate = self.RATE_SHIP_DISCHARGE_LINE1  # Default

        elif self.op_type == OperationType.LOAD:
            rate = (self.RATE_SHIP_LOAD_MIN + self.RATE_SHIP_LOAD_MAX) / 2

        elif self.op_type == OperationType.RAIL_BATCH:
            rate = (
                self.RATE_RAIL_DISCHARGE_SUMMER
                if season == "summer"
                else self.RATE_RAIL_DISCHARGE_WINTER
            )

        elif self.op_type == OperationType.TRANSFER:
            rate = 500.0  # Default transfer rate

        elif self.op_type == OperationType.CLEANING:
            # Duration should be set directly for cleaning operations
            return self.duration

        elif self.op_type == OperationType.ANALYSIS:
            return 72.0  # Standard analysis time

        elif self.op_type == OperationType.BERTHING:
            return 24.0  # Minimum berthing time

        elif self.op_type == OperationType.UNBERTHING:
            return 4.0  # Typical unberthing time

        # else: rate remains 500.0 (default)

        if self.volume <= 0 or rate <= 0:
            return 0.0

        return self.volume / rate
    
    def calculate_wagons(self) -> int:
        """
        Calculate number of wagons needed for this operation.
        
        Returns:
            Number of wagons (rounded up)
        """
        if self.volume <= 0:
            return 0
        return math.ceil(self.volume / self.WAGON_CAPACITY)
    
    def overlaps_with(self, other: "Operation") -> bool:
        """
        Check if this operation overlaps with another in time.
        
        Args:
            other: Another operation to check against
            
        Returns:
            True if operations overlap in time
        """
        if self.start_time is None or self.end_time is None:
            return False
        if other.start_time is None or other.end_time is None:
            return False
        
        # Operations overlap if neither ends before the other starts
        return not (self.end_time <= other.start_time or other.end_time <= self.start_time)
    
    def can_start_at(
        self,
        time: datetime,
        completed_ops: Dict[str, datetime]
    ) -> Tuple[bool, str]:
        """
        Check if operation can start at given time considering dependencies.
        
        Args:
            time: Proposed start time
            completed_ops: Dict mapping op_id to completion time
            
        Returns:
            Tuple of (can_start, reason)
        """
        for dep_id in self.dependencies:
            if dep_id not in completed_ops:
                return False, f"Dependency {dep_id} not completed"
            
            if completed_ops[dep_id] > time:
                return False, f"Dependency {dep_id} completes at {completed_ops[dep_id]}, after proposed start {time}"
        
        return True, "OK"
    
    def update_timing(self, start_time: datetime, duration: Optional[float] = None) -> None:
        """
        Update operation timing.
        
        Args:
            start_time: New start time
            duration: New duration (uses existing if not provided)
        """
        self.start_time = start_time
        if duration is not None:
            self.duration = duration
        self.end_time = start_time + timedelta(hours=self.duration)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert operation to dictionary representation."""
        return {
            "op_id": self.op_id,
            "vessel_id": self.vessel_id,
            "op_type": self.op_type.value,
            "product": self.product,
            "source": self.source,
            "target": self.target,
            "volume": self.volume,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "duration": self.duration,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "line": self.line,
            "wagons": self.wagons,
            "user_locked": self.user_locked,
            "dependencies": self.dependencies,
            "notes": self.notes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Operation":
        """Create operation from dictionary representation."""
        start_time = data.get("start_time")
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)
        
        end_time = data.get("end_time")
        if isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time)
        
        op_type = data.get("op_type", "discharge")
        if isinstance(op_type, str):
            op_type = OperationType(op_type)
        
        return cls(
            op_id=data["op_id"],
            vessel_id=data.get("vessel_id"),
            op_type=op_type,
            product=data.get("product"),
            source=data.get("source", ""),
            target=data.get("target", ""),
            volume=data.get("volume", 0.0),
            start_time=start_time,
            duration=data.get("duration", 0.0),
            end_time=end_time,
            line=data.get("line"),
            wagons=data.get("wagons"),
            user_locked=data.get("user_locked", False),
            dependencies=data.get("dependencies", []),
            notes=data.get("notes", ""),
        )


@dataclass
class Scenario:
    """
    Container for all input data for a planning scenario.
    
    Attributes:
        scenario_id: Unique identifier for this scenario
        vessels: List of vessels in the planning horizon
        tanks: Dictionary of tank configurations
        rail_schedule: List of incoming rail deliveries
        current_inventory: Current state of all tanks
        client_demand: Demand matrix by week and client
        parameters: Scenario parameters (rates, times, costs)
        horizon_days: Planning horizon in days
    """
    scenario_id: str
    vessels: List[Vessel] = field(default_factory=list)
    tanks: Dict[str, Tank] = field(default_factory=dict)
    rail_schedule: List[Dict[str, Any]] = field(default_factory=list)
    current_inventory: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    client_demand: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    horizon_days: int = 30
    
    # Default parameters
    DEFAULT_PARAMETERS = DEFAULT_PARAMETERS
    
    def __post_init__(self):
        """Initialize default parameters."""
        for key, value in self.DEFAULT_PARAMETERS.items():
            if key not in self.parameters:
                self.parameters[key] = value
    
    def get_tanks(self) -> Dict[str, Tank]:
        """Get all tank objects."""
        return self.tanks
    
    def get_tank(self, tank_id: str) -> Optional[Tank]:
        """Get a specific tank by ID."""
        return self.tanks.get(tank_id)
    
    def get_vessels(self) -> List[Vessel]:
        """Get all vessels sorted by ETA."""
        return sorted(self.vessels, key=lambda v: v.eta)
    
    def get_vessel(self, vessel_id: str) -> Optional[Vessel]:
        """Get a specific vessel by ID."""
        for vessel in self.vessels:
            if vessel.vessel_id == vessel_id:
                return vessel
        return None
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate scenario data completeness and consistency.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check vessels
        if not self.vessels:
            errors.append("No vessels defined in scenario")
        
        for vessel in self.vessels:
            valid, msg = vessel.validate_cargo_plan()
            if not valid:
                errors.append(f"Vessel {vessel.vessel_id}: {msg}")
        
        # Check tanks
        if not self.tanks:
            errors.append("No tanks defined in scenario")
        
        # Check that required tanks exist
        required_tanks = ["RVS_1", "RVS_2", "RVS_3", "RVS_5", "SHT"]
        for tank_id in required_tanks:
            if tank_id not in self.tanks:
                errors.append(f"Required tank {tank_id} not found")
        
        # Check current inventory matches tank configuration
        for tank_id, inv in self.current_inventory.items():
            if tank_id not in self.tanks:
                errors.append(f"Inventory for unknown tank {tank_id}")
            else:
                tank = self.tanks[tank_id]
                if inv.get("current_volume", 0) > tank.capacity:
                    errors.append(
                        f"Tank {tank_id} inventory ({inv.get('current_volume')}) "
                        f"exceeds capacity ({tank.capacity})"
                    )
        
        # Check parameters
        if self.parameters.get("season") not in ["summer", "winter"]:
            errors.append(f"Invalid season: {self.parameters.get('season')}")
        
        return len(errors) == 0, errors
    
    def load_from_excel(self, filepath: str) -> None:
        """
        Load scenario data from Excel file.
        
        Args:
            filepath: Path to Excel file
            
        Note:
            This is a placeholder - actual implementation in excel_io.py
        """
        raise NotImplementedError("Use ExcelReader.load_all() instead")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert scenario to dictionary representation."""
        return {
            "scenario_id": self.scenario_id,
            "vessels": [v.to_dict() for v in self.vessels],
            "tanks": {k: v.to_dict() for k, v in self.tanks.items()},
            "rail_schedule": self.rail_schedule,
            "current_inventory": self.current_inventory,
            "client_demand": self.client_demand,
            "parameters": self.parameters,
            "horizon_days": self.horizon_days,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Scenario":
        """Create scenario from dictionary representation."""
        vessels = [Vessel.from_dict(v) for v in data.get("vessels", [])]
        tanks = {k: Tank.from_dict(v) for k, v in data.get("tanks", {}).items()}
        
        return cls(
            scenario_id=data["scenario_id"],
            vessels=vessels,
            tanks=tanks,
            rail_schedule=data.get("rail_schedule", []),
            current_inventory=data.get("current_inventory", {}),
            client_demand=data.get("client_demand", {}),
            parameters=data.get("parameters", {}),
            horizon_days=data.get("horizon_days", 30),
        )


# Factory functions for creating standard tank configurations

def create_standard_tanks() -> Dict[str, Tank]:
    """
    Create standard tank configuration for the terminal.
    
    Returns:
        Dictionary of tank_id to Tank objects
    """
    tanks = {
        "RVS_1": Tank(
            tank_id="RVS_1",
            capacity=9900.0,
            allowed_products=["sunflower"],
            is_swing=False,
            deadstock_ratio={"sunflower": 0.10},
        ),
        "RVS_2": Tank(
            tank_id="RVS_2",
            capacity=9900.0,
            allowed_products=["sunflower"],
            is_swing=False,
            deadstock_ratio={"sunflower": 0.10},
        ),
        "RVS_3": Tank(
            tank_id="RVS_3",
            capacity=9900.0,
            allowed_products=["palm_*"],
            is_swing=False,
            deadstock_ratio={
                "palm_oil": 0.15,
                "palm_olein": 0.15,
                "palm_stearin": 0.15,
                "palm_pfad": 0.15,
                "palm_oil_low3mcpd": 0.20,
                "palm_olein_low3mcpd": 0.20,
            },
        ),
        "RVS_5": Tank(
            tank_id="RVS_5",
            capacity=2700.0,
            allowed_products=["sunflower", "palm_*"],
            is_swing=True,
            deadstock_ratio={
                "sunflower": 0.10,
                "palm_oil": 0.10,
                "palm_olein": 0.10,
                "palm_stearin": 0.10,
                "palm_pfad": 0.10,
                "palm_oil_low3mcpd": 0.15,
                "palm_olein_low3mcpd": 0.15,
            },
        ),
        "SHT": Tank(
            tank_id="SHT",
            capacity=2700.0,
            allowed_products=["palm_*"],
            is_swing=False,
            deadstock_ratio={
                "palm_oil": 0.10,
                "palm_olein": 0.10,
                "palm_stearin": 0.10,
                "palm_pfad": 0.10,
                "palm_oil_low3mcpd": 0.10,
                "palm_olein_low3mcpd": 0.10,
            },
        ),
    }
    return tanks
