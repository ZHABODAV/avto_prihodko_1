"""
Constants Module for Terminal Optimizer

This module provides backward-compatible access to configuration constants.
All constants are now sourced from the centralized configuration system.

For environment-specific overrides, use environment variables prefixed with TERMINAL_OPTIMIZER_.
Example: TERMINAL_OPTIMIZER_RATES__SHIP_DISCHARGE__LINE1=950
"""

from typing import Dict, Tuple
from .config import config

# =============================================================================
# FLOW RATES (tonnes per hour)
# =============================================================================

# Ship discharge rates
RATE_SHIP_DISCHARGE_LINE1 = config.get('rates.ship_discharge.line1', 900.0)
RATE_SHIP_DISCHARGE_LINE2_TANK = config.get('rates.ship_discharge.line2_tank', 500.0)
RATE_SHIP_DISCHARGE_LINE2_DIRECT = config.get('rates.ship_discharge.line2_direct', 146.0)

# Ship loading rates
RATE_SHIP_LOAD_MIN = config.get('rates.ship_load.min', 500.0)
RATE_SHIP_LOAD_MAX = config.get('rates.ship_load.max', 900.0)

# Rail discharge rates
RATE_RAIL_DISCHARGE_SUMMER = config.get('rates.rail_discharge.summer', 195.0)
RATE_RAIL_DISCHARGE_WINTER = config.get('rates.rail_discharge.winter', 146.0)

# Transfer rates
RATE_SHT_TRANSFER = config.get('rates.transfer.sht', 500.0)

# =============================================================================
# WAGON PARAMETERS
# =============================================================================

WAGON_CAPACITY = config.get('wagon.capacity', 65.0)
WAGONS_PER_BATCH = config.get('wagon.per_batch', 18)
MAX_BATCHES_PER_DAY_SUMMER = config.get('wagon.max_batches_per_day.summer', 4)
MAX_BATCHES_PER_DAY_WINTER = config.get('wagon.max_batches_per_day.winter', 3)
WAGON_PREP_TIME_HOURS = config.get('wagon.prep_time_hours', 1.5)
WAGON_REJECT_RATE = config.get('wagon.reject_rate', 0.12)

# =============================================================================
# TANK CAPACITIES (for utilization calculations)
# =============================================================================

TANK_CAPACITY_RVS = config.get('tank_capacity.rvs', 9900.0)
TANK_CAPACITY_SHT = config.get('tank_capacity.sht', 2700.0)

# =============================================================================
# PALM FRACTION PARAMETERS
# =============================================================================

# Palm fraction priorities (higher number = higher priority for Line1)
PALM_FRACTION_PRIORITIES = config.get('palm.fraction_priorities', {
    "palm_oil": 10,
    "palm_oil_low3mcpd": 9,
    "palm_olein": 8,
    "palm_olein_low3mcpd": 7,
    "palm_stearin": 6,
    "palm_pfad": 5,
})

# Fraction size thresholds (tonnes)
LARGE_FRACTION_THRESHOLD = config.get('palm.large_fraction_threshold', 5000.0)
DIRECT_DISCHARGE_THRESHOLD = config.get('palm.direct_discharge_threshold', 2000.0)

# =============================================================================
# SAFETY MARGINS AND THRESHOLDS
# =============================================================================

DEFAULT_SAFETY_MARGIN = config.get('safety.margin', 0.10)

# =============================================================================
# RESOURCE NAMES
# =============================================================================

BERTH_PALM = "BERTH_PALM"
BERTH_SUNFLOWER = "BERTH_SUNFLOWER"

# =============================================================================
# TIME PARAMETERS (hours)
# =============================================================================

DEFAULT_BERTH_SHIFT_TIME = config.get('time.berth_shift', 1.5)
DEFAULT_UNBERTH_DURATION = config.get('time.unberth_duration', 4.0)
DEFAULT_BUFFER_TIME = config.get('time.buffer', 2.0)
RAIL_BUFFER_TIME = config.get('time.rail_buffer', 0.5)

# =============================================================================
# COMPATIBILITY MATRIX
# =============================================================================

def _build_compatibility_matrix() -> Dict[Tuple[str, str], int]:
    """Build compatibility matrix from config."""
    matrix_config = config.get('compatibility_matrix', {})
    matrix = {}
    for key, value in matrix_config.items():
        # Convert key like "sunflower__palm_oil" to ("sunflower", "palm_oil")
        from_prod, to_prod = key.split('__', 1)
        matrix[(from_prod, to_prod)] = value
    return matrix

DEFAULT_COMPATIBILITY_MATRIX: Dict[Tuple[str, str], int] = _build_compatibility_matrix()

# =============================================================================
# DEFAULT PARAMETERS
# =============================================================================

# Default scenario parameters
DEFAULT_PARAMETERS = config.get('scenario_defaults', {
    "season": "summer",
    "rail_discharge_rate": RATE_RAIL_DISCHARGE_SUMMER,
    "ship_load_rate_min": RATE_SHIP_LOAD_MIN,
    "ship_load_rate_max": RATE_SHIP_LOAD_MAX,
    "ship_discharge_line1": RATE_SHIP_DISCHARGE_LINE1,
    "ship_discharge_line2_tank": RATE_SHIP_DISCHARGE_LINE2_TANK,
    "ship_discharge_line2_direct": RATE_SHIP_DISCHARGE_LINE2_DIRECT,
    "wagon_prep_time": WAGON_PREP_TIME_HOURS,
    "wagon_reject_rate": WAGON_REJECT_RATE,
    "berth_shift_time": DEFAULT_BERTH_SHIFT_TIME,
    "cleaning_time_standard": 48.0,
    "cleaning_time_full": 72.0,
    "analysis_time": 72.0,
    "wagon_own_cost": 3000.0,
    "wagon_external_cost": 50000.0,
    "batch_extra_penalty": 50000.0,
    "total_wagon_fleet": 500,
})

# =============================================================================
# OPERATION PARAMETERS
# =============================================================================

# Rail accumulation parameters
DEFAULT_BATCHES_PER_DAY = config.get('operation.batches_per_day', 4)
BATCH_DURATION_HOURS = config.get('operation.batch_duration_hours', 6.0)

# Tank operation thresholds
MIN_TANK_VOLUME_THRESHOLD = config.get('operation.min_tank_volume_threshold', 1000.0)

# Default operation rates
DEFAULT_SHIP_LOAD_RATE = config.get('operation.default_ship_load_rate', 700.0)
DEFAULT_PUMP_RATE = config.get('operation.default_pump_rate', 500.0)
DEFAULT_RAIL_RATE = config.get('operation.default_rail_rate', 195.0)

# =============================================================================
# CLEANING DURATIONS (hours)
# =============================================================================

# Product transition cleaning times
CLEANING_LOW3MCPD_TO_STANDARD = config.get('cleaning.low3mcpd_to_standard', 168.0)  # 7 days
CLEANING_STANDARD_TO_LOW3MCPD = config.get('cleaning.standard_to_low3mcpd', 72.0)   # 3 days
CLEANING_PALM_TO_SUNFLOWER = config.get('cleaning.palm_to_sunflower', 48.0)         # 2 days
CLEANING_DIFFERENT_PALM_FRACTIONS = config.get('cleaning.different_palm_fractions', 12.0)  # 12 hours
CLEANING_DEFAULT = config.get('cleaning.default', 48.0)                             # Default cleaning time

# Line cleaning durations (usually faster than tanks)
CLEANING_LINE_PALM_TO_SUNFLOWER = config.get('cleaning.line.palm_to_sunflower', 4.0)
CLEANING_LINE_DIFFERENT_PALM = config.get('cleaning.line.different_palm', 2.0)
CLEANING_LINE_DEFAULT = config.get('cleaning.line.default', 4.0)

# =============================================================================
# VALIDATION LIMITS
# =============================================================================

# Maximum flow rates for validation
MAX_RATE_SHIP_DISCHARGE_LINE1 = config.get('validation.max_rates.ship_discharge_line1', 900.0)
MAX_RATE_SHIP_DISCHARGE_LINE2_TANK = config.get('validation.max_rates.ship_discharge_line2_tank', 500.0)
MAX_RATE_SHIP_DISCHARGE_LINE2_DIRECT = config.get('validation.max_rates.ship_discharge_line2_direct', 146.0)
MAX_RATE_SHIP_LOAD_MIN = config.get('validation.max_rates.ship_load_min', 500.0)
MAX_RATE_SHIP_LOAD_MAX = config.get('validation.max_rates.ship_load_max', 900.0)
MAX_RATE_RAIL_DISCHARGE_SUMMER = config.get('validation.max_rates.rail_discharge_summer', 195.0)
MAX_RATE_RAIL_DISCHARGE_WINTER = config.get('validation.max_rates.rail_discharge_winter', 146.0)
MAX_RATE_TANK_PUMP = config.get('validation.max_rates.tank_pump', 500.0)

# Operational limits
MAX_RAIL_BATCHES_PER_DAY = config.get('validation.max_rail_batches_per_day', 4)

# =============================================================================
# ALGORITHM PARAMETERS
# =============================================================================

MAX_CONFLICT_ITERATIONS = config.get('algorithm.max_conflict_iterations', 10)