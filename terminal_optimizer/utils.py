"""
Utility Functions for Terminal Optimizer

This module contains common utility functions used across the terminal optimizer,
including date parsing and input validation.

Functions:
    parse_datetime: Parse datetime from various string formats
    validate_excel_file: Validate Excel file path and properties
    validate_vessels_data: Validate vessels sheet data
    validate_inventory_data: Validate inventory sheet data
    validate_rail_data: Validate rail schedule sheet data
    validate_demand_data: Validate demand sheet data
"""

from __future__ import annotations
from datetime import datetime
from typing import List
from pathlib import Path
import locale
import pandas as pd
from dateutil import parser

from terminal_optimizer.exceptions import InvalidDataError


def parse_datetime(date_str: str) -> datetime:
    """
    Parse datetime from various formats with ISO format standardization and locale-aware handling.

    Priority order:
    1. ISO format: 2025-01-15T14:30:00 or 2025-01-15 (strict parsing)
    2. Fallback to locale-aware parsing for other formats

    For ambiguous dates in fallback parsing:
    - '.' separator assumes day-first (European format)
    - '/' separator assumes month-first (US format)
    - Other formats use improved system locale detection

    Args:
        date_str: Date string to parse

    Returns:
        Parsed datetime (timezone-naive)

    Raises:
        ValueError: If date cannot be parsed
    """
    date_str = date_str.strip()
    if not date_str:
        raise ValueError("Empty date string")

    # 1. First try strict ISO format parsing
    try:
        # Handle ISO format with 'T' separator
        if 'T' in date_str:
            return datetime.fromisoformat(date_str)
        # Handle ISO date only
        elif date_str.count('-') == 2 and date_str.replace('-', '').isdigit():
            return datetime.fromisoformat(date_str)
    except ValueError:
        pass  # Fall through to locale-aware parsing

    # 2. Fallback to locale-aware parsing
    # Determine default dayfirst based on improved system locale detection
    default_dayfirst = _detect_locale_dayfirst()

    # Detect format based on separator
    if '.' in date_str:
        dayfirst = True  # European format (DD.MM.YYYY)
    elif '/' in date_str:
        dayfirst = False  # US format (MM/DD/YYYY)
    else:
        dayfirst = default_dayfirst  # Use locale-based default

    try:
        parsed_dt = parser.parse(date_str, dayfirst=dayfirst)
        # Ensure timezone-naive (remove timezone if present)
        if parsed_dt.tzinfo is not None:
            parsed_dt = parsed_dt.replace(tzinfo=None)
        return parsed_dt
    except (ValueError, TypeError, OverflowError) as e:
        raise ValueError(f"Unable to parse date: {date_str}. Please use ISO format (YYYY-MM-DDTHH:MM:SS) for best compatibility. Error: {e}")


def _detect_locale_dayfirst() -> bool:
    """
    Detect if the system locale prefers day-first date format.

    Returns:
        True if day-first (European style), False if month-first (US style)
    """
    try:
        # Try multiple methods to detect locale
        loc = None

        # Method 1: locale.getlocale()
        try:
            loc = locale.getlocale()[0]
        except:
            pass

        # Method 2: locale.getdefaultlocale()
        if not loc:
            try:
                loc = locale.getdefaultlocale()[0]
            except:
                pass

        # Method 3: LC_TIME category specifically
        if not loc:
            try:
                loc = locale.getlocale(locale.LC_TIME)[0]
            except:
                pass

        if loc:
            # Comprehensive list of day-first locales
            day_first_locales = {
                # European countries
                'de', 'fr', 'es', 'it', 'pt', 'ru', 'pl', 'cs', 'sk', 'hu', 'hr', 'sl',
                'bg', 'ro', 'tr', 'el', 'nl', 'da', 'sv', 'no', 'fi', 'et', 'lv', 'lt',
                'uk', 'be', 'sr', 'mk', 'bs', 'me', 'sq', 'is', 'mt', 'ga', 'cy', 'gd',
                # Middle East and North Africa
                'ar', 'he', 'fa', 'ur', 'hi', 'bn', 'pa', 'gu', 'or', 'ta', 'te', 'kn', 'ml',
                # East Asia (some use day-first)
                'zh', 'ja', 'ko',
                # Other
                'th', 'lo', 'km', 'my'
            }

            # Check if locale starts with any day-first prefix
            loc_lower = loc.lower()
            if any(loc_lower.startswith(prefix) for prefix in day_first_locales):
                return True

        # Default to month-first (US style) if locale detection fails
        return False

    except Exception:
        # If all locale detection fails, default to month-first
        return False


def validate_excel_file(filepath: str) -> Path:
    """Validate Excel file path, extension, and size."""
    # Sanitize path
    path = Path(filepath).resolve()
    # Check for dangerous path traversal
    if '..' in path.parts or not path.is_absolute():
        raise ValueError(f"Invalid file path: {filepath}")
    # Check extension
    if path.suffix.lower() not in ['.xlsx', '.xlsm', '.xls']:
        raise ValueError(f"Invalid file extension. Expected .xlsx, .xlsm, or .xls, got {path.suffix}")
    # Check file exists
    if not path.exists():
        raise FileNotFoundError(f"Excel file not found: {filepath}")
    # Check file size (max 50MB)
    max_size = 50 * 1024 * 1024  # 50MB
    if path.stat().st_size > max_size:
        raise ValueError(f"File too large: {path.stat().st_size} bytes. Maximum allowed: {max_size} bytes")
    # Check for malicious content (basic check for macros)
    if path.suffix.lower() == '.xlsm':
        import warnings
        warnings.warn("Excel file contains macros (.xlsm). Ensure the file is from a trusted source.", UserWarning)
    return path


def validate_vessels_data(df: pd.DataFrame) -> None:
    """Validate vessels sheet data."""
    required_columns = ['VesselID', 'ETA', 'CargoType', 'TotalVolume']
    for col in required_columns:
        if col not in df.columns:
            raise InvalidDataError(f"Required column '{col}' missing from vessels sheet")
    for idx, row in df.iterrows():
        if pd.isna(row.get("VesselID")):
            continue  # Skip empty rows
        vessel_id = str(row["VesselID"]).strip()
        if not vessel_id:
            raise InvalidDataError(f"Empty VesselID in row {int(idx)+2}")
        # Validate ETA
        eta_val = row.get("ETA")
        if pd.isna(eta_val):
            raise InvalidDataError(f"Missing ETA for vessel {vessel_id}")
        if not isinstance(eta_val, datetime):
            try:
                parse_datetime(str(eta_val))
            except ValueError as e:
                raise InvalidDataError(f"Invalid ETA for vessel {vessel_id}: {e}")
        # Validate CargoType
        cargo_type_str = str(row.get("CargoType", "sunflower")).strip().lower()
        if cargo_type_str not in ['sunflower', 'palm']:
            raise InvalidDataError(f"Invalid cargo type for vessel {vessel_id}: {cargo_type_str}")
        # Validate TotalVolume
        try:
            total_volume = float(row.get("TotalVolume", 0))
            if total_volume < 0:
                raise InvalidDataError(f"Negative total volume for vessel {vessel_id}: {total_volume}")
            if total_volume > 100000:  # Reasonable max
                raise InvalidDataError(f"Unreasonably large total volume for vessel {vessel_id}: {total_volume}")
        except (ValueError, TypeError):
            raise InvalidDataError(f"Invalid total volume for vessel {vessel_id}: {row.get('TotalVolume')}")
        # Validate DemurrageRate
        try:
            demurrage_rate = float(row.get("DemurrageRate", 100000))
            if demurrage_rate < 0:
                raise InvalidDataError(f"Negative demurrage rate for vessel {vessel_id}: {demurrage_rate}")
        except (ValueError, TypeError):
            raise InvalidDataError(f"Invalid demurrage rate for vessel {vessel_id}: {row.get('DemurrageRate')}")


def validate_inventory_data(df: pd.DataFrame) -> None:
    """Validate inventory sheet data."""
    if df.empty:
        return
    required_columns = ['TankID', 'CurrentProduct', 'CurrentVolume']
    for col in required_columns:
        if col not in df.columns:
            raise InvalidDataError(f"Required column '{col}' missing from inventory sheet")
    for idx, row in df.iterrows():
        tank_id = str(row.get("TankID", "")).strip()
        if not tank_id:
            raise InvalidDataError(f"Empty TankID in inventory row {int(idx)+2}")
        # Product can be None or string
        product = row.get("CurrentProduct")
        if not pd.isna(product) and not isinstance(product, str):
            raise InvalidDataError(f"Invalid product type for tank {tank_id}: {type(product)}")
        try:
            volume = float(row.get("CurrentVolume", 0))
            if volume < 0:
                raise InvalidDataError(f"Negative volume for tank {tank_id}: {volume}")
        except (ValueError, TypeError):
            raise InvalidDataError(f"Invalid volume for tank {tank_id}: {row.get('CurrentVolume')}")


def validate_rail_data(df: pd.DataFrame) -> None:
    """Validate rail schedule sheet data."""
    if df.empty:
        return
    required_columns = ['Date', 'Product', 'Volume']
    for col in required_columns:
        if col not in df.columns:
            raise InvalidDataError(f"Required column '{col}' missing from rail sheet")
    for idx, row in df.iterrows():
        date_val = row.get("Date")
        if pd.isna(date_val):
            raise InvalidDataError(f"Missing date in rail row {int(idx)+2}")
        if not isinstance(date_val, datetime):
            try:
                parse_datetime(str(date_val))
            except ValueError as e:
                raise InvalidDataError(f"Invalid date in rail row {int(idx)+2}: {e}")
        product = str(row.get("Product", "sunflower")).strip()
        if not product:
            raise InvalidDataError(f"Empty product in rail row {int(idx)+2}")
        try:
            volume = float(row.get("Volume", 0))
            if volume < 0:
                raise InvalidDataError(f"Negative volume in rail row {int(idx)+2}: {volume}")
        except (ValueError, TypeError):
            raise InvalidDataError(f"Invalid volume in rail row {int(idx)+2}: {row.get('Volume')}")


def validate_demand_data(df: pd.DataFrame) -> None:
    """Validate demand sheet data."""
    if df.empty:
        return
    required_columns = ['Week', 'Client', 'Product', 'Volume', 'Priority']
    for col in required_columns:
        if col not in df.columns:
            raise InvalidDataError(f"Required column '{col}' missing from demand sheet")
    for idx, row in df.iterrows():
        week = str(row.get("Week", "")).strip()
        if not week:
            raise InvalidDataError(f"Empty week in demand row {int(idx)+2}")
        client = str(row.get("Client", "")).strip()
        if not client:
            raise InvalidDataError(f"Empty client in demand row {int(idx)+2}")
        product = str(row.get("Product", "")).strip()
        if not product:
            raise InvalidDataError(f"Empty product in demand row {int(idx)+2}")
        try:
            volume = float(row.get("Volume", 0))
            if volume < 0:
                raise InvalidDataError(f"Negative volume in demand row {int(idx)+2}: {volume}")
        except (ValueError, TypeError):
            raise InvalidDataError(f"Invalid volume in demand row {int(idx)+2}: {row.get('Volume')}")
        priority = str(row.get("Priority", "MEDIUM")).strip().upper()
        if priority not in ['HIGH', 'MEDIUM', 'LOW']:
            raise InvalidDataError(f"Invalid priority in demand row {int(idx)+2}: {priority}")