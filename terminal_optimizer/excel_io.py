"""
Excel I/O Module

This module handles reading input data from Excel and writing results to Excel.

Classes:
    ExcelReader: Reads scenario data from Excel workbooks
    ExcelWriter: Writes calculation results to Excel format
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import csv
import os
import re
from pathlib import Path
import pandas as pd
from dateutil import parser

from terminal_optimizer.domain_models import (
    Tank, Vessel, Operation, Scenario, CargoType, OperationType, create_standard_tanks
)
from terminal_optimizer.visualization import ExcelGanttChart
from terminal_optimizer.exceptions import ExcelFileError, InvalidDataError
from terminal_optimizer.utils import (
    parse_datetime, validate_excel_file, validate_vessels_data,
    validate_inventory_data, validate_rail_data, validate_demand_data
)


class ExcelReader:
    """
    Reads scenario data from Excel/CSV files.
    
    Supports reading:
    - Vessel schedules
    - Cargo plans for palm vessels
    - Rail delivery schedules
    - Current inventory states
    - Client demand matrices
    """
    
    @staticmethod
    def read_vessels(filepath: str) -> List[Vessel]:
        """
        Read vessel information from CSV file.
        
        Expected columns:
        - vessel_id: Vessel identifier
        - eta: Expected arrival (ISO format preferred, DD.MM.YYYY HH:MM supported)
        - cargo_type: "sunflower" or "palm"
        - total_volume: Total cargo in tonnes
        - demurrage_rate: Cost per hour (optional, default 100000)
        - strategic_weight: Priority multiplier (optional, default 1.0)
        
        Args:
            filepath: Path to vessels CSV file
            
        Returns:
            List of Vessel objects
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If data is invalid
        """
        vessels = []
        path = Path(filepath)

        if not path.exists():
            raise FileNotFoundError(f"Vessels file not found: {filepath}")

        try:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row_num, row in enumerate(reader, start=2):  # Start from 2 (header is row 1)
                    try:
                        vessel_id = row.get('vessel_id', '').strip()
                        if not vessel_id:
                            continue  # Skip empty rows

                        # Parse ETA
                        eta_str = row.get('eta', '').strip()
                        eta = parse_datetime(eta_str)

                        # Parse cargo type
                        cargo_type_str = row.get('cargo_type', 'sunflower').strip().lower()
                        cargo_type = CargoType(cargo_type_str)

                        # Parse volume
                        total_volume = float(row.get('total_volume', 0))

                        # Optional fields
                        demurrage_rate = float(row.get('demurrage_rate', 100000))
                        strategic_weight = float(row.get('strategic_weight', 1.0))
                        notes = row.get('notes', '').strip()
                        
                        # Parse active status
                        active_str = str(row.get('active', 'Yes')).strip().lower()
                        is_active = active_str in ['yes', 'true', '1', 'y']

                        vessel = Vessel(
                            vessel_id=vessel_id,
                            eta=eta,
                            cargo_type=cargo_type,
                            total_volume=total_volume,
                            demurrage_rate=demurrage_rate,
                            strategic_weight=strategic_weight,
                            notes=notes,
                            is_active=is_active
                        )
                        vessels.append(vessel)

                    except (ValueError, TypeError, KeyError) as e:
                        raise InvalidDataError(
                            f"Error reading vessels file row {row_num}: {e}\n"
                            f"Row data: {row}"
                        )
        except (OSError, UnicodeDecodeError, csv.Error) as e:
            raise ExcelFileError(f"Failed to read vessels CSV file: {e}")
        
        return vessels
    
    @staticmethod
    def read_cargo_plan(filepath: str, vessel_id: str) -> Dict[str, Tuple[str, float]]:
        """
        Read cargo plan for a specific palm vessel.
        
        Expected columns:
        - vessel_id: Vessel identifier
        - hold_id: Hold identifier (H1, H2, etc.)
        - fraction: Palm fraction name
        - volume: Volume in tonnes
        
        Args:
            filepath: Path to cargo plan CSV file
            vessel_id: Vessel to read plan for
            
        Returns:
            Dict mapping hold_id to (fraction, volume)
        """
        cargo_plan = {}
        path = Path(filepath)
        
        if not path.exists():
            # Not an error - not all vessels have cargo plans
            return cargo_plan
        
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                row_vessel = row.get('vessel_id', '').strip()
                if row_vessel != vessel_id:
                    continue
                
                hold_id = row.get('hold_id', '').strip()
                fraction = row.get('fraction', '').strip()
                volume = float(row.get('volume', 0))
                
                if hold_id and fraction and volume > 0:
                    cargo_plan[hold_id] = (fraction, volume)
        
        return cargo_plan
    
    @staticmethod
    def read_rail_schedule(filepath: str) -> List[Dict[str, Any]]:
        """
        Read railway delivery schedule.
        
        Expected columns:
        - date: Delivery date
        - product: Product name
        - volume: Volume in tonnes
        - wagons: Number of wagons (optional)
        
        Args:
            filepath: Path to rail schedule CSV file
            
        Returns:
            List of rail delivery dictionaries
        """
        schedule = []
        path = Path(filepath)
        
        if not path.exists():
            return schedule  # Empty schedule if file missing
        
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                date_str = row.get('date', '').strip()
                if not date_str:
                    continue
                
                delivery_date = parse_datetime(date_str)
                product = row.get('product', 'sunflower').strip()
                volume = float(row.get('volume', 0))
                wagons = int(row.get('wagons', 0)) if row.get('wagons') else None
                
                schedule.append({
                    'date': delivery_date,
                    'product': product,
                    'volume': volume,
                    'wagons': wagons
                })
        
        return schedule
    
    @staticmethod
    def read_inventory(filepath: str) -> Dict[str, Dict[str, Any]]:
        """
        Read current tank inventory.
        
        Expected columns:
        - tank_id: Tank identifier
        - current_product: Product currently in tank (or empty)
        - current_volume: Current volume in tonnes
        - temperature: Current temperature (optional)
        
        Args:
            filepath: Path to inventory CSV file
            
        Returns:
            Dict mapping tank_id to inventory state
        """
        inventory = {}
        path = Path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"Inventory file not found: {filepath}")
        
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                tank_id = row.get('tank_id', '').strip().replace("-", "_")
                if not tank_id:
                    continue
                
                product = row.get('current_product', '').strip()
                if product.lower() in ['', 'empty', 'none']:
                    product = None
                
                volume = float(row.get('current_volume', 0))
                temp = row.get('temperature')
                temperature = float(temp) if temp and temp.strip() else None
                
                inventory[tank_id] = {
                    'current_product': product,
                    'current_volume': volume,
                    'temperature': temperature
                }
        
        return inventory
    
    @staticmethod
    def read_demand(filepath: str) -> Dict[str, Dict[str, Any]]:
        """
        Read client demand matrix.
        
        Expected columns:
        - week: Week number or date
        - client: Client name
        - product: Product name
        - volume: Demanded volume in tonnes
        - priority: Priority level (HIGH/MEDIUM/LOW)
        
        Args:
            filepath: Path to demand CSV file
            
        Returns:
            Nested dict structure for demand
        """
        demand = {}
        path = Path(filepath)
        
        if not path.exists():
            return demand  # Empty demand if file missing
        
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                week = row.get('week', '').strip()
                client = row.get('client', '').strip()
                product = row.get('product', '').strip()
                volume = float(row.get('volume', 0))
                priority = row.get('priority', 'MEDIUM').strip()
                
                if week not in demand:
                    demand[week] = {}
                
                if client not in demand[week]:
                    demand[week][client] = {}
                
                demand[week][client][product] = {
                    'volume': volume,
                    'priority': priority
                }
        
        return demand
    
    @staticmethod
    def load_scenario(
        vessels_file: str,
        inventory_file: str,
        scenario_id: str = "scenario_1",
        cargo_plan_file: Optional[str] = None,
        rail_schedule_file: Optional[str] = None,
        demand_file: Optional[str] = None
    ) -> Scenario:
        """
        Load complete scenario from multiple CSV files.
        
        Args:
            vessels_file: Path to vessels CSV
            inventory_file: Path to inventory CSV
            scenario_id: Scenario identifier
            cargo_plan_file: Optional path to cargo plans CSV
            rail_schedule_file: Optional path to rail schedule CSV
            demand_file: Optional path to demand CSV
            
        Returns:
            Fully populated Scenario object
        """
        # Read vessels
        vessels = ExcelReader.read_vessels(vessels_file)
        
        # Read cargo plans for palm vessels
        if cargo_plan_file:
            for vessel in vessels:
                if vessel.cargo_type == CargoType.PALM:
                    cargo_plan = ExcelReader.read_cargo_plan(cargo_plan_file, vessel.vessel_id)
                    vessel.cargo_plan = cargo_plan
        
        # Read inventory
        inventory = ExcelReader.read_inventory(inventory_file)
        
        # Read optional files
        rail_schedule = []
        if rail_schedule_file:
            rail_schedule = ExcelReader.read_rail_schedule(rail_schedule_file)
        
        demand = {}
        if demand_file:
            demand = ExcelReader.read_demand(demand_file)
        
        # Create standard tanks
        tanks = create_standard_tanks()
        
        # Update tank states from inventory
        for tank_id, inv in inventory.items():
            if tank_id in tanks:
                tanks[tank_id].current_product = inv.get('current_product')
                tanks[tank_id].current_volume = inv.get('current_volume', 0.0)
                tanks[tank_id].temperature = inv.get('temperature')
        
        # Create scenario
        scenario = Scenario(
            scenario_id=scenario_id,
            vessels=vessels,
            tanks=tanks,
            rail_schedule=rail_schedule,
            current_inventory=inventory,
            client_demand=demand
        )
        
        return scenario
    
    @staticmethod
    def read_from_excel(filepath: str) -> Scenario:
        """
        Load complete scenario from a single Excel file with multiple sheets.
        
        Expected sheets:
        - Input_Vessels
        - Input_CargoPlan
        - Input_CurrentState
        - Input_Rail (optional)
        - Input_Demand (optional)
        
        Args:
            filepath: Path to Excel file
            
        Returns:
            Fully populated Scenario object
        """
        path = validate_excel_file(filepath)
             
        # Read all sheets
        try:
            xls = pd.ExcelFile(path)
        except (FileNotFoundError, PermissionError, pd.errors.EmptyDataError, OSError) as e:
            raise ExcelFileError(f"Failed to open Excel file: {e}")
            
        # 1. Read Vessels
        if "Input_Vessels" not in xls.sheet_names:
            raise ValueError("Sheet 'Input_Vessels' not found in Excel file")
            
        df_vessels = pd.read_excel(xls, "Input_Vessels")
        validate_vessels_data(df_vessels)
         
        # Collect vessel IDs for cargo plan validation
        vessel_ids = []
        for _, row in df_vessels.iterrows():
            if not pd.isna(row.get("VesselID")):
                vessel_ids.append(str(row["VesselID"]).strip())
         
        vessels = []
        
        for _, row in df_vessels.iterrows():
            # Skip empty rows or example rows
            if pd.isna(row.get("VesselID")):
                continue
                
            vessel_id = str(row["VesselID"]).strip()
            
            # Parse ETA
            eta_val = row.get("ETA")
            if isinstance(eta_val, datetime):
                # Ensure timezone-naive datetime
                eta = eta_val.replace(tzinfo=None) if eta_val.tzinfo else eta_val
            else:
                eta = parse_datetime(str(eta_val))
                
            cargo_type_str = str(row.get("CargoType", "sunflower")).strip().lower()
            cargo_type = CargoType(cargo_type_str)
            
            total_volume = float(row.get("TotalVolume", 0))
            demurrage_rate = float(row.get("DemurrageRate", 100000))
            
            # Parse priority/strategic weight
            priority = str(row.get("Priority", "MEDIUM")).upper()
            strategic_weight = 2.0 if priority == "HIGH" else (0.5 if priority == "LOW" else 1.0)
            
            notes = str(row.get("Notes", "")) if not pd.isna(row.get("Notes")) else ""
            
            # Parse active status
            active_val = row.get("Active", "Yes")
            if pd.isna(active_val):
                active_val = "Yes"
            is_active = str(active_val).strip().lower() in ['yes', 'true', '1', 'y']
            
            vessel = Vessel(
                vessel_id=vessel_id,
                eta=eta,
                cargo_type=cargo_type,
                total_volume=total_volume,
                demurrage_rate=demurrage_rate,
                strategic_weight=strategic_weight,
                notes=notes,
                is_active=is_active
            )
            vessels.append(vessel)
            
        # 2. Read Cargo Plans
        if "Input_CargoPlan" in xls.sheet_names:
            df_cargo = pd.read_excel(xls, "Input_CargoPlan")
            
            for vessel in vessels:
                if vessel.cargo_type == CargoType.PALM:
                    vessel_cargo = df_cargo[df_cargo["VesselID"] == vessel.vessel_id]
                    
                    cargo_plan = {}
                    for _, row in vessel_cargo.iterrows():
                        if pd.isna(row.get("Hold")):
                            continue
                            
                        hold_id = str(row["Hold"]).strip()
                        fraction = str(row["Fraction"]).strip()
                        volume = float(row["Volume"])
                        
                        if hold_id and fraction and volume > 0:
                            cargo_plan[hold_id] = (fraction, volume)
                            
                    vessel.cargo_plan = cargo_plan

        # 3. Read Inventory (Current State)
        inventory = {}
        if "Input_CurrentState" in xls.sheet_names:
            df_state = pd.read_excel(xls, "Input_CurrentState")
             
            validate_inventory_data(df_state)
             
            for _, row in df_state.iterrows():
                if pd.isna(row.get("TankID")):
                    continue
                    
                tank_id = str(row["TankID"]).strip().replace("-", "_")
                
                product = row.get("CurrentProduct")
                if pd.isna(product) or str(product).strip() in ["-", "empty", "none", ""]:
                    product = None
                else:
                    product = str(product).strip()
                    
                volume = float(row.get("CurrentVolume", 0))
                
                inventory[tank_id] = {
                    "current_product": product,
                    "current_volume": volume,
                    "temperature": None
                }

        # 4. Read Rail Schedule
        rail_schedule = []
        if "Input_Rail" in xls.sheet_names:
            df_rail = pd.read_excel(xls, "Input_Rail")
             
            validate_rail_data(df_rail)
             
            for _, row in df_rail.iterrows():
                if pd.isna(row.get("Date")):
                    continue
                    
                date_val = row["Date"]
                if isinstance(date_val, datetime):
                    # Ensure timezone-naive datetime
                    delivery_date = date_val.replace(tzinfo=None) if date_val.tzinfo else date_val
                else:
                    delivery_date = parse_datetime(str(date_val))
                    
                product = str(row.get("Product", "sunflower")).strip()
                volume = float(row.get("Volume", 0))
                batches = int(row.get("Batches", 0)) if not pd.isna(row.get("Batches")) else None
                
                rail_schedule.append({
                    "date": delivery_date,
                    "product": product,
                    "volume": volume,
                    "wagons": None,
                    "batches": batches
                })

        # 5. Read Demand
        demand = {}
        if "Input_Demand" in xls.sheet_names:
            df_demand = pd.read_excel(xls, "Input_Demand")
             
            validate_demand_data(df_demand)
             
            for _, row in df_demand.iterrows():
                if pd.isna(row.get("Week")):
                    continue
                    
                week = str(row["Week"]).strip()
                client = str(row.get("Client", "")).strip()
                product = str(row.get("Product", "")).strip()
                volume = float(row.get("Volume", 0))
                priority = str(row.get("Priority", "MEDIUM")).strip()
                
                if week not in demand:
                    demand[week] = {}
                if client not in demand[week]:
                    demand[week][client] = {}
                    
                demand[week][client][product] = {
                    "volume": volume,
                    "priority": priority
                }

        # Create standard tanks
        tanks = create_standard_tanks()
        
        # Update tank states from inventory
        for tank_id, inv in inventory.items():
            if tank_id in tanks:
                tanks[tank_id].current_product = inv.get("current_product")
                tanks[tank_id].current_volume = inv.get("current_volume", 0.0)

        # Create scenario
        scenario = Scenario(
            scenario_id=path.stem,
            vessels=vessels,
            tanks=tanks,
            rail_schedule=rail_schedule,
            current_inventory=inventory,
            client_demand=demand
        )
        
        return scenario



class ExcelWriter:
    """
    Writes calculation results to Excel file.
    """
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.writer = pd.ExcelWriter(filepath, engine='openpyxl')
        
    def write_operations(self, operations: List[Operation]) -> None:
        """Write operations timeline."""
        data = []
        for op in operations:
            row = {
                'Operation ID': op.op_id,
                'Vessel ID': op.vessel_id,
                'Type': op.op_type.value,
                'Product': op.product,
                'Source': op.source,
                'Target': op.target,
                'Volume (t)': op.volume,
                'Start Time': op.start_time,
                'Duration (h)': op.duration,
                'End Time': op.end_time,
                'Line': op.line,
                'Wagons': op.wagons,
                'Locked': 'Yes' if op.user_locked else 'No',
                'Notes': op.notes
            }
            data.append(row)
            
        df = pd.DataFrame(data)
        df.to_excel(self.writer, sheet_name='Output_Operations', index=False)
        
    def write_balances(self, balances: Any) -> None:
        """Write tank balances."""
        # balances is expected to be a DataFrame
        if hasattr(balances, 'to_excel'):
            balances.to_excel(self.writer, sheet_name='Output_TankBalance')
            
    def write_wagon_analysis(self, wagon_analysis: Dict[str, Any]) -> None:
        """Write wagon analysis."""
        # Summary
        summary = wagon_analysis.get('summary', {})
        pd.DataFrame([summary]).to_excel(self.writer, sheet_name='Output_RailSchedule', index=False)
        
        # Daily requirements
        daily_reqs = wagon_analysis.get('requirements', {})
        daily_data = []
        for day, ops in daily_reqs.items():
            total = sum(w for _, w in ops)
            op_ids = ', '.join(op.op_id for op, _ in ops)
            daily_data.append({'Date': day, 'Total Wagons': total, 'Operations': op_ids})
        
        if daily_data:
            pd.DataFrame(daily_data).to_excel(self.writer, sheet_name='Output_RailDaily', index=False)
            
    def write_risk_report(self, risk_report: Dict[str, Any]) -> None:
        """Write risk analysis report."""
        # Critical points
        critical = risk_report.get('critical_points', [])
        if critical:
            pd.DataFrame(critical).to_excel(self.writer, sheet_name='Output_Warnings', index=False)
            
        # Recommendations
        recs = risk_report.get('recommendations', [])
        if recs:
            pd.DataFrame(recs).to_excel(self.writer, sheet_name='Output_Recommendations', index=False)
            
    def write_validation_results(self, validation_result: Any) -> None:
        """Write validation results."""
        # Assuming validation_result has errors and warnings lists
        data = []
        for err in getattr(validation_result, 'errors', []):
            data.append({'Type': 'Error', 'Message': str(err)})
        for warn in getattr(validation_result, 'warnings', []):
            data.append({'Type': 'Warning', 'Message': str(warn)})
            
        if data:
            pd.DataFrame(data).to_excel(self.writer, sheet_name='Output_Validation', index=False)
            
    def add_gantt_chart(self, operations: List[Operation]) -> None:
        """Add Gantt chart to the workbook."""
        gantt = ExcelGanttChart(self.writer)
        gantt.create_chart(operations)

    def save(self) -> None:
        """Save the workbook."""
        self.writer.close()
