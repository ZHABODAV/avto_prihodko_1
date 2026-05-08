"""
Main Application Logic for Terminal Optimizer

This module contains the TerminalOptimizer orchestrator class that manages
the entire optimization workflow from data loading to result export.

Classes:
    TerminalOptimizer: Main orchestrator for terminal optimization
    SequenceEditor: Handles user edits to the operation sequence
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from pathlib import Path
import sys

from .domain_models import Scenario, Operation, OperationType, CargoType
from .excel_io import ExcelReader, ExcelWriter
from .sequence_generator import PalmSequenceGenerator, SunflowerHandler
from .sequence_optimizer import SequenceOptimizer
from .balance_calculator import TankBalanceCalculator
from .validation import ValidationEngine, ValidationResult
from .wagon_manager import WagonManager, WagonForecaster
from .risk_analysis import identify_critical_points, analyze_sequence_risks
from .monte_carlo import MonteCarloSimulator
from .logger import (
    get_logger,
    TerminalOptimizerLogger,
    FileIOError,
    DataValidationError,
    SequenceGenerationError,
    CalculationError
)
from .exceptions import TerminalOptimizerError, ExcelFileError, ValidationError, InvalidDataError

# Get logger instance
logger = get_logger(__name__)


class TerminalOptimizer:
    """
    Main orchestrator for terminal optimization workflow.
    
    This class coordinates the entire optimization process:
    1. Load scenario from Excel
    2. Generate initial operation sequence
    3. Calculate tank balances
    4. Validate solution
    5. Calculate wagon requirements
    6. Analyze risks
    7. Export results
    
    Attributes:
        scenario: Current scenario being optimized
        operations: List of operations in the sequence
        balances: Tank balance dataframe from simulation
        validation_result: Result of validation check
        wagon_analysis: Wagon requirement analysis
        risk_report: Risk analysis report
    """
    
    def __init__(self):
        """Initialize the Terminal Optimizer."""
        self.scenario: Optional[Scenario] = None
        self.operations: List[Operation] = []
        self.balances: Optional[Any] = None  # pandas DataFrame
        self.validation_result: Optional[ValidationResult] = None
        self.wagon_analysis: Optional[Dict[str, Any]] = None
        self.risk_report: Optional[Dict[str, Any]] = None
    
    def load_scenario(self, excel_path: str) -> Scenario:
        """
        Load scenario data from Excel file.
        
        Args:
            excel_path: Path to the Excel file with scenario data
            
        Returns:
            Loaded and validated Scenario object
            
        Raises:
            ValueError: If scenario validation fails
            FileNotFoundError: If Excel file not found
        """
        logger.info(f"Loading scenario from: {excel_path}")
        
        # Check file exists
        excel_file = Path(excel_path)
        if not excel_file.exists():
            raise FileNotFoundError(f"Scenario file not found: {excel_path}")
        
        # Load scenario using ExcelReader
        try:
            scenario = ExcelReader.read_from_excel(excel_path)
        except FileNotFoundError as e:
            logger.error(f"Scenario file not found: {excel_path}")
            raise
        except PermissionError as e:
            logger.error(f"Permission denied accessing scenario file: {excel_path}")
            raise
        except (ExcelFileError, InvalidDataError) as e:
            logger.error(f"Failed to load scenario from Excel: {e}")
            raise TerminalOptimizerError(f"Failed to load scenario: {e}") from e
        except (OSError, IOError) as e:
            logger.error(f"File system error loading scenario: {e}")
            raise TerminalOptimizerError(f"File system error loading scenario: {e}") from e
        
        # Validate scenario
        is_valid, errors = scenario.validate()
        if not is_valid:
            error_msg = "Scenario validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"Scenario loaded successfully: {scenario.scenario_id}")
        logger.info(f"  Vessels: {len(scenario.vessels)}")
        logger.info(f"  Tanks: {len(scenario.tanks)}")
        logger.info(f"  Horizon: {scenario.horizon_days} days")
        
        self.scenario = scenario
        return scenario
    
    def generate_initial_sequence(
        self,
        run_mode: str = "all",
        vessel_filter: Optional[List[str]] = None,
        optimize: bool = False
    ) -> List[Operation]:
        """
        Generate initial operation sequence for vessels.
        
        Args:
            run_mode: "all", "palm_only", or "sunflower_only"
            vessel_filter: Optional list of vessel IDs to process
            optimize: Whether to optimize the sequence order
            
        Returns:
            List of operations in chronological order
        """
        if self.scenario is None:
            raise ValueError("No scenario loaded. Call load_scenario() first.")
        
        logger.info(f"Generating sequence (Mode: {run_mode}, Optimize: {optimize})")
        
        # Filter vessels
        vessels = self.scenario.get_vessels()
        filtered_vessels = []
        
        for v in vessels:
            # Check active status
            if not v.is_active:
                continue
                
            # Check mode
            if run_mode == "palm_only" and v.cargo_type != CargoType.PALM:
                continue
            if run_mode == "sunflower_only" and v.cargo_type != CargoType.SUNFLOWER:
                continue
                
            # Check specific filter
            if vessel_filter and v.vessel_id not in vessel_filter:
                continue
                
            filtered_vessels.append(v)
            
        logger.info(f"Processing {len(filtered_vessels)} vessels after filtering")
        
        # Use SequenceOptimizer to generate operations
        # It handles both optimization and standard generation (if optimize=False, it respects ETA order)
        optimizer = SequenceOptimizer(self.scenario)
        
        if optimize:
            all_operations = optimizer.optimize(filtered_vessels)
        else:
            # If not optimizing, just use the optimizer's internal logic but with original order
            # We can reuse _evaluate_sequence but we need to split by group first
            palm_vessels = [v for v in filtered_vessels if v.cargo_type == CargoType.PALM]
            sunflower_vessels = [v for v in filtered_vessels if v.cargo_type == CargoType.SUNFLOWER]
            
            # Sort by ETA to respect arrival order
            palm_vessels.sort(key=lambda v: v.eta)
            sunflower_vessels.sort(key=lambda v: v.eta)
            
            palm_ops, _ = optimizer._evaluate_sequence(palm_vessels, "palm")
            sunflower_ops, _ = optimizer._evaluate_sequence(sunflower_vessels, "sunflower")
            
            # Merge and resolve
            all_ops = optimizer.coordinator.merge_sequences([palm_ops, sunflower_ops])
            all_operations, _ = optimizer.coordinator.resolve_all_conflicts(all_ops)

        # Add rail operations if any (and if mode allows)
        # Rail operations are usually independent but might conflict on tanks
        if self.scenario.rail_schedule:
            logger.info(f"Processing {len(self.scenario.rail_schedule)} rail deliveries")
            rail_ops = self._generate_rail_operations()
            
            # Merge rail ops
            all_operations.extend(rail_ops)
            all_operations.sort(key=lambda op: op.start_time if op.start_time else datetime.max)
            
            # Resolve conflicts again to handle rail/tank interactions
            # Note: SequenceOptimizer already resolved vessel-vessel conflicts
            all_operations = self._resolve_conflicts(all_operations)
        
        logger.info(f"Generated {len(all_operations)} total operations")
        self.operations = all_operations
        return all_operations
    
    def _generate_rail_operations(self) -> List[Operation]:
        """Generate operations for rail schedule."""
        if self.scenario is None:
            raise ValueError("No scenario loaded")

        rail_ops = []
        
        for rail_entry in self.scenario.rail_schedule:
            # Determine target tank based on product if not specified
            target = rail_entry.get('target_tank', "")
            if not target:
                product_val = rail_entry.get('product')
                product = str(product_val).lower() if product_val else ''
                if 'sunflower' in product:
                    target = "RVS-1"  # Default for sunflower
                elif 'palm' in product:
                    target = "RVS-3"  # Default for palm
            
            op = Operation(
                op_id=f"RAIL_{rail_entry.get('id', len(rail_ops) + 1)}",
                op_type=OperationType.RAIL_BATCH,
                product=rail_entry.get('product'),
                source="Rail",
                target=target,
                volume=rail_entry.get('volume', 0),
                start_time=rail_entry.get('date'),  # Changed from arrival_date
                duration=0.0,  # Will be calculated
            )
            op.duration = op.calculate_duration(
                season=self.scenario.parameters.get('season', 'summer')
            )
            if op.start_time:
                op.end_time = op.start_time + timedelta(hours=op.duration)
            else:
                logger.warning(f"Rail operation {op.op_id} has no start time")
            rail_ops.append(op)
        
        return rail_ops
    
    def _resolve_conflicts(self, operations: List[Operation]) -> List[Operation]:
        """
        Resolve timing conflicts in operation sequence.
        
        Args:
            operations: List of operations that may have conflicts
            
        Returns:
            List of operations with resolved timing
        """
        # Simple conflict resolution: if two operations overlap,
        # push the later one to start after the earlier one ends
        
        if not operations:
            return operations
        
        # Group operations by resource (line, tank, etc.)
        by_resource: Dict[str, List[Operation]] = {}
        
        for op in operations:
            # Determine resource key
            if op.line:
                key = f"line_{op.line}"
            elif op.target and op.target.startswith("RVS"):
                key = f"tank_{op.target}"
            elif op.source and op.source.startswith("RVS"):
                key = f"tank_{op.source}"
            else:
                key = "general"
            
            if key not in by_resource:
                by_resource[key] = []
            by_resource[key].append(op)
        
        # For each resource, ensure no overlaps
        resolved_ops = []
        for resource, ops in by_resource.items():
            ops.sort(key=lambda x: x.start_time if x.start_time else datetime.max)
            
            for i, op in enumerate(ops):
                if i == 0:
                    resolved_ops.append(op)
                    continue
                
                prev_op = ops[i - 1]
                if op.overlaps_with(prev_op):
                    # Push this operation to start after previous ends
                    logger.debug(f"Resolving conflict: {op.op_id} pushed after {prev_op.op_id}")
                    if prev_op.end_time is None:
                        raise ValueError(f"Operation {prev_op.op_id} has no end time")
                    op.update_timing(prev_op.end_time, op.duration)
                
                resolved_ops.append(op)
        
        return sorted(resolved_ops, key=lambda x: x.start_time if x.start_time else datetime.max)
    
    def calculate_balances(self, operations: Optional[List[Operation]] = None) -> Any:
        """
        Calculate tank balances over time using operations sequence.
        
        Args:
            operations: List of operations (uses self.operations if None)
            
        Returns:
            Balance dataframe from TankBalanceCalculator
            
        Raises:
            ValueError: If no scenario or operations available
        """
        if self.scenario is None:
            raise ValueError("No scenario loaded. Call load_scenario() first.")
        
        if operations is None:
            operations = self.operations
        
        if not operations:
            raise ValueError("No operations to calculate balances for.")
        
        logger.info("Calculating tank balances...")
        
        calculator = TankBalanceCalculator(
            tanks=self.scenario.tanks,
            parameters=self.scenario.parameters
        )
        
        # Determine horizon from operations or use default
        if operations:
            horizon_hours = self.scenario.horizon_days * 24
            # Get reference time from first operation
            reference_time = min(
                (op.start_time for op in operations if op.start_time),
                default=datetime.now()
            )
        else:
            horizon_hours = self.scenario.horizon_days * 24
            reference_time = datetime.now()
        
        balances = calculator.simulate(
            operations=operations,
            initial_inventory=self.scenario.current_inventory,
            horizon_hours=horizon_hours,
            reference_time=reference_time
        )
        
        logger.info(f"Balance calculation complete: {len(balances)} time steps")
        self.balances = balances
        return balances
    
    def validate_solution(
        self,
        operations: Optional[List[Operation]] = None,
        balances: Optional[Any] = None
    ) -> ValidationResult:
        """
        Validate the solution for constraint violations.
        
        Args:
            operations: List of operations (uses self.operations if None)
            balances: Balance dataframe (uses self.balances if None)
            
        Returns:
            ValidationResult object with violations and status
            
        Raises:
            ValueError: If no scenario, operations, or balances available
        """
        if self.scenario is None:
            raise ValueError("No scenario loaded. Call load_scenario() first.")
        
        if operations is None:
            operations = self.operations
        
        if balances is None:
            balances = self.balances
        
        if not operations:
            raise ValueError("No operations to validate.")
        
        if balances is None:
            raise ValueError("No balances calculated. Call calculate_balances() first.")
        
        logger.info("Validating solution...")
        
        engine = ValidationEngine(
            scenario=self.scenario,
            operations=operations,
            balances=balances
        )
        
        result = engine.validate_all()
        
        if result.has_errors():
            logger.warning(f"Validation found {len(result.errors)} errors")
            for error in result.errors[:5]:  # Show first 5 errors
                logger.warning(f"  - {error}")
        else:
            logger.info("Validation passed with no errors")
        
        if result.has_warnings():
            logger.info(f"Validation found {len(result.warnings)} warnings")
        
        self.validation_result = result
        return result
    
    def calculate_wagons(self, operations: Optional[List[Operation]] = None) -> Dict[str, Any]:
        """
        Calculate wagon requirements and availability.
        
        Args:
            operations: List of operations (uses self.operations if None)
            
        Returns:
            Dictionary with wagon analysis including:
            - requirements: Wagon needs by time period
            - availability: Available wagons (looping + forecast)
            - gaps: Periods with insufficient wagons
            - cost_estimate: Cost projection
        """
        if self.scenario is None:
            raise ValueError("No scenario loaded. Call load_scenario() first.")
        
        if operations is None:
            operations = self.operations
        
        logger.info("Calculating wagon requirements...")
        
        # Create wagon manager with correct parameters
        wagon_manager = WagonManager(
            total_wagon_fleet=self.scenario.parameters.get('total_wagon_fleet', 500),
            season=self.scenario.parameters.get('season', 'summer'),
            parameters=self.scenario.parameters
        )
        
        # Generate wagon report from operations
        wagon_report = wagon_manager.generate_wagon_report(operations)
        
        # Forecast future availability
        forecaster = WagonForecaster(wagon_manager)
        forecast = forecaster.forecast(days_ahead=self.scenario.horizon_days)
        
        # Build analysis from wagon report
        analysis = {
            "requirements": wagon_report.get("daily_requirements", {}),
            "availability": wagon_report.get("looping_availability", {}),
            "forecast": forecast,
            "gaps": wagon_report.get("gaps", {}),
            "batches": wagon_report.get("batches", []),
            "external_orders": wagon_report.get("external_orders", []),
            "cost_estimate": {
                "total": wagon_report.get("total_external_cost", 0)
            },
            "summary": {
                "total_wagons_needed": sum(
                    sum(wagons for _, wagons in ops)
                    for ops in wagon_report.get("daily_requirements", {}).values()
                ),
                "peak_demand": max(
                    (sum(wagons for _, wagons in ops)
                     for ops in wagon_report.get("daily_requirements", {}).values()),
                    default=0
                ),
                "gap_count": len(wagon_report.get("gaps", {})),
                "estimated_cost": wagon_report.get("total_external_cost", 0),
            },
            "warnings": wagon_report.get("warnings", [])
        }
        
        logger.info(f"Wagon analysis complete:")
        logger.info(f"  Total wagons needed: {analysis['summary']['total_wagons_needed']}")
        logger.info(f"  Peak demand: {analysis['summary']['peak_demand']}")
        logger.info(f"  Gaps identified: {analysis['summary']['gap_count']}")
        
        self.wagon_analysis = analysis
        return analysis
    
    def analyze_risks(
        self,
        operations: Optional[List[Operation]] = None,
        wagon_analysis: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze risks in the solution.
        
        Args:
            operations: List of operations (uses self.operations if None)
            wagon_analysis: Wagon analysis (uses self.wagon_analysis if None)
            
        Returns:
            Dictionary with risk analysis including:
            - critical_points: Time-sensitive operations
            - wagon_risks: Wagon shortage risks
            - capacity_risks: Tank capacity risks
            - recommendations: Mitigation recommendations
        """
        if self.scenario is None:
            raise ValueError("No scenario loaded. Call load_scenario() first.")
        
        if operations is None:
            operations = self.operations
        
        if wagon_analysis is None:
            wagon_analysis = self.wagon_analysis
        
        logger.info("Analyzing risks...")
        
        # Identify critical points
        critical_points = identify_critical_points(
            operations=operations,
            tanks=self.scenario.tanks,
            balances=self.balances
        )
        
        # Analyze sequence risks
        sequence_risks = analyze_sequence_risks(
            operations=operations,
            scenario=self.scenario
        )
        
        # Analyze wagon risks
        wagon_risks = []
        if wagon_analysis and wagon_analysis.get("gaps"):
            for gap in wagon_analysis["gaps"]:
                wagon_risks.append({
                    "type": "wagon_shortage",
                    "severity": "HIGH" if gap.get("shortfall", 0) > 50 else "MEDIUM",
                    "period": gap.get("period"),
                    "shortfall": gap.get("shortfall"),
                    "recommendation": f"Source {gap.get('shortfall')} additional wagons"
                })
        
        # Compile recommendations
        recommendations = []
        
        for cp in critical_points[:5]:  # Top 5 critical points
            recommendations.append({
                "priority": "HIGH",
                "item": f"Monitor {cp.get('op_id')} closely",
                "reason": cp.get("reason", "Critical timing constraint"),
                "action": "Ensure no delays in dependent operations"
            })
        
        for risk in sequence_risks.get("high_severity", [])[:3]:
            recommendations.append({
                "priority": "HIGH",
                "item": risk.get("description"),
                "reason": risk.get("impact"),
                "action": risk.get("mitigation", "Review and adjust schedule")
            })
        
        report = {
            "critical_points": critical_points,
            "sequence_risks": sequence_risks,
            "wagon_risks": wagon_risks,
            "recommendations": recommendations,
            "summary": {
                "critical_count": len(critical_points),
                "high_risk_count": len(wagon_risks) + len(sequence_risks.get("high_severity", [])),
                "medium_risk_count": len(sequence_risks.get("medium_severity", [])),
            }
        }
        
        logger.info(f"Risk analysis complete:")
        logger.info(f"  Critical points: {report['summary']['critical_count']}")
        logger.info(f"  High risks: {report['summary']['high_risk_count']}")
        logger.info(f"  Recommendations: {len(recommendations)}")
        
        self.risk_report = report
        return report

    def run_simulation(self, iterations: int = 50) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation.
        
        Args:
            iterations: Number of iterations
            
        Returns:
            Simulation report dictionary
        """
        if self.scenario is None:
            raise ValueError("No scenario loaded. Call load_scenario() first.")
            
        simulator = MonteCarloSimulator(self.scenario)
        report = simulator.run(iterations)
        
        logger.info("Simulation Complete:")
        logger.info(f"  Success Rate: {report.success_rate:.1f}%")
        logger.info(f"  Confidence: {report.confidence_score:.2f}")
        
        return {
            "iterations": report.iterations,
            "success_rate": report.success_rate,
            "confidence_score": report.confidence_score,
            "avg_conflicts": report.avg_conflicts,
            "recommendations": report.recommendations
        }
    
    def export_results(self, output_path: str) -> str:
        """
        Export all results to Excel file.
        
        Args:
            output_path: Path for output Excel file
            
        Returns:
            Path to generated file
            
        Raises:
            ValueError: If no results to export
        """
        if self.scenario is None:
            raise ValueError("No scenario loaded.")
        
        if not self.operations:
            raise ValueError("No operations to export.")
        
        logger.info(f"Exporting results to: {output_path}")
        
        writer = ExcelWriter(output_path)
        
        # Write operations schedule
        writer.write_operations(self.operations)
        
        # Write tank balances
        if self.balances is not None:
            writer.write_balances(self.balances)
        
        # Write wagon analysis
        if self.wagon_analysis:
            writer.write_wagon_analysis(self.wagon_analysis)
        
        # Write risk report
        if self.risk_report:
            writer.write_risk_report(self.risk_report)
        
        # Write validation results
        if self.validation_result:
            writer.write_validation_results(self.validation_result)
            
        # Add Gantt chart
        writer.add_gantt_chart(self.operations)
        
        writer.save()
        
        logger.info(f"Results exported successfully to: {output_path}")
        return output_path
    
    def run(
        self,
        input_excel: str,
        output_excel: str,
        run_simulation: bool = False,
        run_mode: str = "all",
        vessel_filter: Optional[List[str]] = None,
        optimize_sequence: bool = False
    ) -> Dict[str, Any]:
        """
        Main entry point - run complete optimization workflow.
        
        Args:
            input_excel: Path to input Excel file
            output_excel: Path for output Excel file
            run_simulation: Whether to run Monte Carlo simulation
            run_mode: "all", "palm_only", or "sunflower_only"
            vessel_filter: List of vessel IDs to process
            optimize_sequence: Whether to optimize vessel order
            
        Returns:
            Dictionary with execution summary and results
        """
        logger.info("=" * 80)
        logger.info("STARTING TERMINAL OPTIMIZER")
        logger.info(f"Mode: {run_mode}, Optimize: {optimize_sequence}")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        
        try:
            # Step 1: Load scenario
            scenario = self.load_scenario(input_excel)

            # Step 2: Generate initial sequence
            operations = self.generate_initial_sequence(
                run_mode=run_mode,
                vessel_filter=vessel_filter,
                optimize=optimize_sequence
            )

            # Step 3: Calculate balances
            balances = self.calculate_balances(operations)

            # Step 4: Validate solution
            validation = self.validate_solution(operations, balances)

            if validation.has_errors():
                error_report = "VALIDATION FAILED:\n"
                error_report += "\n".join(f"  ERROR: {e}" for e in validation.errors[:10])
                logger.error(error_report)
                raise ValidationError(f"Solution validation failed with {len(validation.errors)} errors")

            # Step 5: Calculate wagons
            wagon_analysis = self.calculate_wagons(operations)

            # Step 6: Analyze risks
            risks = self.analyze_risks(operations, wagon_analysis)

            # Step 7: Run Simulation if requested
            sim_results = {}
            if run_simulation:
                sim_results = self.run_simulation()

            # Step 8: Export results
            output_file = self.export_results(output_excel)
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Build summary
            summary = {
                "status": "SUCCESS",
                "input_file": input_excel,
                "output_file": output_file,
                "execution_time_seconds": execution_time,
                "scenario_id": scenario.scenario_id,
                "vessels_processed": len(scenario.vessels),
                "operations_generated": len(operations),
                "validation_warnings": len(validation.warnings),
                "critical_points": len(risks["critical_points"]),
                "high_risks": risks["summary"]["high_risk_count"],
                "wagon_gaps": wagon_analysis["summary"]["gap_count"],
                "simulation_confidence": sim_results.get("confidence_score") if sim_results else None
            }

            logger.info("=" * 80)
            logger.info("OPTIMIZATION COMPLETE")
            logger.info(f"  Status: {summary['status']}")
            logger.info(f"  Operations: {summary['operations_generated']}")
            logger.info(f"  Warnings: {summary['validation_warnings']}")
            logger.info(f"  Execution time: {execution_time:.2f}s")
            logger.info(f"  Output: {output_file}")
            logger.info("=" * 80)

            return summary

        except (TerminalOptimizerError, ValidationError, FileNotFoundError, ValueError) as e:
            logger.error(f"OPTIMIZATION FAILED: {str(e)}", exc_info=True)
            raise


class SequenceEditor:
    """
    Handles user edits to the operation sequence.
    
    This class allows users to:
    - Swap operations in the sequence
    - Lock operations to prevent changes
    - Adjust operation timing
    - Recompute balances and validation after edits
    
    Attributes:
        optimizer: Reference to TerminalOptimizer instance
        edit_history: List of edits made to the sequence
    """
    
    def __init__(self, optimizer: TerminalOptimizer):
        """
        Initialize the Sequence Editor.
        
        Args:
            optimizer: TerminalOptimizer instance with loaded scenario and operations
        """
        self.optimizer = optimizer
        self.edit_history: List[Dict[str, Any]] = []
    
    def apply_swap(
        self,
        op_a_id: str,
        op_b_id: str,
        validate: bool = True
    ) -> Tuple[bool, str, List[Operation]]:
        """
        Swap start times of two operations.
        
        Args:
            op_a_id: ID of first operation
            op_b_id: ID of second operation
            validate: Whether to validate after swapping
            
        Returns:
            Tuple of (success, message, updated_operations)
        """
        logger.info(f"Attempting to swap operations: {op_a_id} <-> {op_b_id}")
        
        # Find operations
        op_a = None
        op_b = None
        for op in self.optimizer.operations:
            if op.op_id == op_a_id:
                op_a = op
            if op.op_id == op_b_id:
                op_b = op
        
        if op_a is None:
            return False, f"Operation {op_a_id} not found", self.optimizer.operations
        
        if op_b is None:
            return False, f"Operation {op_b_id} not found", self.optimizer.operations
        
        # Check if operations are locked
        if op_a.user_locked:
            return False, f"Operation {op_a_id} is locked", self.optimizer.operations
        
        if op_b.user_locked:
            return False, f"Operation {op_b_id} is locked", self.optimizer.operations
        
        # Save original times
        orig_a_start = op_a.start_time
        orig_a_duration = op_a.duration
        orig_b_start = op_b.start_time
        orig_b_duration = op_b.duration
        
        # Swap start times
        if orig_b_start is None:
            raise ValueError(f"Operation {op_b_id} has no start time")
        if orig_a_start is None:
            raise ValueError(f"Operation {op_a_id} has no start time")
            
        op_a.update_timing(orig_b_start, orig_a_duration)
        op_b.update_timing(orig_a_start, orig_b_duration)
        
        # Propagate changes to dependent operations
        self._propagate_dependencies(op_a)
        self._propagate_dependencies(op_b)
        
        # Sort operations by new times
        self.optimizer.operations.sort(
            key=lambda x: x.start_time if x.start_time else datetime.max
        )
        
        # Validate if requested
        if validate:
            # Recompute balances
            self.optimizer.calculate_balances()
            
            # Validate
            result = self.optimizer.validate_solution()
            
            if result.has_errors():
                # Swap back if validation fails
                if orig_a_start is None:
                    raise ValueError(f"Operation {op_a_id} has no start time")
                if orig_b_start is None:
                    raise ValueError(f"Operation {op_b_id} has no start time")
                    
                op_a.update_timing(orig_a_start, orig_a_duration)
                op_b.update_timing(orig_b_start, orig_b_duration)
                self._propagate_dependencies(op_a)
                self._propagate_dependencies(op_b)
                
                error_msg = f"Swap rejected: {result.errors[0] if result.errors else 'validation failed'}"
                logger.warning(error_msg)
                return False, error_msg, self.optimizer.operations
        
        # Record edit
        self.edit_history.append({
            "type": "swap",
            "timestamp": datetime.now(),
            "op_a": op_a_id,
            "op_b": op_b_id,
        })
        
        logger.info(f"Swap successful: {op_a_id} <-> {op_b_id}")
        return True, "Swap successful", self.optimizer.operations
    
    def apply_lock(self, op_id: str) -> Tuple[bool, str]:
        """
        Lock an operation to prevent modifications.
        
        Args:
            op_id: ID of operation to lock
            
        Returns:
            Tuple of (success, message)
        """
        logger.info(f"Locking operation: {op_id}")
        
        for op in self.optimizer.operations:
            if op.op_id == op_id:
                op.user_locked = True
                
                # Record edit
                self.edit_history.append({
                    "type": "lock",
                    "timestamp": datetime.now(),
                    "op_id": op_id,
                })
                
                logger.info(f"Operation locked: {op_id}")
                return True, f"Operation {op_id} locked successfully"
        
        return False, f"Operation {op_id} not found"
    
    def apply_time_adjustment(
        self,
        op_id: str,
        new_start_time: datetime,
        validate: bool = True
    ) -> Tuple[bool, str, List[Operation]]:
        """
        Adjust the start time of an operation.
        
        Args:
            op_id: ID of operation to adjust
            new_start_time: New start time
            validate: Whether to validate after adjustment
            
        Returns:
            Tuple of (success, message, updated_operations)
        """
        logger.info(f"Adjusting operation {op_id} to start at {new_start_time}")
        
        # Find operation
        operation = None
        for op in self.optimizer.operations:
            if op.op_id == op_id:
                operation = op
                break
        
        if operation is None:
            return False, f"Operation {op_id} not found", self.optimizer.operations
        
        if operation.user_locked:
            return False, f"Operation {op_id} is locked", self.optimizer.operations
        
        # Save original time
        orig_start = operation.start_time
        orig_duration = operation.duration
        
        # Update timing
        operation.update_timing(new_start_time, orig_duration)
        
        # Propagate to dependents
        self._propagate_dependencies(operation)
        
        # Sort operations
        self.optimizer.operations.sort(
            key=lambda x: x.start_time if x.start_time else datetime.max
        )
        
        # Validate if requested
        if validate:
            self.optimizer.calculate_balances()
            result = self.optimizer.validate_solution()
            
            if result.has_errors():
                # Revert if validation fails
                if orig_start is None:
                    raise ValueError(f"Operation {op_id} has no start time")
                operation.update_timing(orig_start, orig_duration)
                self._propagate_dependencies(operation)
                
                error_msg = f"Adjustment rejected: {result.errors[0] if result.errors else 'validation failed'}"
                logger.warning(error_msg)
                return False, error_msg, self.optimizer.operations
        
        # Record edit
        self.edit_history.append({
            "type": "time_adjustment",
            "timestamp": datetime.now(),
            "op_id": op_id,
            "old_start": orig_start,
            "new_start": new_start_time,
        })
        
        logger.info(f"Time adjustment successful for {op_id}")
        return True, "Time adjustment successful", self.optimizer.operations
    
    def _propagate_dependencies(self, operation: Operation) -> None:
        """
        Propagate timing changes to dependent operations.
        
        Args:
            operation: Operation that was modified
        """
        # Find operations that depend on this one
        for op in self.optimizer.operations:
            if operation.op_id in op.dependencies:
                # Ensure dependent starts after this operation ends
                if op.start_time is None or operation.end_time is None:
                    continue
                    
                if op.start_time < operation.end_time:
                    logger.debug(f"Propagating: {op.op_id} pushed to {operation.end_time}")
                    op.update_timing(operation.end_time, op.duration)
                    # Recursively propagate
                    self._propagate_dependencies(op)
    
    def recompute(self) -> Dict[str, Any]:
        """
        Recompute balances, validation, and wagon analysis after edits.
        
        Returns:
            Dictionary with updated results
        """
        logger.info("Recomputing solution after edits...")
        
        # Recalculate balances
        balances = self.optimizer.calculate_balances()
        
        # Revalidate
        validation = self.optimizer.validate_solution()
        
        # Recalculate wagon analysis
        wagon_analysis = self.optimizer.calculate_wagons()
        
        # Re-analyze risks
        risks = self.optimizer.analyze_risks()
        
        results = {
            "balances_updated": True,
            "validation": {
                "errors": len(validation.errors),
                "warnings": len(validation.warnings),
            },
            "wagon_gaps": wagon_analysis["summary"]["gap_count"],
            "critical_points": len(risks["critical_points"]),
        }
        
        logger.info("Recompute complete")
        return results


def main():
    """
    Command-line entry point for Terminal Optimizer.
    
    Usage:
        python -m terminal_optimizer.main <input_file.xlsx> [output_file.xlsx]
    """
    import sys
    from pathlib import Path
    
    # Check arguments
    if len(sys.argv) < 2:
        print("Usage: python -m terminal_optimizer.main <input_file.xlsx> [output_file.xlsx] [options]")
        print()
        print("Arguments:")
        print("  input_file.xlsx   - Path to input Excel file")
        print("  output_file.xlsx  - (Optional) Path for output file")
        print()
        print("Options:")
        print("  --simulate        - Run Monte Carlo simulation")
        print("  --mode <mode>     - Run mode: all, palm_only, sunflower_only")
        print("  --optimize        - Optimize vessel sequence")
        print("  --vessel <id>     - Run for specific vessel ID")
        sys.exit(1)
    
    # Parse arguments manually
    args = sys.argv[1:]
    
    run_sim = False
    if "--simulate" in args:
        run_sim = True
        args.remove("--simulate")
        
    optimize = False
    if "--optimize" in args:
        optimize = True
        args.remove("--optimize")
        
    run_mode = "all"
    if "--mode" in args:
        idx = args.index("--mode")
        if idx + 1 < len(args):
            run_mode = args[idx + 1]
            args.pop(idx) # remove value
            args.pop(idx) # remove flag
            
    vessel_filter = None
    if "--vessel" in args:
        idx = args.index("--vessel")
        if idx + 1 < len(args):
            vessel_filter = [args[idx + 1]]
            args.pop(idx)
            args.pop(idx)
            
    # Handle VBA arguments
    input_file = None
    if "--excel" in args:
        idx = args.index("--excel")
        if idx + 1 < len(args):
            input_file = args[idx + 1]
            args.pop(idx)
            args.pop(idx)
            
    # Handle --output-excel flag (ignore it, just ensures we use default output logic if not specified)
    if "--output-excel" in args:
        args.remove("--output-excel")
        
    if not input_file:
        if not args:
            print("ERROR: Missing input file")
            sys.exit(1)
        input_file = args[0]
    
    # Determine output file
    if len(args) >= 2 and not args[1].startswith("--") and args[0] == input_file:
        output_file = args[1]
    elif len(args) >= 1 and not args[0].startswith("--") and args[0] != input_file:
        # Case where input_file was parsed from --excel, so args[0] might be output
        output_file = args[0]
    else:
        input_path = Path(input_file)
        output_file = str(input_path.parent / f"{input_path.stem}_optimized{input_path.suffix}")
    
    # Check input file exists
    if not Path(input_file).exists():
        print(f"ERROR: Input file not found: {input_file}")
        sys.exit(1)
    
    print()
    print("=" * 80)
    print("  TERMINAL OPTIMIZER - Оптимизатор Операций Нефтяного Терминала")
    print("=" * 80)
    print()
    print(f"Input:    {input_file}")
    print(f"Output:   {output_file}")
    print(f"Mode:     {run_mode}")
    print(f"Optimize: {optimize}")
    if vessel_filter:
        print(f"Vessel:   {vessel_filter[0]}")
    print()
    
    # Run optimization
    try:
        optimizer = TerminalOptimizer()
        summary = optimizer.run(
            input_file,
            output_file,
            run_simulation=run_sim,
            run_mode=run_mode,
            vessel_filter=vessel_filter,
            optimize_sequence=optimize
        )

        print()
        print("=" * 80)
        print("РЕЗУЛЬТАТЫ / RESULTS")
        print("=" * 80)
        print(f"Статус:           {summary['status']}")
        print(f"Операций:         {summary['operations_generated']}")
        print(f"Предупреждений:   {summary['validation_warnings']}")
        print(f"Критич. точек:    {summary['critical_points']}")
        print(f"Высоких рисков:   {summary['high_risks']}")
        print(f"Время выполнения: {summary['execution_time_seconds']:.2f} сек")
        print()
        print(f"Результаты сохранены в: {output_file}")
        print("=" * 80)
        print()

        return 0

    except (TerminalOptimizerError, ValidationError, FileNotFoundError, ValueError, OSError) as e:
        print()
        print("=" * 80)
        print("ОШИБКА / ERROR")
        print("=" * 80)
        print(f"{str(e)}")
        print()
        print("Проверьте лог-файл в папке logs/ для подробностей")
        print("=" * 80)
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
