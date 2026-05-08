"""
Monte Carlo Simulation Module

This module provides capabilities for running Monte Carlo simulations
to assess the robustness of terminal plans against variability.

Classes:
    MonteCarloSimulator: Runs multiple iterations with perturbed parameters
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import random
import copy
import statistics

from .domain_models import Scenario, Operation
from .sequence_generator import PalmSequenceGenerator, SunflowerHandler
from .balance_calculator import TankBalanceCalculator
from .validation import ValidationEngine
from .logger import get_logger

logger = get_logger(__name__)

@dataclass
class SimulationResult:
    """Result of a single simulation iteration."""
    iteration: int
    success: bool
    conflicts: int
    overflows: int
    max_delay_hours: float
    total_duration_hours: float
    notes: str = ""

@dataclass
class MonteCarloReport:
    """Aggregated report from Monte Carlo simulation."""
    iterations: int
    success_rate: float
    avg_conflicts: float
    avg_overflows: float
    avg_delay: float
    p90_delay: float
    confidence_score: float  # 0.0 to 1.0
    recommendations: List[str]

class MonteCarloSimulator:
    """
    Runs Monte Carlo simulations to test plan robustness.
    
    Variability factors:
    - Vessel ETA: +/- 12 hours
    - Flow rates: +/- 10%
    """
    
    def __init__(self, scenario: Scenario):
        """
        Initialize simulator.
        
        Args:
            scenario: Base scenario to simulate
        """
        self.base_scenario = scenario
    
    def run(self, iterations: int = 100) -> MonteCarloReport:
        """
        Run simulation iterations.
        
        Args:
            iterations: Number of iterations to run
            
        Returns:
            MonteCarloReport with aggregated statistics
        """
        logger.info(f"Starting Monte Carlo simulation with {iterations} iterations")
        
        results = []
        
        for i in range(iterations):
            # Create perturbed scenario
            scenario = self._perturb_scenario(self.base_scenario)
            
            # Run simulation step
            result = self._run_iteration(i, scenario)
            results.append(result)
        
        return self._aggregate_results(results)
    
    def _perturb_scenario(self, base_scenario: Scenario) -> Scenario:
        """
        Create a copy of the scenario with perturbed parameters.
        """
        # Deep copy to avoid modifying original
        # Note: Scenario contains complex objects, so we need to be careful
        # For simplicity, we'll recreate the scenario structure
        
        # Perturb parameters
        params = base_scenario.parameters.copy()
        
        # Perturb rates (+/- 10%)
        rate_keys = [k for k in params.keys() if 'rate' in k and isinstance(params[k], (int, float))]
        for key in rate_keys:
            variation = random.uniform(0.9, 1.1)
            params[key] = params[key] * variation
            
        # Create new scenario object
        # We need to clone vessels to perturb ETAs
        vessels = []
        for v in base_scenario.vessels:
            # Clone vessel
            v_copy = copy.deepcopy(v)
            
            # Perturb ETA (+/- 12 hours)
            hours_shift = random.uniform(-12, 12)
            v_copy.eta = v_copy.eta + timedelta(hours=hours_shift)
            vessels.append(v_copy)
            
        # Clone other components
        tanks = copy.deepcopy(base_scenario.tanks)
        rail_schedule = copy.deepcopy(base_scenario.rail_schedule)
        inventory = copy.deepcopy(base_scenario.current_inventory)
        demand = copy.deepcopy(base_scenario.client_demand)
        
        return Scenario(
            scenario_id=f"{base_scenario.scenario_id}_sim",
            vessels=vessels,
            tanks=tanks,
            rail_schedule=rail_schedule,
            current_inventory=inventory,
            client_demand=demand,
            parameters=params,
            horizon_days=base_scenario.horizon_days
        )
    
    def _run_iteration(self, iteration: int, scenario: Scenario) -> SimulationResult:
        """Run a single iteration of the planning logic."""
        try:
            # 1. Generate Sequence
            operations = []
            
            # Palm
            palm_gen = PalmSequenceGenerator(scenario.tanks, scenario.parameters)
            for v in scenario.get_vessels():
                if v.cargo_type.value == "palm":
                    large, small = palm_gen.classify_fractions(v)
                    line_allocs = palm_gen.allocate_lines(large, small)
                    tank_allocs = palm_gen.allocate_tanks(line_allocs, scenario.current_inventory)
                    ops = palm_gen.generate_sequence(v, tank_allocs, scenario.current_inventory, v.eta)
                    operations.extend(ops)
            
            # Sunflower
            sun_handler = SunflowerHandler(scenario.tanks, scenario.parameters)
            for v in scenario.get_vessels():
                if v.cargo_type.value == "sunflower":
                    # Simplified logic for simulation: just generate loading
                    ops = sun_handler.generate_loading_plan(v, scenario.current_inventory, v.eta)
                    operations.extend(ops)
            
            # Sort
            operations.sort(key=lambda op: op.start_time or datetime.min)
            
            # 2. Calculate Balances
            calc = TankBalanceCalculator(scenario.tanks, scenario.parameters)
            horizon_hours = scenario.horizon_days * 24
            start_time = min((op.start_time for op in operations if op.start_time), default=datetime.now())
            balances = calc.simulate(operations, scenario.current_inventory, horizon_hours, start_time)
            
            # 3. Validate
            validator = ValidationEngine(scenario, operations, balances)
            val_result = validator.validate_all()
            
            # Metrics
            conflicts = len(val_result.errors)
            overflows = sum(1 for e in val_result.errors if "overfilled" in e)
            
            # Calculate delay (difference between planned end and ideal end)
            # For simplicity, just use total duration
            if operations:
                end_time = max((op.end_time for op in operations if op.end_time), default=start_time)
                duration = (end_time - start_time).total_seconds() / 3600.0
            else:
                duration = 0.0
            
            return SimulationResult(
                iteration=iteration,
                success=not val_result.has_errors(),
                conflicts=conflicts,
                overflows=overflows,
                max_delay_hours=0.0, # Placeholder
                total_duration_hours=duration
            )
            
        except Exception as e:
            logger.warning(f"Simulation iteration {iteration} failed: {e}")
            return SimulationResult(
                iteration=iteration,
                success=False,
                conflicts=1,
                overflows=0,
                max_delay_hours=0.0,
                total_duration_hours=0.0,
                notes=str(e)
            )

    def _aggregate_results(self, results: List[SimulationResult]) -> MonteCarloReport:
        """Aggregate results into a report."""
        total = len(results)
        if total == 0:
            return MonteCarloReport(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, ["No iterations run"])
            
        success_count = sum(1 for r in results if r.success)
        success_rate = (success_count / total) * 100.0
        
        avg_conflicts = statistics.mean(r.conflicts for r in results)
        avg_overflows = statistics.mean(r.overflows for r in results)
        avg_duration = statistics.mean(r.total_duration_hours for r in results)
        
        # P90 Duration
        durations = sorted(r.total_duration_hours for r in results)
        p90_idx = int(total * 0.9)
        p90_duration = durations[p90_idx] if durations else 0.0
        
        # Confidence Score
        # Simple heuristic: Success rate weighted by conflict severity
        confidence = (success_rate / 100.0) * (1.0 / (1.0 + avg_conflicts))
        
        recommendations = []
        if success_rate < 80:
            recommendations.append("Plan is risky. Consider increasing buffers.")
        if avg_overflows > 0.1:
            recommendations.append("High risk of tank overflow. Check capacity.")
            
        return MonteCarloReport(
            iterations=total,
            success_rate=success_rate,
            avg_conflicts=avg_conflicts,
            avg_overflows=avg_overflows,
            avg_delay=0.0, # Placeholder
            p90_delay=p90_duration, # Using duration as proxy for delay
            confidence_score=confidence,
            recommendations=recommendations
        )
