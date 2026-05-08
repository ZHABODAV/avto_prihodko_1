"""
Terminal Optimizer - Oil Terminal Operations Planning System

This package provides tools for optimizing oil terminal operations including:
- Tank management (РВС 1-5, ШТ) for sunflower and palm oil
- Vessel cargo operations with multi-fraction handling
- Railway wagon logistics with Markov chain forecasting
- Excel-based I/O with schedule generation
- Risk analysis and cost optimization
- Main orchestration and user edit handling

Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "Terminal Optimizer Team"

from terminal_optimizer.domain_models import Tank, Vessel, Operation, Scenario
from terminal_optimizer.main import TerminalOptimizer, SequenceEditor

__all__ = [
    "Tank",
    "Vessel",
    "Operation",
    "Scenario",
    "TerminalOptimizer",
    "SequenceEditor",
    "__version__",
]
