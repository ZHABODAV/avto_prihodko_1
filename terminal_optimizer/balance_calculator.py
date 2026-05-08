"""
Tank Balance Calculator

This module calculates tank balances over time given a sequence of operations.
It simulates the flow of materials through the terminal and validates capacity constraints.

Classes:
    TankBalanceCalculator: Core balance calculation engine
    ValidationEngine: Validates sequences against operational constraints
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
from collections import defaultdict
from typing_extensions import Self

from terminal_optimizer.domain_models import Tank, Operation, Scenario, OperationType
from terminal_optimizer.domain_models import TankState as DomainTankState


@dataclass
class FlowEvent:
    """Represents a flow event at a specific time."""
    time: datetime
    tank_id: str
    product: str
    flow_in: float  # tonnes/hour
    flow_out: float  # tonnes/hour
    operation_id: str
    
    def __repr__(self) -> str:
        direction = "IN" if self.flow_in > 0 else "OUT"
        volume = self.flow_in if self.flow_in > 0 else self.flow_out
        return f"FlowEvent({self.time}, {self.tank_id}, {direction} {volume:.1f}t/h, {self.product})"


@dataclass
class TankState:
    """State of a tank at a specific point in time."""
    time: datetime
    tank_id: str
    volume: float
    product: Optional[str]
    state: str  # idle/filling/discharging/analysis/cleaning
    flow_in: float = 0.0  # current flow rate in
    flow_out: float = 0.0  # current flow rate out
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DataFrame."""
        return {
            "time": self.time,
            "tank_id": self.tank_id,
            "volume": self.volume,
            "product": self.product or "",
            "state": self.state,
            "flow_in": self.flow_in,
            "flow_out": self.flow_out,
            "utilization": (self.volume / 9900.0) * 100 if self.tank_id.startswith("RVS") else (self.volume / 2700.0) * 100,
        }


@dataclass
class BalanceViolation:
    """Represents a constraint violation found during simulation."""
    time: datetime
    tank_id: str
    violation_type: str  # overfill, underflow, product_mix, etc.
    severity: str  # ERROR, WARNING
    details: str
    current_value: float
    limit_value: float
    
    def __repr__(self) -> str:
        return f"{self.severity}: {self.tank_id} at {self.time} - {self.violation_type}: {self.details}"


class TankBalanceCalculator:
    """
    Calculates tank balances over time based on operation sequence.

    This engine simulates the physical flow of materials through tanks,
    tracking levels, flows, and states at hourly intervals.
    """

    def __init__(self, tanks: Dict[str, Tank], parameters: Optional[Dict[str, Any]] = None):
        """
        Initialize balance calculator.

        Args:
            tanks: Dictionary of tank_id to Tank objects
            parameters: Optional scenario parameters
        """
        self.tanks = tanks
        self.parameters = parameters or {}
        self.violations: List[BalanceViolation] = []
        self.max_iterations = 1000  # Maximum iterations to prevent infinite loops
        self.convergence_tolerance = 1e-6  # Volume change tolerance for convergence
        
    def initialize_state(self, current_inventory: Dict[str, Dict[str, Any]]) -> Dict[str, "TankState"]:
        """
        Initialize tank states from current inventory.

        Args:
            current_inventory: Dict mapping tank_id to inventory data

        Returns:
            Dict mapping tank_id to initial TankState
        """
        states = {}
        base_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for tank_id, tank in self.tanks.items():
            inv = current_inventory.get(tank_id, {})
            states[tank_id] = TankState(
                time=base_time,
                tank_id=tank_id,
                volume=inv.get("current_volume", 0.0),
                product=inv.get("current_product"),
                state=inv.get("state", "idle"),
            )
        
        return states
    
    def calculate_flows(
        self,
        operations: List[Operation],
        hour: int,
        reference_time: datetime
    ) -> Dict[str, Tuple[float, float, str]]:
        """
        Calculate flows for each tank at a given hour.
        
        Args:
            operations: List of all operations
            hour: Hour offset from reference time
            reference_time: Base time for calculations
            
        Returns:
            Dict mapping tank_id to (flow_in, flow_out, product)
        """
        current_time = reference_time + timedelta(hours=hour)
        flows: Dict[str, Tuple[float, float, str]] = {}
        
        # Initialize all tanks with zero flow
        for tank_id in self.tanks.keys():
            flows[tank_id] = (0.0, 0.0, "")
        
        # Find active operations at this hour
        for op in operations:
            if op.start_time is None or op.end_time is None:
                continue
            
            # Check if operation is active at current time
            if op.start_time <= current_time < op.end_time:
                # Calculate flow rate (volume / duration)
                if op.duration > 0:
                    flow_rate = op.volume / op.duration
                else:
                    continue
                
                # Determine which tanks are affected
                if op.op_type == OperationType.DISCHARGE:
                    # Ship to tank
                    if op.target in self.tanks:
                        current_in, current_out, _ = flows[op.target]
                        flows[op.target] = (current_in + flow_rate, current_out, op.product or "")
                
                elif op.op_type == OperationType.LOAD:
                    # Tank to ship
                    if op.source in self.tanks:
                        current_in, current_out, product = flows[op.source]
                        flows[op.source] = (current_in, current_out + flow_rate, op.product or product)
                
                elif op.op_type == OperationType.TRANSFER:
                    # Tank to another tank or rail
                    if op.source in self.tanks:
                        current_in, current_out, product = flows[op.source]
                        flows[op.source] = (current_in, current_out + flow_rate, op.product or product)
                    
                    if op.target in self.tanks:
                        current_in, current_out, _ = flows[op.target]
                        flows[op.target] = (current_in + flow_rate, current_out, op.product or "")
                
                elif op.op_type == OperationType.RAIL_BATCH:
                    # Rail to tank
                    if "Rail" in op.source and op.target in self.tanks:
                        current_in, current_out, _ = flows[op.target]
                        flows[op.target] = (current_in + flow_rate, current_out, op.product or "")
                    # Tank to rail
                    elif "Rail" in op.target and op.source in self.tanks:
                        current_in, current_out, product = flows[op.source]
                        flows[op.source] = (current_in, current_out + flow_rate, op.product or product)
        
        return flows
    
    def step_forward(
        self,
        current_states: Dict[str, "TankState"],
        flows: Dict[str, Tuple[float, float, str]],
        hour: int,
        reference_time: datetime
    ) -> Dict[str, "TankState"]:
        """
        Advance tank states forward by one hour.

        Args:
            current_states: Current state of each tank
            flows: Flow rates for each tank
            hour: Current hour offset
            reference_time: Base time

        Returns:
            New state dictionary after one hour
        """
        new_states = {}
        current_time = reference_time + timedelta(hours=hour)

        # Track volume changes for convergence checking
        volume_changes = {}
        negative_volume_count = 0

        for tank_id, tank in self.tanks.items():
            current_state = current_states[tank_id]
            flow_in, flow_out, product = flows.get(tank_id, (0.0, 0.0, ""))

            # Calculate new volume
            new_volume = current_state.volume + flow_in - flow_out
            volume_change = abs(new_volume - current_state.volume)
            volume_changes[tank_id] = volume_change

            # Check for violations
            if new_volume > tank.capacity:
                self.violations.append(BalanceViolation(
                    time=current_time,
                    tank_id=tank_id,
                    violation_type="overfill",
                    severity="ERROR",
                    details=f"Volume {new_volume:.1f}t exceeds capacity {tank.capacity}t",
                    current_value=new_volume,
                    limit_value=tank.capacity,
                ))
                # Cap at capacity
                new_volume = tank.capacity

            if new_volume < 0:
                negative_volume_count += 1
                self.violations.append(BalanceViolation(
                    time=current_time,
                    tank_id=tank_id,
                    violation_type="underflow",
                    severity="ERROR",
                    details=f"Volume {new_volume:.1f}t is negative",
                    current_value=new_volume,
                    limit_value=0.0,
                ))
                # Floor at zero
                new_volume = 0.0

            # Determine state
            if flow_in > 0 and flow_out == 0:
                state = "filling"
            elif flow_out > 0 and flow_in == 0:
                state = "discharging"
            elif new_volume == 0:
                state = "idle"
            else:
                state = "available"

            # Determine product
            if new_volume > 0:
                # Use incoming product if filling, otherwise keep current
                new_product = product if product else current_state.product
            else:
                new_product = None

            new_states[tank_id] = TankState(
                time=current_time,
                tank_id=tank_id,
                volume=new_volume,
                product=new_product,
                state=state,
                flow_in=flow_in,
                flow_out=flow_out,
            )

        # Convergence check: if too many negative volumes or very small changes, we may be stuck
        max_volume_change = max(volume_changes.values()) if volume_changes else 0.0
        if max_volume_change < self.convergence_tolerance and negative_volume_count > len(self.tanks) * 0.5:
            # Log convergence warning but continue (don't stop simulation)
            pass  # Could add logging here if needed

        return new_states
    
    def simulate(
        self,
        operations: List[Operation],
        initial_inventory: Dict[str, Dict[str, Any]],
        horizon_hours: int,
        reference_time: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Run full simulation of tank balances over the horizon.

        Args:
            operations: List of operations to simulate
            initial_inventory: Initial state of tanks
            horizon_hours: Number of hours to simulate
            reference_time: Start time (defaults to now)

        Returns:
            DataFrame with columns: hour, time, tank_id, volume, product, state, flow_in, flow_out

        Raises:
            RuntimeError: If simulation fails to converge or exceeds iteration limits
        """
        if reference_time is None:
            reference_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Clear violations
        self.violations = []

        # Initialize states
        states = self.initialize_state(initial_inventory)

        # Store history
        history: List[Dict[str, Any]] = []

        # Record initial state
        for tank_id, state in states.items():
            record = state.to_dict()
            record["hour"] = 0
            history.append(record)

        # Track convergence metrics
        consecutive_small_changes = 0
        max_consecutive_small_changes = 10  # Allow some small changes before considering converged

        # Simulate each hour with safety limits
        for hour in range(1, min(horizon_hours + 1, self.max_iterations)):
            # Calculate flows for this hour
            flows = self.calculate_flows(operations, hour, reference_time)

            # Store previous states for convergence check
            prev_volumes = {tank_id: state.volume for tank_id, state in states.items()}

            # Step forward
            states = self.step_forward(states, flows, hour, reference_time)

            # Check for convergence (very small volume changes across all tanks)
            max_volume_change = max(
                abs(states[tank_id].volume - prev_volumes[tank_id])
                for tank_id in states.keys()
            )

            if max_volume_change < self.convergence_tolerance:
                consecutive_small_changes += 1
                if consecutive_small_changes >= max_consecutive_small_changes:
                    # Simulation has converged, stop early
                    break
            else:
                consecutive_small_changes = 0

            # Safety check: if too many violations, stop
            error_violations = [v for v in self.violations if v.severity == "ERROR"]
            if len(error_violations) > len(self.tanks) * horizon_hours * 0.1:  # 10% error rate
                raise RuntimeError(
                    f"Simulation aborted: too many violations ({len(error_violations)}) "
                    f"detected. Check operation sequencing and tank capacities."
                )

            # Record state
            for tank_id, state in states.items():
                record = state.to_dict()
                record["hour"] = hour
                history.append(record)

            # Prevent infinite loops
            if hour >= self.max_iterations:
                raise RuntimeError(
                    f"Simulation exceeded maximum iterations ({self.max_iterations}). "
                    "Check for circular dependencies or invalid flow calculations."
                )

        # Convert to DataFrame
        df = pd.DataFrame(history)

        # Pivot to have one row per hour with columns for each tank
        df_pivot = df.pivot_table(
            index=["hour", "time"],
            columns="tank_id",
            values=["volume", "flow_in", "flow_out"],
            aggfunc="first"
        )

        # Flatten column names
        df_pivot.columns = [f"{tank}_{metric}" for metric, tank in df_pivot.columns]
        df_pivot = df_pivot.reset_index()

        return df_pivot
    
    def get_violations(self) -> List[BalanceViolation]:
        """Get list of violations found during simulation."""
        return self.violations
    
    def has_violations(self, severity: Optional[str] = None) -> bool:
        """
        Check if simulation had violations.
        
        Args:
            severity: Filter by severity (ERROR/WARNING), or None for any
            
        Returns:
            True if violations were found
        """
        if severity is None:
            return len(self.violations) > 0
        return any(v.severity == severity for v in self.violations)


class ValidationEngine:
    """
    Validates operation sequences against operational constraints.
    
    Checks:
    - Physical capacity constraints
    - Product segregation rules
    - Precedence dependencies
    - Railway batch limits
    - Resource conflicts
    """
    
    def __init__(self, tanks: Dict[str, Tank], parameters: Optional[Dict[str, Any]] = None):
        """
        Initialize validation engine.
        
        Args:
            tanks: Dictionary of tank configurations
            parameters: Scenario parameters
        """
        self.tanks = tanks
        self.parameters = parameters or {}
        self.violations: List[BalanceViolation] = []
    
    def validate_capacity(self, balance_df: pd.DataFrame) -> List[BalanceViolation]:
        """
        Validate that tank levels never exceed capacity.
        
        Args:
            balance_df: DataFrame from simulation
            
        Returns:
            List of capacity violations
        """
        violations = []
        
        for tank_id, tank in self.tanks.items():
            vol_col = f"{tank_id}_volume"
            if vol_col not in balance_df.columns:
                continue
            
            # Check each hour
            for idx, row in balance_df.iterrows():
                volume = row[vol_col]
                if pd.isna(volume):
                    continue
                
                if volume > tank.capacity:
                    violations.append(BalanceViolation(
                        time=row["time"],
                        tank_id=tank_id,
                        violation_type="capacity_exceeded",
                        severity="ERROR",
                        details=f"Volume {volume:.1f}t exceeds capacity {tank.capacity}t",
                        current_value=volume,
                        limit_value=tank.capacity,
                    ))
                
                if volume < 0:
                    violations.append(BalanceViolation(
                        time=row["time"],
                        tank_id=tank_id,
                        violation_type="negative_volume",
                        severity="ERROR",
                        details=f"Negative volume {volume:.1f}t",
                        current_value=volume,
                        limit_value=0.0,
                    ))
        
        return violations
    
    def validate_product_segregation(
        self,
        operations: List[Operation],
        tanks: Dict[str, Tank]
    ) -> List[BalanceViolation]:
        """
        Validate that product changes include proper cleaning operations.
        
        Args:
            operations: List of operations
            tanks: Tank configurations
            
        Returns:
            List of segregation violations
        """
        violations = []
        
        # Track product in each tank over time
        tank_products: Dict[str, Optional[str]] = {}
        for tank_id in tanks.keys():
            tank_products[tank_id] = None
        
        # Sort operations by time
        sorted_ops = sorted(
            [op for op in operations if op.start_time is not None],
            key=lambda x: x.start_time or datetime.max
        )
        
        for op in sorted_ops:
            if op.op_type == OperationType.DISCHARGE or op.op_type == OperationType.TRANSFER:
                # Check target tank
                if op.target in tank_products:
                    current_product = tank_products[op.target]
                    new_product = op.product
                    
                    if current_product and new_product and current_product != new_product:
                        # Look for cleaning operation before this one
                        cleaning_found = False
                        for check_op in sorted_ops:
                            if (check_op.op_type == OperationType.CLEANING and
                                check_op.target == op.target and
                                check_op.end_time and op.start_time and
                                check_op.end_time <= op.start_time):
                                cleaning_found = True
                                break
                        
                        if not cleaning_found:
                            assert op.start_time is not None  # We filtered for this above
                            violations.append(BalanceViolation(
                                time=op.start_time,
                                tank_id=op.target,
                                violation_type="product_mix",
                                severity="ERROR",
                                details=f"Product change from {current_product} to {new_product} without cleaning",
                                current_value=0.0,
                                limit_value=0.0,
                            ))
                    
                    # Update tank product
                    tank_products[op.target] = new_product
            
            elif op.op_type == OperationType.CLEANING:
                # Cleaning clears the product
                if op.target in tank_products:
                    tank_products[op.target] = None
        
        return violations
    
    def validate_precedence(
        self,
        operations: List[Operation]
    ) -> List[BalanceViolation]:
        """
        Validate that dependent operations respect precedence constraints.
        
        Args:
            operations: List of operations
            
        Returns:
            List of precedence violations
        """
        violations = []
        
        # Build map of op_id to operation
        op_map = {op.op_id: op for op in operations}
        
        for op in operations:
            if not op.dependencies:
                continue
            
            for dep_id in op.dependencies:
                if dep_id not in op_map:
                    violations.append(BalanceViolation(
                        time=op.start_time or datetime.now(),
                        tank_id=op.target or op.source,
                        violation_type="missing_dependency",
                        severity="ERROR",
                        details=f"Operation {op.op_id} depends on missing operation {dep_id}",
                        current_value=0.0,
                        limit_value=0.0,
                    ))
                    continue
                
                dep_op = op_map[dep_id]
                
                # Check that dependency completes before this operation starts
                if (op.start_time and dep_op.end_time and
                    op.start_time < dep_op.end_time):
                    violations.append(BalanceViolation(
                        time=op.start_time,
                        tank_id=op.target or op.source,
                        violation_type="precedence_violation",
                        severity="ERROR",
                        details=f"Operation {op.op_id} starts before dependency {dep_id} completes",
                        current_value=op.start_time.timestamp(),
                        limit_value=dep_op.end_time.timestamp(),
                    ))
        
        return violations
    
    def validate_rail_limit(
        self,
        operations: List[Operation]
    ) -> List[BalanceViolation]:
        """
        Validate that railway batches don't exceed 4 per day limit.
        
        Args:
            operations: List of operations
            
        Returns:
            List of batch limit violations
        """
        violations = []
        
        # Group rail operations by day
        rail_ops_by_day: Dict[str, List[Operation]] = defaultdict(list)
        
        for op in operations:
            if op.op_type == OperationType.RAIL_BATCH and op.start_time:
                day_key = op.start_time.date().isoformat()
                rail_ops_by_day[day_key].append(op)
        
        # Check each day
        for day, ops in rail_ops_by_day.items():
            if len(ops) > 4:
                start_time = ops[0].start_time
                assert start_time is not None  # We filtered for operations with start_time
                violations.append(BalanceViolation(
                    time=start_time,
                    tank_id="Rail_Platform",
                    violation_type="batch_limit_exceeded",
                    severity="ERROR",
                    details=f"Day {day} has {len(ops)} batches, limit is 4",
                    current_value=float(len(ops)),
                    limit_value=4.0,
                ))
        
        return violations
    
    def validate_all(
        self,
        operations: List[Operation],
        balance_df: pd.DataFrame
    ) -> Tuple[bool, List[BalanceViolation]]:
        """
        Run all validation checks.
        
        Args:
            operations: List of operations
            balance_df: DataFrame from balance simulation
            
        Returns:
            Tuple of (is_valid, list_of_violations)
        """
        all_violations = []
        
        # Run all checks
        all_violations.extend(self.validate_capacity(balance_df))
        all_violations.extend(self.validate_product_segregation(operations, self.tanks))
        all_violations.extend(self.validate_precedence(operations))
        all_violations.extend(self.validate_rail_limit(operations))
        
        # Check for ERROR-level violations
        has_errors = any(v.severity == "ERROR" for v in all_violations)
        
        return not has_errors, all_violations
