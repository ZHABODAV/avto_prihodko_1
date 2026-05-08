#!/usr/bin/env python3
"""Test script for configuration system."""

import os
import sys
sys.path.append('.')

# Set test environment variable
os.environ['TERMINAL_OPTIMIZER_RATES__SHIP_DISCHARGE__LINE1'] = '950'

# Import after setting env var
from terminal_optimizer.constants import RATE_SHIP_DISCHARGE_LINE1, WAGON_CAPACITY

print("Testing configuration system:")
print(f"RATE_SHIP_DISCHARGE_LINE1: {RATE_SHIP_DISCHARGE_LINE1} (should be 950)")
print(f"WAGON_CAPACITY: {WAGON_CAPACITY} (should be 65.0)")

# Test direct config access
from terminal_optimizer.config import config
print(f"Direct config access - rates.ship_discharge.line1: {config.get('rates.ship_discharge.line1')}")

print("Test completed successfully!")