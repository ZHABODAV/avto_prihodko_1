"""
Validation Engine for Terminal Optimizer

This module provides constraint validation functions for checking physical,
operational, and business rule violations in terminal operations.

Functions:
    Physical Constraints:
        - validate_capacity_constraints: Check tank capacity limits
        - validate_flow_rates: Check operation flow rates
    
    Operational Constraints:
        - validate_rail_batches: Check rail batch limits per day
        - validate_resource_exclusivity: Check for resource conflicts
        - validate_product_compatibility: Check product transitions
    
    Business Rules:
        - validate_strategic_priorities: Check strategic client priorities
        - validate_client_commitments: Check client demand fulfillment
"""

from __future__ import annotations
from typing import List, Dict, Tuple, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd

from terminal_optimizer.domain_models import (
    Tank, Vessel, Operation, OperationType, TankState,
    DEFAULT_COMPATIBILITY_MATRIX
)
from terminal_optimizer.constants import (
    MAX_RATE_SHIP_DISCHARGE_LINE1,
    MAX_RATE_SHIP_DISCHARGE_LINE2_TANK,
    MAX_RATE_SHIP_DISCHARGE_LINE2_DIRECT,
    MAX_RATE_SHIP_LOAD_MIN,
    MAX_RATE_SHIP_LOAD_MAX,
    MAX_RATE_RAIL_DISCHARGE_SUMMER,
    MAX_RATE_RAIL_DISCHARGE_WINTER,
    MAX_RATE_TANK_PUMP,
    MAX_RAIL_BATCHES_PER_DAY,
    BERTH_PALM,
    BERTH_SUNFLOWER,
)


@dataclass
class Violation:
    """Represents a constraint violation."""
    severity: str  # "ERROR", "WARNING", "INFO"
    category: str  # "PHYSICAL", "OPERATIONAL", "BUSINESS"
    message: str
    details: Dict[str, Any]
    timestamp: Optional[datetime] = None
    
    def __str__(self) -> str:
        return f"[{self.severity}] {self.category}: {self.message}"


@dataclass
class ValidationResult:
    """Result of validation with errors and warnings."""
    errors: List[str]
    warnings: List[str]
    violations: List[Violation]
    
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0 or any(v.severity == "ERROR" for v in self.violations)
    
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0 or any(v.severity == "WARNING" for v in self.violations)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export."""
        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "violation_count": len(self.violations),
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }


class ValidationEngine:
    """
    Engine for validating operational sequences and scenarios.
    
    Attributes:
        scenario: Scenario to validate
        operations: List of operations
        balances: Balance dataframe (optional)
    """
    
    def __init__(
        self,
        scenario: Any,
        operations: List[Operation],
        balances: Optional[pd.DataFrame] = None
    ):
        """Initialize validation engine."""
        self.scenario = scenario
        self.operations = operations
        self.balances = balances
        self.tanks = scenario.tanks if hasattr(scenario, 'tanks') else {}
    
    def validate_all(self) -> ValidationResult:
        """
        Run all validation checks.
        
        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []
        violations_dict = validate_all_constraints(
            operations=self.operations,
            balance_dataframe=self.balances,
            tanks=self.tanks,
        )
        
        all_violations = []
        for category, viols in violations_dict.items():
            all_violations.extend(viols)
            for v in viols:
                if v.severity == "ERROR":
                    errors.append(f"{v.category}: {v.message}")
                elif v.severity == "WARNING":
                    warnings.append(f"{v.category}: {v.message}")
        
        return ValidationResult(
            errors=errors,
            warnings=warnings,
            violations=all_violations
        )


# =============================================================================
# SECTION 7.1: Physical Constraints
# =============================================================================

def validate_capacity_constraints(
    balance_dataframe: pd.DataFrame,
    tanks: Dict[str, Tank]
) -> List[Violation]:
    """
    Validate that tank levels stay within capacity bounds.
    
    Args:
        balance_dataframe: DataFrame with columns for each tank showing levels over time
        tanks: Dictionary of tank configurations
        
    Returns:
        List of capacity violations
        
    Example:
        >>> violations = validate_capacity_constraints(balance_df, tanks)
        >>> for v in violations:
        ...     print(v)
    """
    violations = []
    
    # Check each tank column in the dataframe
    for tank_id in tanks.keys():
        if tank_id not in balance_dataframe.columns:
            continue
        
        tank = tanks[tank_id]
        levels = balance_dataframe[tank_id]
        
        # Check for overfill (level > capacity)
        overfill_mask = levels > tank.capacity
        if overfill_mask.any():
            overfill_times = balance_dataframe.index[overfill_mask].tolist()
            max_overfill = levels[overfill_mask].max()
            
            violations.append(Violation(
                severity="ERROR",
                category="PHYSICAL",
                message=f"Tank {tank_id} overfilled",
                details={
                    "tank_id": tank_id,
                    "capacity": tank.capacity,
                    "max_level": max_overfill,
                    "overfill_amount": max_overfill - tank.capacity,
                    "occurrences": len(overfill_times),
                    "first_occurrence": overfill_times[0] if overfill_times else None,
                }
            ))
        
        # Check for negative stock (level < 0)
        negative_mask = levels < 0
        if negative_mask.any():
            negative_times = balance_dataframe.index[negative_mask].tolist()
            min_level = levels[negative_mask].min()
            
            violations.append(Violation(
                severity="ERROR",
                category="PHYSICAL",
                message=f"Tank {tank_id} has negative stock",
                details={
                    "tank_id": tank_id,
                    "min_level": min_level,
                    "deficit": abs(min_level),
                    "occurrences": len(negative_times),
                    "first_occurrence": negative_times[0] if negative_times else None,
                }
            ))
    
    return violations


def validate_flow_rates(
    operations: List[Operation],
    tanks: Dict[str, Tank]
) -> List[Violation]:
    """
    Validate that operation flow rates don't exceed equipment limits.
    
    Args:
        operations: List of operations to validate
        tanks: Dictionary of tank configurations
        
    Returns:
        List of flow rate violations
    """
    violations = []
    
    # Define maximum flow rates for different equipment
    MAX_RATES = {
        "ship_discharge_line1": MAX_RATE_SHIP_DISCHARGE_LINE1,
        "ship_discharge_line2_tank": MAX_RATE_SHIP_DISCHARGE_LINE2_TANK,
        "ship_discharge_line2_direct": MAX_RATE_SHIP_DISCHARGE_LINE2_DIRECT,
        "ship_load_min": MAX_RATE_SHIP_LOAD_MIN,
        "ship_load_max": MAX_RATE_SHIP_LOAD_MAX,
        "rail_discharge_summer": MAX_RATE_RAIL_DISCHARGE_SUMMER,
        "rail_discharge_winter": MAX_RATE_RAIL_DISCHARGE_WINTER,
        "tank_pump": MAX_RATE_TANK_PUMP,
    }
    
    for op in operations:
        if op.volume <= 0 or op.duration <= 0:
            continue
        
        flow_rate = op.volume / op.duration
        max_rate = None
        rate_type = None
        
        # Determine applicable rate limit
        if op.op_type == OperationType.DISCHARGE:
            if op.line == "Line1":
                max_rate = MAX_RATES["ship_discharge_line1"]
                rate_type = "ship_discharge_line1"
            elif op.line == "Line2":
                if "direct" in op.notes.lower():
                    max_rate = MAX_RATES["ship_discharge_line2_direct"]
                    rate_type = "ship_discharge_line2_direct"
                else:
                    max_rate = MAX_RATES["ship_discharge_line2_tank"]
                    rate_type = "ship_discharge_line2_tank"
        
        elif op.op_type == OperationType.LOAD:
            max_rate = MAX_RATES["ship_load_max"]
            rate_type = "ship_load_max"
        
        elif op.op_type == OperationType.RAIL_BATCH:
            max_rate = MAX_RATES["rail_discharge_summer"]
            rate_type = "rail_discharge"
        
        elif op.op_type == OperationType.TRANSFER:
            max_rate = MAX_RATES["tank_pump"]
            rate_type = "tank_pump"
        
        # Check if flow rate exceeds limit
        if max_rate is not None and flow_rate > max_rate * 1.01:  # 1% tolerance
            violations.append(Violation(
                severity="ERROR",
                category="PHYSICAL",
                message=f"Operation {op.op_id} exceeds flow rate limit",
                details={
                    "op_id": op.op_id,
                    "op_type": op.op_type.value,
                    "flow_rate": flow_rate,
                    "max_rate": max_rate,
                    "rate_type": rate_type,
                    "excess": flow_rate - max_rate,
                    "volume": op.volume,
                    "duration": op.duration,
                }
            ))
    
    return violations


# =============================================================================
# SECTION 7.2: Operational Constraints
# =============================================================================

def validate_rail_batches(operations: List[Operation]) -> List[Violation]:
    """
    Validate that rail batches don't exceed 4 per day limit.
    
    Args:
        operations: List of operations to validate
        
    Returns:
        List of rail batch violations
    """
    violations = []
    
    # Group rail operations by day
    rail_ops = [op for op in operations if op.op_type == OperationType.RAIL_BATCH]
    
    if not rail_ops:
        return violations
    
    # Group by date
    batches_by_day: Dict[str, List[Operation]] = {}
    for op in rail_ops:
        if op.start_time is None:
            continue
        
        day_key = op.start_time.date().isoformat()
        if day_key not in batches_by_day:
            batches_by_day[day_key] = []
        batches_by_day[day_key].append(op)
    
    # Check each day
    for day_key, day_ops in batches_by_day.items():
        batch_count = len(day_ops)
        
        if batch_count > MAX_RAIL_BATCHES_PER_DAY:
            violations.append(Violation(
                severity="ERROR",
                category="OPERATIONAL",
                message=f"Too many rail batches on {day_key}",
                details={
                    "date": day_key,
                    "batch_count": batch_count,
                    "max_batches": MAX_RAIL_BATCHES_PER_DAY,
                    "excess": batch_count - MAX_RAIL_BATCHES_PER_DAY,
                    "operation_ids": [op.op_id for op in day_ops],
                }
            ))
    
    return violations


def validate_resource_exclusivity(operations: List[Operation]) -> List[Violation]:
    """
    Validate that resources (tanks, berths, rail) are not used concurrently.
    
    Args:
        operations: List of operations to validate
        
    Returns:
        List of resource conflict violations
    """
    violations = []
    
    # Get all operations with valid timing
    timed_ops = [op for op in operations if op.start_time and op.end_time]
    
    # Check each pair of operations
    for i, op1 in enumerate(timed_ops):
        for op2 in timed_ops[i+1:]:
            # Check if operations overlap in time
            if not op1.overlaps_with(op2):
                continue
            
            # Check for resource conflicts
            conflicts = []
            
            # Check tank conflicts
            tanks1 = set()
            tanks2 = set()
            
            if op1.source and op1.source.startswith("RVS"):
                tanks1.add(op1.source)
            if op1.target and op1.target.startswith("RVS"):
                tanks1.add(op1.target)
            if op2.source and op2.source.startswith("RVS"):
                tanks2.add(op2.source)
            if op2.target and op2.target.startswith("RVS"):
                tanks2.add(op2.target)
            
            shared_tanks = tanks1 & tanks2
            if shared_tanks:
                conflicts.append(("tank", shared_tanks))
            
            # Check berth conflicts
            # Determine berth for op1
            berth1 = None
            if op1.target in [BERTH_PALM, BERTH_SUNFLOWER]:
                berth1 = op1.target
            elif op1.source in [BERTH_PALM, BERTH_SUNFLOWER]:
                berth1 = op1.source
            elif "berth" in op1.notes.lower():
                # Fallback inference
                if "palm" in op1.notes.lower() or (op1.product and "palm" in op1.product.lower()):
                    berth1 = BERTH_PALM
                elif "sunflower" in op1.notes.lower() or (op1.product and "sunflower" in op1.product.lower()):
                    berth1 = BERTH_SUNFLOWER
                else:
                    berth1 = "BERTH_GENERIC"

            # Determine berth for op2
            berth2 = None
            if op2.target in [BERTH_PALM, BERTH_SUNFLOWER]:
                berth2 = op2.target
            elif op2.source in [BERTH_PALM, BERTH_SUNFLOWER]:
                berth2 = op2.source
            elif "berth" in op2.notes.lower():
                # Fallback inference
                if "palm" in op2.notes.lower() or (op2.product and "palm" in op2.product.lower()):
                    berth2 = BERTH_PALM
                elif "sunflower" in op2.notes.lower() or (op2.product and "sunflower" in op2.product.lower()):
                    berth2 = BERTH_SUNFLOWER
                else:
                    berth2 = "BERTH_GENERIC"
            
            if berth1 and berth2 and berth1 == berth2:
                conflicts.append(("berth", {berth1}))
            
            # Check rail conflicts
            if op1.op_type == OperationType.RAIL_BATCH and op2.op_type == OperationType.RAIL_BATCH:
                # Rail batches can overlap if they don't exceed capacity
                pass
            
            # Report conflicts
            for resource_type, resources in conflicts:
                violations.append(Violation(
                    severity="ERROR",
                    category="OPERATIONAL",
                    message=f"Resource conflict: {resource_type}",
                    details={
                        "resource_type": resource_type,
                        "resources": list(resources),
                        "op1_id": op1.op_id,
                        "op1_start": op1.start_time.isoformat() if op1.start_time else None,
                        "op1_end": op1.end_time.isoformat() if op1.end_time else None,
                        "op2_id": op2.op_id,
                        "op2_start": op2.start_time.isoformat() if op2.start_time else None,
                        "op2_end": op2.end_time.isoformat() if op2.end_time else None,
                    }
                ))
    
    return violations


def validate_product_compatibility(
    operations: List[Operation],
    tanks: Dict[str, Tank],
    compatibility_matrix: Optional[Dict[Tuple[str, str], int]] = None
) -> List[Violation]:
    """
    Validate that product changes in tanks follow compatibility rules.
    
    Args:
        operations: List of operations to validate
        tanks: Dictionary of tank configurations
        compatibility_matrix: Product compatibility matrix (uses default if None)
        
    Returns:
        List of product compatibility violations
    """
    violations = []
    
    if compatibility_matrix is None:
        compatibility_matrix = DEFAULT_COMPATIBILITY_MATRIX
    
    # Sort operations by time
    sorted_ops = sorted(
        [op for op in operations if op.start_time],
        key=lambda x: x.start_time or datetime.min
    )
    
    # Track product in each tank over time
    tank_products: Dict[str, Optional[str]] = {
        tank_id: tank.current_product
        for tank_id, tank in tanks.items()
    }
    
    # Track product BEFORE cleaning
    tank_prev_product: Dict[str, Optional[str]] = {}
    
    # Track cleaning completion times
    tank_cleaned_at: Dict[str, Optional[datetime]] = {}
    
    for op in sorted_ops:
        target_tank = op.target if op.target and op.target in tanks else None
        
        # Handle cleaning operations
        if op.op_type == OperationType.CLEANING and target_tank:
            tank_prev_product[target_tank] = tank_products.get(target_tank)
            tank_cleaned_at[target_tank] = op.end_time
            tank_products[target_tank] = None
            continue
        
        if not target_tank or not op.product:
            continue
        
        new_product = op.product
        current_product = tank_products.get(target_tank)
        
        # Check for product change
        if current_product and current_product != new_product:
            # Check if cleaning required
            key = (current_product, new_product)
            cleaning_hours = compatibility_matrix.get(key, 48)
            
            if cleaning_hours > 0:
                # Check if cleaning was performed
                last_cleaning = tank_cleaned_at.get(target_tank)
                
                # op.start_time is guaranteed to be non-None because sorted_ops filters None values
                op_start_time = op.start_time
                if op_start_time and (last_cleaning is None or last_cleaning > op_start_time):
                    violations.append(Violation(
                        severity="ERROR",
                        category="OPERATIONAL",
                        message=f"Product change without cleaning in {target_tank}",
                        details={
                            "tank_id": target_tank,
                            "from_product": current_product,
                            "to_product": new_product,
                            "required_cleaning_hours": cleaning_hours,
                            "op_id": op.op_id,
                            "op_start": op_start_time.isoformat(),
                            "last_cleaning": last_cleaning.isoformat() if last_cleaning else None,
                        }
                    ))
        elif current_product is None and target_tank in tank_prev_product:
            # Tank was cleaned, check if new product needs cleaning from previous
            prev_product = tank_prev_product[target_tank]
            if prev_product and prev_product != new_product:
                key = (prev_product, new_product)
                cleaning_hours = compatibility_matrix.get(key, 48)
                
                if cleaning_hours > 0:
                    last_cleaning = tank_cleaned_at.get(target_tank)
                    # op.start_time is guaranteed to be non-None because sorted_ops filters None values
                    op_start_time = op.start_time
                    if op_start_time and (last_cleaning is None or last_cleaning > op_start_time):
                            violations.append(Violation(
                            severity="ERROR",
                            category="OPERATIONAL",
                            message=f"Product change without cleaning in {target_tank}",
                            details={
                                "tank_id": target_tank,
                                "from_product": prev_product,
                                "to_product": new_product,
                                "required_cleaning_hours": cleaning_hours,
                                "op_id": op.op_id,
                                "op_start": op_start_time.isoformat(),
                                "last_cleaning": last_cleaning.isoformat() if last_cleaning else None,
                            }
                        ))
                    else:
                        # Cleaning was completed before op, so it's OK
                        tank_prev_product.pop(target_tank, None)
        
        # Update tank product
        if op.op_type in [OperationType.DISCHARGE, OperationType.TRANSFER]:
            tank_products[target_tank] = new_product
    
    return violations


def validate_line_cleaning(operations: List[Operation]) -> List[Violation]:
    """
    Validate that lines are cleaned between incompatible products.
    
    Args:
        operations: List of operations to validate
        
    Returns:
        List of line cleaning violations
    """
    violations = []
    
    # Sort operations by time
    sorted_ops = sorted(
        [op for op in operations if op.start_time],
        key=lambda x: x.start_time or datetime.min
    )
    
    # Track product on each line
    line_products: Dict[str, Optional[str]] = {
        "Line1": None,
        "Line2": None
    }
    
    # Track cleaning completion times
    line_cleaned_at: Dict[str, Optional[datetime]] = {
        "Line1": None,
        "Line2": None
    }
    
    for op in sorted_ops:
        # Handle line cleaning
        if op.op_type == OperationType.CLEANING and op.target in ["Line1", "Line2"]:
            line_cleaned_at[op.target] = op.end_time
            line_products[op.target] = None
            continue
            
        # Handle discharge operations (which use lines)
        if op.op_type == OperationType.DISCHARGE and op.line in ["Line1", "Line2"]:
            line = op.line
            new_product = op.product
            current_product = line_products.get(line)
            
            if current_product and current_product != new_product:
                # Check if cleaning was performed
                last_cleaning = line_cleaned_at.get(line)
                
                # op.start_time is guaranteed to be non-None
                op_start_time = op.start_time
                if op_start_time and (last_cleaning is None or last_cleaning > op_start_time):
                    violations.append(Violation(
                        severity="ERROR",
                        category="OPERATIONAL",
                        message=f"Product change without cleaning on {line}",
                        details={
                            "line": line,
                            "from_product": current_product,
                            "to_product": new_product,
                            "op_id": op.op_id,
                            "op_start": op_start_time.isoformat(),
                            "last_cleaning": last_cleaning.isoformat() if last_cleaning else None,
                        }
                    ))
            
            # Update line product
            line_products[line] = new_product
            
    return violations


# =============================================================================
# SECTION 7.3: Business Rules
# =============================================================================

def validate_strategic_priorities(
    wagon_allocation: Dict[str, Any],
    client_priorities: Dict[str, str]
) -> List[Violation]:
    """
    Validate that strategic clients are served with priority.
    
    Args:
        wagon_allocation: Dictionary mapping client_id to allocated wagon data
        client_priorities: Dictionary mapping client_id to priority level
        
    Returns:
        List of priority violations
    """
    violations = []
    
    # Get strategic (HIGH priority) and regular clients
    strategic_clients = {
        client_id for client_id, priority in client_priorities.items()
        if priority == "HIGH"
    }
    
    regular_clients = {
        client_id for client_id, priority in client_priorities.items()
        if priority != "HIGH"
    }
    
    # Check allocation timing
    for client_id, allocation in wagon_allocation.items():
        if client_id not in strategic_clients:
            continue
        
        if not isinstance(allocation, dict) or "delivery_date" not in allocation:
            continue
        
        strategic_date = allocation["delivery_date"]
        
        # Check if any regular client got delivery before strategic
        for regular_id in regular_clients:
            if regular_id not in wagon_allocation:
                continue
            
            regular_allocation = wagon_allocation[regular_id]
            if not isinstance(regular_allocation, dict) or "delivery_date" not in regular_allocation:
                continue
            
            regular_date = regular_allocation["delivery_date"]
            
            if regular_date < strategic_date:
                violations.append(Violation(
                    severity="WARNING",
                    category="BUSINESS",
                    message=f"Strategic client {client_id} served after regular client",
                    details={
                        "strategic_client": client_id,
                        "strategic_date": strategic_date,
                        "regular_client": regular_id,
                        "regular_date": regular_date,
                    }
                ))
    
    return violations


def validate_client_commitments(
    wagon_allocation: Dict[str, Any],
    client_demand: Dict[str, float]
) -> List[Violation]:
    """
    Validate that client demand is met by allocated volumes.
    
    Args:
        wagon_allocation: Dictionary mapping client_id to allocation data
        client_demand: Dictionary mapping client_id to demanded volume
        
    Returns:
        List of shortage violations
    """
    violations = []
    
    for client_id, demand in client_demand.items():
        # Get allocated volume
        allocated = 0.0
        
        if client_id in wagon_allocation:
            allocation = wagon_allocation[client_id]
            if isinstance(allocation, dict) and "volume" in allocation:
                allocated = allocation["volume"]
            elif isinstance(allocation, (int, float)):
                allocated = float(allocation)
        
        # Check if demand is met (with 1% tolerance)
        if allocated < demand * 0.99:
            shortage = demand - allocated
            shortage_pct = (shortage / demand) * 100
            
            violations.append(Violation(
                severity="ERROR" if shortage_pct > 10 else "WARNING",
                category="BUSINESS",
                message=f"Client {client_id} has unmet demand",
                details={
                    "client_id": client_id,
                    "demand": demand,
                    "allocated": allocated,
                    "shortage": shortage,
                    "shortage_percentage": shortage_pct,
                }
            ))
    
    return violations


# =============================================================================
# Consolidated Validation Function
# =============================================================================

def validate_all_constraints(
    operations: List[Operation],
    balance_dataframe: Optional[pd.DataFrame],
    tanks: Dict[str, Tank],
    wagon_allocation: Optional[Dict[str, Any]] = None,
    client_demand: Optional[Dict[str, float]] = None,
    client_priorities: Optional[Dict[str, str]] = None,
) -> Dict[str, List[Violation]]:
    """
    Run all validation checks and return categorized violations.
    
    Args:
        operations: List of operations to validate
        balance_dataframe: Tank balance over time
        tanks: Tank configurations
        wagon_allocation: Optional wagon allocation data
        client_demand: Optional client demand data
        client_priorities: Optional client priority data
        
    Returns:
        Dictionary mapping category to list of violations
    """
    all_violations = {
        "PHYSICAL": [],
        "OPERATIONAL": [],
        "BUSINESS": [],
    }
    
    # Physical constraints
    if balance_dataframe is not None:
        all_violations["PHYSICAL"].extend(
            validate_capacity_constraints(balance_dataframe, tanks)
        )
    
    all_violations["PHYSICAL"].extend(
        validate_flow_rates(operations, tanks)
    )
    
    # Operational constraints
    all_violations["OPERATIONAL"].extend(
        validate_rail_batches(operations)
    )
    
    all_violations["OPERATIONAL"].extend(
        validate_resource_exclusivity(operations)
    )
    
    all_violations["OPERATIONAL"].extend(
        validate_product_compatibility(operations, tanks)
    )
    
    all_violations["OPERATIONAL"].extend(
        validate_line_cleaning(operations)
    )
    
    # Business rules
    if wagon_allocation and client_priorities:
        all_violations["BUSINESS"].extend(
            validate_strategic_priorities(wagon_allocation, client_priorities)
        )
    
    if wagon_allocation and client_demand:
        all_violations["BUSINESS"].extend(
            validate_client_commitments(wagon_allocation, client_demand)
        )
    
    return all_violations


def print_violations(violations: Dict[str, List[Violation]]) -> None:
    """
    Print violations in a readable format.
    
    Args:
        violations: Dictionary of categorized violations
    """
    total_count = sum(len(v) for v in violations.values())
    
    if total_count == 0:
        print("✓ No violations found")
        return
    
    print(f"\n❌ Found {total_count} violation(s):\n")
    
    for category, viols in violations.items():
        if not viols:
            continue
        
        print(f"  [{category}] - {len(viols)} violation(s)")
        for v in viols:
            print(f"    {v}")
        print()
