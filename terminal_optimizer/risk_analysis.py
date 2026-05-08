"""
Risk Analysis Module for Terminal Optimizer

This module provides risk analysis capabilities including:
- Wagon availability forecasting using Markov chains
- Risk identification for wagon shortages, tank overflows, and critical path operations
- Recommendation generation with ROI calculations

Classes:
    WagonForecaster: Markov chain forecaster for wagon availability
    Risk: Represents a potential risk event
    Recommendation: Mitigation recommendation with cost/benefit analysis
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from enum import Enum
from .logger import get_logger


class WagonState(Enum):
    """Possible states for wagons in the system."""
    AVAILABLE = "Available"
    IN_TRANSIT_TO_TERMINAL = "In Transit to Terminal"
    AT_TERMINAL = "At Terminal"
    IN_TRANSIT_TO_CLIENT = "In Transit to Client"
    AT_CLIENT = "At Client"
    IN_TRANSIT_RETURNING = "In Transit Returning"


class RiskType(Enum):
    """Types of risks identified in the system."""
    WAGON_SHORTAGE = "wagon_shortage"
    TANK_OVERFLOW = "tank_overflow"
    CRITICAL_PATH = "critical_path"
    DEMURRAGE = "demurrage"
    CAPACITY_CONSTRAINT = "capacity_constraint"


class RiskSeverity(Enum):
    """Severity levels for risks."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Risk:
    """
    Represents a potential risk event.
    
    Attributes:
        risk_id: Unique identifier for the risk
        risk_type: Type of risk
        severity: Severity level
        description: Human-readable description
        probability: Probability of occurrence (0.0-1.0)
        impact: Financial impact in RUB
        expected_value: probability × impact
        affected_operations: List of operation IDs affected
        time_window: When the risk might occur
        metadata: Additional risk-specific data
    """
    risk_id: str
    risk_type: RiskType
    severity: RiskSeverity
    description: str
    probability: float
    impact: float
    expected_value: float = 0.0
    affected_operations: List[str] = field(default_factory=list)
    time_window: Optional[Tuple[datetime, datetime]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate derived fields."""
        self.expected_value = self.probability * self.impact
        
        # Validate probability
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError(f"Probability must be between 0 and 1, got {self.probability}")


@dataclass
class Recommendation:
    """
    Mitigation recommendation with cost/benefit analysis.
    
    Attributes:
        rec_id: Unique identifier
        risk_id: Associated risk ID
        action: Recommended action
        cost: Cost to implement the mitigation (RUB)
        benefit: Expected benefit (risk avoided) (RUB)
        roi: Return on investment (benefit / cost)
        implementation_time: Time required to implement
        priority: Priority ranking
        notes: Additional notes
    """
    rec_id: str
    risk_id: str
    action: str
    cost: float
    benefit: float
    roi: float = 0.0
    implementation_time: Optional[float] = None  # hours
    priority: int = 0
    notes: str = ""
    
    def __post_init__(self):
        """Calculate ROI."""
        if self.cost > 0:
            self.roi = self.benefit / self.cost
        else:
            self.roi = float('inf') if self.benefit > 0 else 0.0


class WagonForecaster:
    """
    Markov chain-based forecaster for wagon availability.
    
    This class builds a transition matrix from historical delay data
    and uses it to forecast future wagon availability states.
    """
    
    def __init__(self):
        """Initialize the forecaster."""
        self.transition_matrix: Optional[np.ndarray] = None
        self.state_names: List[str] = [state.value for state in WagonState]
        self.state_count: int = len(WagonState)
    
    def build_markov_matrix(
        self,
        historical_delays: List[Tuple[str, str]]
    ) -> np.ndarray:
        """
        Build Markov transition matrix from historical data.
        
        Args:
            historical_delays: List of (from_state, to_state) transitions
            
        Returns:
            6×6 transition matrix where P[i,j] = probability of 
            transitioning from state i to state j
            
        Example:
            >>> historical = [
            ...     ("Available", "In Transit to Terminal"),
            ...     ("Available", "In Transit to Terminal"),
            ...     ("In Transit to Terminal", "At Terminal"),
            ... ]
            >>> matrix = forecaster.build_markov_matrix(historical)
        """
        # Initialize count matrix
        count_matrix = np.zeros((self.state_count, self.state_count))
        
        # State name to index mapping
        state_to_idx = {state.value: idx for idx, state in enumerate(WagonState)}
        
        # Count transitions
        for from_state, to_state in historical_delays:
            if from_state in state_to_idx and to_state in state_to_idx:
                from_idx = state_to_idx[from_state]
                to_idx = state_to_idx[to_state]
                count_matrix[from_idx, to_idx] += 1
        
        # Normalize rows to get probabilities
        # Each row should sum to 1
        transition_matrix = np.zeros_like(count_matrix, dtype=float)
        
        for i in range(self.state_count):
            row_sum = count_matrix[i, :].sum()
            if row_sum > 0:
                transition_matrix[i, :] = count_matrix[i, :] / row_sum
            else:
                # If no transitions observed from this state, assume it stays
                transition_matrix[i, i] = 1.0
        
        self.transition_matrix = transition_matrix
        return transition_matrix
    
    def forecast(
        self,
        current_state_vector: np.ndarray,
        days_ahead: int
    ) -> np.ndarray:
        """
        Forecast future state distribution using Markov chain.
        
        Args:
            current_state_vector: Initial state probability distribution (length 6)
            days_ahead: Number of days to forecast
            
        Returns:
            Array of shape (days_ahead+1, 6) containing probability distributions
            for each day. π[0] = current_state, π[day] = π[day-1] · P
            
        Example:
            >>> initial = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0])  # All available
            >>> forecast = forecaster.forecast(initial, days_ahead=7)
            >>> forecast.shape
            (8, 6)
        """
        if self.transition_matrix is None:
            raise ValueError("Transition matrix not built. Call build_markov_matrix() first.")
        
        # Validate input
        if len(current_state_vector) != self.state_count:
            raise ValueError(
                f"State vector must have length {self.state_count}, "
                f"got {len(current_state_vector)}"
            )
        
        # Normalize state vector
        current_state_vector = current_state_vector / current_state_vector.sum()
        
        # Initialize forecast array
        forecast = np.zeros((days_ahead + 1, self.state_count))
        forecast[0, :] = current_state_vector
        
        # Iterate through days
        for day in range(1, days_ahead + 1):
            # π[day] = π[day-1] · P (matrix multiplication)
            forecast[day, :] = forecast[day - 1, :] @ self.transition_matrix
        
        return forecast
    
    def get_expected_available(
        self,
        forecast: np.ndarray,
        N_total: int
    ) -> Dict[int, float]:
        """
        Calculate expected number of available wagons for each day.
        
        Args:
            forecast: Forecast array from forecast() method
            N_total: Total number of wagons in the fleet
            
        Returns:
            Dictionary mapping day number to expected available wagons
            
        Example:
            >>> forecast = forecaster.forecast(initial, days_ahead=7)
            >>> expected = forecaster.get_expected_available(forecast, N_total=500)
            >>> expected[0]  # Day 0
            500.0
            >>> expected[7]  # Day 7
            350.5
        """
        result = {}
        available_idx = 0  # Index for "Available" state
        
        for day in range(len(forecast)):
            π_available = forecast[day, available_idx]
            result[day] = N_total * π_available
        
        return result
    
    def get_P90_quantile(
        self,
        forecast: np.ndarray,
        N_total: int,
        trials: int = 10000
    ) -> Dict[int, float]:
        """
        Calculate 90th percentile of available wagons.
        
        Uses Monte Carlo simulation to estimate the distribution and
        calculate the 90th percentile (P90) value.
        
        Args:
            forecast: Forecast array from forecast() method
            N_total: Total number of wagons in the fleet
            trials: Number of Monte Carlo trials
            
        Returns:
            Dictionary mapping day number to P90 available wagons
            
        Note:
            P90 means 90% of simulations show at most this many wagons
            available.
        """
        result = {}
        
        for day in range(len(forecast)):
            # Get probability distribution for this day
            prob_dist = forecast[day, :]
            
            # Run Monte Carlo simulation
            samples = []
            for _ in range(trials):
                # Sample state for each wagon
                states = np.random.choice(
                    self.state_count,
                    size=N_total,
                    p=prob_dist
                )
                # Count available wagons (state index 0)
                available_count = np.sum(states == 0)
                samples.append(available_count)
            
            # Calculate 90th percentile
            # Note: P90 = 90th percentile, meaning 90% of simulations have <= this value
            result[day] = np.percentile(samples, 90)
        
        return result


def identify_wagon_shortage_risks(
    operations: List[Dict[str, Any]],
    forecast: Dict[int, float],
    demurrage_rate: float = 100000.0
) -> List[Risk]:
    """
    Identify wagon shortage risks by comparing needed vs forecasted wagons.
    
    Args:
        operations: List of operations with wagon requirements
        forecast: Forecast of available wagons by day (from get_P90_quantile)
        demurrage_rate: Cost per hour of demurrage (RUB)
        
    Returns:
        List of Risk objects for wagon shortages
        
    Example:
        >>> operations = [
        ...     {
        ...         "op_id": "OP_001",
        ...         "op_type": "rail_batch",
        ...         "wagons_needed": 18,
        ...         "scheduled_day": 3,
        ...         "product": "palm_oil"
        ...     }
        ... ]
        >>> risks = identify_wagon_shortage_risks(operations, forecast_P90)
    """
    risks = []
    risk_counter = 1
    
    for op in operations:
        # Only check operations that need wagons
        op_type = op.get("op_type", "")
        if "rail" not in op_type.lower() and "discharge" not in op_type.lower():
            continue
        
        wagons_needed = op.get("wagons_needed", op.get("wagons", 0))
        if wagons_needed <= 0:
            continue
        
        # Get scheduled day
        scheduled_day = op.get("scheduled_day", 0)
        if scheduled_day not in forecast:
            continue
        
        # Get forecast availability
        forecast_available = forecast[scheduled_day]
        
        # Check if there's a shortage
        gap = wagons_needed - forecast_available
        if gap > 0:
            # Calculate impact
            # Assume shortage causes 24h delay
            delay_hours = 24.0
            impact = gap * demurrage_rate * delay_hours / wagons_needed
            
            # Determine severity
            if gap >= wagons_needed:
                severity = RiskSeverity.CRITICAL
                probability = 0.8
            elif gap >= wagons_needed * 0.5:
                severity = RiskSeverity.HIGH
                probability = 0.6
            elif gap >= wagons_needed * 0.25:
                severity = RiskSeverity.MEDIUM
                probability = 0.4
            else:
                severity = RiskSeverity.LOW
                probability = 0.2
            
            risk = Risk(
                risk_id=f"RISK_WAGON_{risk_counter:03d}",
                risk_type=RiskType.WAGON_SHORTAGE,
                severity=severity,
                description=(
                    f"Wagon shortage for {op.get('op_id', 'Unknown')}: "
                    f"need {wagons_needed} wagons, forecast only {forecast_available:.0f} available"
                ),
                probability=probability,
                impact=impact,
                affected_operations=[op.get("op_id", f"OP_{risk_counter}")],
                metadata={
                    "wagons_needed": wagons_needed,
                    "wagons_forecast": forecast_available,
                    "shortage_gap": gap,
                    "scheduled_day": scheduled_day,
                }
            )
            risks.append(risk)
            risk_counter += 1
    
    return risks


def identify_tank_overflow_risks(
    balance_simulation: Dict[str, List[Dict[str, Any]]],
    tanks: Dict[str, Any],
    threshold: float = 0.95
) -> List[Risk]:
    """
    Identify tank overflow risks from balance simulation.
    
    Args:
        balance_simulation: Tank balance simulation results
            Format: {tank_id: [{"time": datetime, "volume": float, "capacity": float}, ...]}
        tanks: Dictionary of tank configurations
        threshold: Capacity threshold for risk (default 0.95 = 95%)
        
    Returns:
        List of Risk objects for tank overflow risks
        
    Example:
        >>> balance = {
        ...     "RVS_3": [
        ...         {"time": datetime(...), "volume": 9500, "capacity": 9900},
        ...         {"time": datetime(...), "volume": 9800, "capacity": 9900},
        ...     ]
        ... }
        >>> risks = identify_tank_overflow_risks(balance, tanks)
    """
    risks = []
    risk_counter = 1
    
    for tank_id, balance_history in balance_simulation.items():
        # Find peaks (highest utilization points)
        max_utilization = 0.0
        peak_time = None
        peak_volume = 0.0
        peak_capacity = 0.0
        
        for snapshot in balance_history:
            volume = snapshot.get("volume", 0.0)
            capacity = snapshot.get("capacity", 1.0)
            
            if capacity > 0:
                utilization = volume / capacity
                if utilization > max_utilization:
                    max_utilization = utilization
                    peak_time = snapshot.get("time")
                    peak_volume = volume
                    peak_capacity = capacity
        
        # Check if peak exceeds threshold
        if max_utilization > threshold:
            # Calculate impact (cost of emergency measures)
            overflow_margin = max_utilization - threshold
            impact = overflow_margin * 1000000.0  # 1M RUB per 1% over
            
            # Determine severity and probability
            if max_utilization >= 1.0:
                severity = RiskSeverity.CRITICAL
                probability = 0.9
            elif max_utilization >= 0.98:
                severity = RiskSeverity.HIGH
                probability = 0.7
            elif max_utilization >= 0.96:
                severity = RiskSeverity.MEDIUM
                probability = 0.5
            else:
                severity = RiskSeverity.LOW
                probability = 0.3
            
            risk = Risk(
                risk_id=f"RISK_OVERFLOW_{risk_counter:03d}",
                risk_type=RiskType.TANK_OVERFLOW,
                severity=severity,
                description=(
                    f"Tank overflow risk for {tank_id}: "
                    f"peak utilization {max_utilization*100:.1f}% "
                    f"({peak_volume:.0f}t / {peak_capacity:.0f}t)"
                ),
                probability=probability,
                impact=impact,
                affected_operations=[],  # Would need to trace back to operations
                time_window=(peak_time, peak_time) if peak_time else None,
                metadata={
                    "tank_id": tank_id,
                    "peak_utilization": max_utilization,
                    "peak_volume": peak_volume,
                    "peak_capacity": peak_capacity,
                    "threshold": threshold,
                }
            )
            risks.append(risk)
            risk_counter += 1
    
    return risks


def identify_critical_path_ops(
    operations: List[Dict[str, Any]]
) -> List[Risk]:
    """
    Identify critical path operations using dependency graph analysis.
    
    Operations on the critical path have zero slack time and any delay
    will delay the entire project.
    
    Args:
        operations: List of operations with dependencies and timing
            Each operation should have:
            - op_id: str
            - dependencies: List[str]
            - start_time: datetime
            - end_time: datetime
            - duration: float (hours)
            
    Returns:
        List of Risk objects for critical path operations
        
    Example:
        >>> operations = [
        ...     {
        ...         "op_id": "OP_001",
        ...         "start_time": datetime(2024, 1, 1, 8, 0),
        ...         "end_time": datetime(2024, 1, 1, 20, 0),
        ...         "duration": 12.0,
        ...         "dependencies": []
        ...     },
        ...     {
        ...         "op_id": "OP_002",
        ...         "start_time": datetime(2024, 1, 1, 20, 0),
        ...         "end_time": datetime(2024, 1, 2, 8, 0),
        ...         "duration": 12.0,
        ...         "dependencies": ["OP_001"]
        ...     }
        ... ]
        >>> risks = identify_critical_path_ops(operations)
    """
    if not operations:
        return []
    
    # Build dependency graph
    op_dict = {op["op_id"]: op for op in operations}
    
    # Calculate earliest start/finish times (forward pass)
    earliest_start = {}
    earliest_finish = {}
    
    # Topological sort using dependencies
    sorted_ops = _topological_sort(operations)
    
    for op_id in sorted_ops:
        op = op_dict[op_id]
        deps = op.get("dependencies", [])
        
        if not deps:
            # No dependencies - can start at scheduled time
            earliest_start[op_id] = op.get("start_time")
        else:
            # Must start after all dependencies finish
            dep_finish_times = [
                earliest_finish.get(dep_id)
                for dep_id in deps
                if dep_id in earliest_finish
            ]
            # Filter out None values to avoid comparison errors
            valid_finish_times = [t for t in dep_finish_times if t is not None]
            
            if valid_finish_times:
                earliest_start[op_id] = max(valid_finish_times)
            else:
                earliest_start[op_id] = op.get("start_time")
        
        # Calculate earliest finish
        duration_hours = op.get("duration", 0.0)
        if earliest_start[op_id]:
            from datetime import timedelta
            earliest_finish[op_id] = earliest_start[op_id] + timedelta(hours=duration_hours)
        else:
            earliest_finish[op_id] = op.get("end_time")
    
    # Calculate latest start/finish times (backward pass)
    # For simplicity, assume project deadline is max(earliest_finish)
    if earliest_finish:
        project_deadline = max(earliest_finish.values())
    else:
        end_times = [op["end_time"] for op in operations if op.get("end_time") is not None]
        project_deadline = max(end_times) if end_times else datetime.now()
    
    latest_finish = {}
    latest_start = {}
    
    # Reverse topological order
    for op_id in reversed(sorted_ops):
        op = op_dict[op_id]
        
        # Find operations that depend on this one
        successors = [
            other_id for other_id, other_op in op_dict.items()
            if op_id in other_op.get("dependencies", [])
        ]
        
        if not successors:
            # No successors - must finish by project deadline
            latest_finish[op_id] = project_deadline
        else:
            # Must finish before earliest successor starts
            successor_starts = [
                latest_start[succ_id]
                for succ_id in successors
                if succ_id in latest_start
            ]
            if successor_starts:
                latest_finish[op_id] = min(successor_starts)
            else:
                latest_finish[op_id] = project_deadline
        
        # Calculate latest start
        duration_hours = op.get("duration", 0.0)
        from datetime import timedelta
        latest_start[op_id] = latest_finish[op_id] - timedelta(hours=duration_hours)
    
    # Calculate slack time and identify critical operations
    risks = []
    risk_counter = 1
    
    for op_id in sorted_ops:
        if op_id in earliest_start and op_id in latest_start:
            slack = (latest_start[op_id] - earliest_start[op_id]).total_seconds() / 3600.0
            
            # Operations with zero (or near-zero) slack are on critical path
            if abs(slack) < 0.1:  # Within 6 minutes
                # Critical path operations are high risk
                # Any delay propagates to project completion
                impact = 500000.0  # Base impact for delays
                
                risk = Risk(
                    risk_id=f"RISK_CRITICAL_{risk_counter:03d}",
                    risk_type=RiskType.CRITICAL_PATH,
                    severity=RiskSeverity.HIGH,
                    description=(
                        f"Operation {op_id} is on critical path with zero slack. "
                        f"Any delay will delay project completion."
                    ),
                    probability=0.3,  # Assume 30% chance of delay on critical ops
                    impact=impact,
                    affected_operations=[op_id],
                    metadata={
                        "slack_hours": slack,
                        "earliest_start": earliest_start[op_id],
                        "latest_start": latest_start[op_id],
                    }
                )
                risks.append(risk)
                risk_counter += 1
    
    return risks


def _topological_sort(operations: List[Dict[str, Any]]) -> List[str]:
    """
    Perform topological sort on operations based on dependencies.
    
    Args:
        operations: List of operations with dependencies
        
    Returns:
        List of operation IDs in topological order
    """
    # Build adjacency list
    graph = {op["op_id"]: op.get("dependencies", []) for op in operations}
    
    # Track visited nodes
    visited = set()
    result = []
    
    def visit(node_id: str):
        if node_id in visited:
            return
        visited.add(node_id)
        
        # Visit dependencies first
        for dep_id in graph.get(node_id, []):
            if dep_id in graph:
                visit(dep_id)
        
        result.append(node_id)
    
    # Visit all nodes
    for op_id in graph:
        visit(op_id)
    
    return result


def generate_recommendations(
    risks: List[Risk],
    demurrage_rate: float = 100000.0,
    wagon_external_cost: float = 50000.0,
    wagon_own_cost: float = 3000.0
) -> List[Recommendation]:
    """
    Generate mitigation recommendations for identified risks.
    
    Args:
        risks: List of Risk objects to generate recommendations for
        demurrage_rate: Cost per hour of demurrage (RUB)
        wagon_external_cost: Cost to lease external wagon (RUB per wagon)
        wagon_own_cost: Cost to use own wagon (RUB per wagon)
        
    Returns:
        List of Recommendation objects sorted by ROI (descending)
        
    Example:
        >>> risks = identify_wagon_shortage_risks(operations, forecast)
        >>> recommendations = generate_recommendations(risks)
        >>> for rec in recommendations[:5]:  # Top 5
        ...     print(f"{rec.action}: ROI={rec.roi:.2f}")
    """
    recommendations = []
    rec_counter = 1
    
    for risk in risks:
        # Generate recommendation based on risk type
        if risk.risk_type == RiskType.WAGON_SHORTAGE:
            shortage_gap = risk.metadata.get("shortage_gap", 0)
            
            # Option 1: Lease external wagons
            action = f"Lease {int(shortage_gap)} external wagons"
            cost = shortage_gap * wagon_external_cost
            benefit = risk.expected_value
            
            rec = Recommendation(
                rec_id=f"REC_{rec_counter:03d}",
                risk_id=risk.risk_id,
                action=action,
                cost=cost,
                benefit=benefit,
                implementation_time=48.0,  # 2 days to arrange
                notes="External wagon leasing to cover shortage"
            )
            recommendations.append(rec)
            rec_counter += 1
            
            # Option 2: Reschedule operation if possible
            action = f"Reschedule operation {risk.affected_operations[0] if risk.affected_operations else 'Unknown'}"
            cost = 50000.0  # Administrative cost
            benefit = risk.expected_value * 0.8  # Partial benefit
            
            rec = Recommendation(
                rec_id=f"REC_{rec_counter:03d}",
                risk_id=risk.risk_id,
                action=action,
                cost=cost,
                benefit=benefit,
                implementation_time=24.0,
                notes="Reschedule to period with better wagon availability"
            )
            recommendations.append(rec)
            rec_counter += 1
        
        elif risk.risk_type == RiskType.TANK_OVERFLOW:
            tank_id = risk.metadata.get("tank_id", "Unknown")
            peak_volume = risk.metadata.get("peak_volume", 0)
            peak_capacity = risk.metadata.get("peak_capacity", 1)
            
            # Option 1: Accelerate discharge operations
            action = f"Accelerate discharge from {tank_id}"
            cost = 200000.0  # Overtime and expediting costs
            benefit = risk.expected_value
            
            rec = Recommendation(
                rec_id=f"REC_{rec_counter:03d}",
                risk_id=risk.risk_id,
                action=action,
                cost=cost,
                benefit=benefit,
                implementation_time=12.0,
                notes="Increase discharge rate or add extra shifts"
            )
            recommendations.append(rec)
            rec_counter += 1
            
            # Option 2: Temporary storage arrangement
            excess_volume = peak_volume - peak_capacity * 0.95
            action = f"Arrange temporary storage for {excess_volume:.0f}t"
            cost = excess_volume * 500.0  # Cost per tonne for temp storage
            benefit = risk.expected_value
            
            rec = Recommendation(
                rec_id=f"REC_{rec_counter:03d}",
                risk_id=risk.risk_id,
                action=action,
                cost=cost,
                benefit=benefit,
                implementation_time=72.0,
                notes="Secure alternative storage capacity"
            )
            recommendations.append(rec)
            rec_counter += 1
        
        elif risk.risk_type == RiskType.CRITICAL_PATH:
            op_id = risk.affected_operations[0] if risk.affected_operations else "Unknown"
            
            # Option 1: Add buffer/contingency time
            action = f"Add contingency time buffer for {op_id}"
            cost = 100000.0  # Cost of schedule adjustment
            benefit = risk.expected_value
            
            rec = Recommendation(
                rec_id=f"REC_{rec_counter:03d}",
                risk_id=risk.risk_id,
                action=action,
                cost=cost,
                benefit=benefit,
                implementation_time=24.0,
                notes="Build in schedule flexibility for critical operations"
            )
            recommendations.append(rec)
            rec_counter += 1
            
            # Option 2: Increase resource allocation
            action = f"Allocate additional resources to {op_id}"
            cost = 300000.0  # Extra equipment/personnel
            benefit = risk.expected_value * 1.2  # Higher benefit from faster execution
            
            rec = Recommendation(
                rec_id=f"REC_{rec_counter:03d}",
                risk_id=risk.risk_id,
                action=action,
                cost=cost,
                benefit=benefit,
                implementation_time=48.0,
                notes="Deploy extra resources to reduce duration and risk"
            )
            recommendations.append(rec)
            rec_counter += 1
    
    # Sort by ROI descending
    recommendations.sort(key=lambda r: r.roi, reverse=True)
    
    # Assign priority based on sorted order
    for idx, rec in enumerate(recommendations):
        rec.priority = idx + 1
    
    return recommendations


def create_risk_summary(
    risks: List[Risk],
    recommendations: List[Recommendation]
) -> Dict[str, Any]:
    """
    Create a summary report of risks and recommendations.
    
    Args:
        risks: List of identified risks
        recommendations: List of mitigation recommendations
        
    Returns:
        Dictionary containing summary statistics and top items
    """
    summary = {
        "total_risks": len(risks),
        "total_expected_value": sum(r.expected_value for r in risks),
        "risks_by_type": {},
        "risks_by_severity": {},
        "top_risks": [],
        "total_recommendations": len(recommendations),
        "top_recommendations": [],
        "total_mitigation_cost": sum(r.cost for r in recommendations),
        "total_potential_benefit": sum(r.benefit for r in recommendations),
    }
    
    # Count by type
    for risk_type in RiskType:
        count = sum(1 for r in risks if r.risk_type == risk_type)
        if count > 0:
            summary["risks_by_type"][risk_type.value] = count
    
    # Count by severity
    for severity in RiskSeverity:
        count = sum(1 for r in risks if r.severity == severity)
        if count > 0:
            summary["risks_by_severity"][severity.value] = count
    
    # Top 10 risks by expected value
    sorted_risks = sorted(risks, key=lambda r: r.expected_value, reverse=True)
    summary["top_risks"] = [
        {
            "risk_id": r.risk_id,
            "type": r.risk_type.value,
            "severity": r.severity.value,
            "description": r.description,
            "expected_value": r.expected_value,
        }
        for r in sorted_risks[:10]
    ]
    
    # Top 10 recommendations by ROI
    summary["top_recommendations"] = [
        {
            "rec_id": r.rec_id,
            "action": r.action,
            "cost": r.cost,
            "benefit": r.benefit,
            "roi": r.roi,
            "priority": r.priority,
        }
        for r in recommendations[:10]
    ]
    
    return summary


# =============================================================================
# Compatibility wrappers for legacy code
# =============================================================================

def identify_critical_points(
    operations: List[Any],
    tanks: Dict[str, Any],
    balances: Any = None
) -> List[Dict[str, Any]]:
    """
    Wrapper for identify_critical_path_ops for compatibility with main.py.
    
    Args:
        operations: List of Operation objects
        tanks: Dictionary of tanks (unused in current implementation)
        balances: Balance dataframe (unused in current implementation)
        
    Returns:
        List of critical points as dictionaries
    """
    # Convert operations to dict format for identify_critical_path_ops
    ops_as_dicts = []
    for op in operations:
        op_dict = {
            "op_id": getattr(op, 'op_id', 'UNKNOWN'),
            "dependencies": getattr(op, 'dependencies', []),
            "start_time": getattr(op, 'start_time', None),
            "end_time": getattr(op, 'end_time', None),
            "duration": getattr(op, 'duration', 0.0),
        }
        ops_as_dicts.append(op_dict)
    
    # Get risks from identify_critical_path_ops
    risks = identify_critical_path_ops(ops_as_dicts)
    
    # Convert risks to simpler dict format
    critical_points = []
    for risk in risks:
        critical_points.append({
            "op_id": risk.affected_operations[0] if risk.affected_operations else 'UNKNOWN',
            "reason": risk.description,
            "slack_hours": risk.metadata.get("slack_hours", 0),
            "severity": risk.severity.value,
        })
    
    return critical_points


def analyze_sequence_risks(
    operations: List[Any],
    scenario: Any
) -> Dict[str, Any]:
    """
    Wrapper for comprehensive risk analysis for compatibility with main.py.
    
    Args:
        operations: List of Operation objects
        scenario: Scenario object
        
    Returns:
        Dictionary with categorized risks
    """
    # Convert operations to dict format
    ops_as_dicts = []
    for op in operations:
        op_dict = {
            "op_id": getattr(op, 'op_id', 'UNKNOWN'),
            "op_type": getattr(op, 'op_type', 'unknown'),
            "dependencies": getattr(op, 'dependencies', []),
            "start_time": getattr(op, 'start_time', None),
            "end_time": getattr(op, 'end_time', None),
            "duration": getattr(op, 'duration', 0.0),
            "wagons_needed": getattr(op, 'wagons', 0),
        }
        ops_as_dicts.append(op_dict)
    
    # Identify critical path risks
    critical_risks = identify_critical_path_ops(ops_as_dicts)
    
    # Categorize by severity
    high_severity = []
    medium_severity = []
    low_severity = []
    
    for risk in critical_risks:
        risk_dict = {
            "risk_id": risk.risk_id,
            "description": risk.description,
            "impact": risk.expected_value,
            "probability": risk.probability,
            "mitigation": "Add contingency time or allocate additional resources",
        }
        
        if risk.severity in [RiskSeverity.HIGH, RiskSeverity.CRITICAL]:
            high_severity.append(risk_dict)
        elif risk.severity == RiskSeverity.MEDIUM:
            medium_severity.append(risk_dict)
        else:
            low_severity.append(risk_dict)
    
    return {
        "high_severity": high_severity,
        "medium_severity": medium_severity,
        "low_severity": low_severity,
        "total_count": len(critical_risks),
    }
