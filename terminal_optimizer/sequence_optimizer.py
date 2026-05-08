"""
Sequence Optimizer Module

This module provides functionality to optimize the order of vessel operations
to minimize total costs, including demurrage and cleaning downtime.

Classes:
    SequenceOptimizer: Optimizes vessel sequences for each berth.
"""

from __future__ import annotations
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
import itertools
import math

from .domain_models import Vessel, Operation, Scenario, CargoType, OperationType
from .sequence_generator import PalmSequenceGenerator, SunflowerHandler, SequenceCoordinator
from .constants import BERTH_PALM, BERTH_SUNFLOWER

class SequenceOptimizer:
    """
    Optimizes the sequence of vessels to minimize operational costs.
    
    The optimizer handles Palm and Sunflower vessels separately as they use
    independent berths. It uses a permutation-based approach for small numbers
    of vessels and a greedy heuristic for larger numbers.
    """
    
    def __init__(self, scenario: Scenario):
        """
        Initialize the optimizer.
        
        Args:
            scenario: The scenario containing vessels and tanks.
        """
        self.scenario = scenario
        self.tanks = scenario.tanks
        self.parameters = scenario.parameters
        
        # Initialize generators
        self.palm_generator = PalmSequenceGenerator(self.tanks, self.parameters)
        self.sunflower_handler = SunflowerHandler(self.tanks, self.parameters)
        self.coordinator = SequenceCoordinator(self.tanks, self.parameters)

    def optimize(self, vessels: List[Vessel]) -> List[Operation]:
        """
        Optimize the sequence for the provided list of vessels.
        
        Args:
            vessels: List of vessels to optimize.
            
        Returns:
            List of optimized operations.
        """
        # 1. Separate vessels by berth/type
        palm_vessels = [v for v in vessels if v.cargo_type == CargoType.PALM]
        sunflower_vessels = [v for v in vessels if v.cargo_type == CargoType.SUNFLOWER]
        
        # 2. Optimize each group independently
        optimized_palm_ops = self._optimize_group(palm_vessels, "palm")
        optimized_sunflower_ops = self._optimize_group(sunflower_vessels, "sunflower")
        
        # 3. Merge and resolve any cross-berth conflicts (e.g. shared tanks)
        all_ops = self.coordinator.merge_sequences([optimized_palm_ops, optimized_sunflower_ops])
        resolved_ops, _ = self.coordinator.resolve_all_conflicts(all_ops)
        
        return resolved_ops

    def _optimize_group(self, vessels: List[Vessel], group_type: str) -> List[Operation]:
        """
        Optimize a group of vessels sharing the same berth.
        
        Args:
            vessels: List of vessels.
            group_type: "palm" or "sunflower".
            
        Returns:
            List of operations for the best sequence.
        """
        if not vessels:
            return []
            
        # If few vessels, try all permutations
        if len(vessels) <= 5:
            return self._optimize_permutations(vessels, group_type)
        else:
            return self._optimize_greedy(vessels, group_type)

    def _optimize_permutations(self, vessels: List[Vessel], group_type: str) -> List[Operation]:
        """Try all permutations to find the best sequence."""
        best_cost = float('inf')
        best_ops = []
        
        # Sort by ETA initially to limit permutations to reasonable windows if needed
        # But for N<=5, we can just do full factorial
        
        for perm in itertools.permutations(vessels):
            ops, cost = self._evaluate_sequence(list(perm), group_type)
            if cost < best_cost:
                best_cost = cost
                best_ops = ops
                
        return best_ops

    def _optimize_greedy(self, vessels: List[Vessel], group_type: str) -> List[Operation]:
        """
        Greedy optimization: pick the next vessel that minimizes immediate cost.
        """
        # Start with vessels sorted by ETA
        remaining = sorted(vessels, key=lambda v: v.eta)
        sequence = []
        current_time = min(v.eta for v in vessels)
        
        # Track state
        current_inventory = self.scenario.current_inventory.copy()
        line_status = {"Line1": None, "Line2": None}
        
        while remaining:
            best_next_vessel = None
            best_step_cost = float('inf')
            
            # Look at next few available vessels (window size 3)
            candidates = remaining[:3]
            
            for candidate in candidates:
                # Calculate cost of picking this candidate next
                # This is a simplified lookahead
                wait_time = max(0, (current_time - candidate.eta).total_seconds() / 3600)
                demurrage = candidate.calculate_demurrage(wait_time)
                
                # Estimate cleaning cost (only for Palm)
                cleaning_cost = 0
                if group_type == "palm":
                    # Check compatibility with last line products
                    # This is a heuristic estimation
                    pass 
                
                step_cost = demurrage + cleaning_cost
                
                if step_cost < best_step_cost:
                    best_step_cost = step_cost
                    best_next_vessel = candidate
            
            if best_next_vessel:
                sequence.append(best_next_vessel)
                remaining.remove(best_next_vessel)
                # Update current_time (approximate)
                duration = best_next_vessel.total_volume / 500.0 # Approx rate
                current_time += timedelta(hours=duration + 4.0) # + unberthing
            else:
                # Fallback
                v = remaining.pop(0)
                sequence.append(v)
        
        # Generate full operations for the final sequence
        ops, _ = self._evaluate_sequence(sequence, group_type)
        return ops

    def _evaluate_sequence(self, sequence: List[Vessel], group_type: str) -> Tuple[List[Operation], float]:
        """
        Generate operations and calculate cost for a specific sequence.
        
        Args:
            sequence: Ordered list of vessels.
            group_type: "palm" or "sunflower".
            
        Returns:
            Tuple of (operations, total_cost).
        """
        operations = []
        current_inventory = self.scenario.current_inventory.copy() # Deep copy needed in real sim
        # Note: We are not doing a full deep copy of inventory for performance in permutation,
        # but generate_sequence doesn't modify the input dict structure deeply, usually.
        # However, to be safe, we should be careful. 
        # For this implementation, we assume generate_sequence is stateless enough regarding inventory structure
        # or we accept slight inaccuracy in optimization for speed.
        
        line_status = {"Line1": None, "Line2": None}
        
        total_demurrage = 0.0
        total_cleaning_time = 0.0
        
        # Determine start time based on first vessel
        if not sequence:
            return [], 0.0
            
        current_time = sequence[0].eta
        
        for vessel in sequence:
            # Vessel cannot start before ETA
            start_time = max(current_time, vessel.eta)
            
            # Calculate demurrage for waiting
            wait_hours = (start_time - vessel.eta).total_seconds() / 3600
            if wait_hours > 0:
                total_demurrage += vessel.calculate_demurrage(wait_hours)
            
            vessel_ops = []
            if group_type == "palm":
                # Generate palm operations
                large, small = self.palm_generator.classify_fractions(vessel)
                line_allocs = self.palm_generator.allocate_lines(large, small)
                tank_allocs = self.palm_generator.allocate_tanks(line_allocs, current_inventory)
                
                vessel_ops = self.palm_generator.generate_sequence(
                    vessel, tank_allocs, current_inventory, start_time, line_status
                )
                
                # Update line status from operations
                # Find last product on lines
                for op in vessel_ops:
                    if op.op_type == OperationType.DISCHARGE:
                        if op.line == "Line1":
                            line_status["Line1"] = op.product
                        elif op.line == "Line2":
                            line_status["Line2"] = op.product
                    elif op.op_type == OperationType.CLEANING:
                        total_cleaning_time += op.duration
                        
            elif group_type == "sunflower":
                # Generate sunflower operations
                vessel_ops = self.sunflower_handler.generate_loading_plan(
                    vessel, current_inventory, start_time
                )
            
            operations.extend(vessel_ops)
            
            # Update tank states for next vessel
            for op in vessel_ops:
                if op.op_type == OperationType.DISCHARGE and op.target in current_inventory:
                    current_inventory[op.target]["current_product"] = op.product
                    # We don't strictly track volume here as it's complex, but we track product
                    # For SHT, we know it's emptied, but product remains
                elif op.op_type == OperationType.CLEANING and op.target in current_inventory:
                    current_inventory[op.target]["current_product"] = None
            
            # Update current_time for next vessel
            if vessel_ops:
                last_op = max(vessel_ops, key=lambda o: o.end_time if o.end_time else datetime.min)
                if last_op.end_time:
                    current_time = last_op.end_time
        
        # Calculate total cost
        # Cost = Demurrage + (Cleaning Hours * Cost per Hour)
        CLEANING_COST_PER_HOUR = 5000.0 # Arbitrary cost for optimization
        total_cost = total_demurrage + (total_cleaning_time * CLEANING_COST_PER_HOUR)
        
        return operations, total_cost
