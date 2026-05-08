"""
Custom Exception Hierarchy for Terminal Optimizer

This module defines custom exceptions for domain-specific errors in the terminal optimization system.
All exceptions inherit from TerminalOptimizerError for consistent error handling.
"""

from typing import Any, Optional


class TerminalOptimizerError(Exception):
    """
    Base exception for all terminal optimizer errors.

    Attributes:
        message: Error message
        details: Optional additional details
    """

    def __init__(self, message: str, details: Optional[Any] = None):
        self.message = message
        self.details = details
        super().__init__(message)


class FileIOError(TerminalOptimizerError):
    """Raised when file I/O operations fail."""
    pass


class ExcelFileError(FileIOError):
    """Raised when Excel file operations fail."""
    pass


class CSVFileError(FileIOError):
    """Raised when CSV file operations fail."""
    pass


class DataValidationError(TerminalOptimizerError):
    """Raised when input data validation fails."""
    pass


class MissingDataError(DataValidationError):
    """Raised when required data is missing."""
    pass


class InvalidDataError(DataValidationError):
    """Raised when data is invalid or malformed."""
    pass


class CalculationError(TerminalOptimizerError):
    """Raised when calculations fail."""
    pass


class BalanceCalculationError(CalculationError):
    """Raised when tank balance calculations fail."""
    pass


class SequenceGenerationError(TerminalOptimizerError):
    """Raised when operation sequence generation fails."""
    pass


class WagonError(TerminalOptimizerError):
    """Raised when wagon-related operations fail."""
    pass


class WagonShortageError(WagonError):
    """Raised when wagon shortages occur."""
    pass


class RiskAnalysisError(TerminalOptimizerError):
    """Raised when risk analysis fails."""
    pass


class ValidationError(TerminalOptimizerError):
    """Raised when solution validation fails."""
    pass


class ConfigurationError(TerminalOptimizerError):
    """Raised when configuration is invalid."""
    pass


class DateParseError(DataValidationError):
    """Raised when date parsing fails."""
    pass