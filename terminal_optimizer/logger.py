"""
Logging configuration for Terminal Optimizer
Конфигурация логирования для Терминального Оптимизатора
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import yaml


class TerminalOptimizerLogger:
    """Centralized logging for the optimizer"""
    
    _instance: Optional[logging.Logger] = None
    _error_messages: dict = {}
    
    @classmethod
    def get_logger(cls, name: str = "terminal_optimizer") -> logging.Logger:
        """Get or create logger instance"""
        if cls._instance is None:
            cls._instance = cls._setup_logger(name)
            cls._load_error_messages()
        return cls._instance
    
    @classmethod
    def _setup_logger(cls, name: str) -> logging.Logger:
        """Setup logger with file and console handlers"""
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        logger.handlers.clear()
        
        # Create logs directory
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Create log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"terminal_optimizer_{timestamp}.log"
        
        # File handler - detailed logs
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # Console handler - important messages only
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        # Add handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        logger.info(f"Logging initialized. Log file: {log_file}")
        
        return logger
    
    @classmethod
    def _load_error_messages(cls):
        """Load error messages from YAML file"""
        try:
            error_file = Path(__file__).parent / "error_messages.yaml"
            if error_file.exists():
                with open(error_file, 'r', encoding='utf-8') as f:
                    cls._error_messages = yaml.safe_load(f)
                if cls._instance:
                    cls._instance.debug(f"Loaded {len(cls._error_messages)} error messages")
            else:
                if cls._instance:
                    cls._instance.warning(f"Error messages file not found: {error_file}")
        except (FileNotFoundError, yaml.YAMLError, OSError) as e:
            if cls._instance:
                cls._instance.error(f"Failed to load error messages: {e}")
    
    @classmethod
    def get_error_message(cls, error_code: str, **kwargs) -> str:
        """
        Get formatted error message by code
        
        Args:
            error_code: Error code (e.g., 'ERR_001')
            **kwargs: Format parameters for the message
            
        Returns:
            Formatted error message
        """
        if not cls._error_messages:
            cls._load_error_messages()
        
        message_template = cls._error_messages.get(
            error_code, 
            f"Unknown error code: {error_code}"
        )
        
        try:
            return message_template.format(**kwargs)
        except KeyError as e:
            return f"{message_template} (Missing parameter: {e})"
    
    @classmethod
    def log_error(cls, error_code: str, **kwargs):
        """Log error with code and parameters"""
        logger = cls.get_logger()
        message = cls.get_error_message(error_code, **kwargs)
        logger.error(f"[{error_code}] {message}")
    
    @classmethod
    def log_warning(cls, warning_code: str, **kwargs):
        """Log warning with code and parameters"""
        logger = cls.get_logger()
        message = cls.get_error_message(warning_code, **kwargs)
        logger.warning(f"[{warning_code}] {message}")
    
    @classmethod
    def log_info(cls, info_code: str, **kwargs):
        """Log info with code and parameters"""
        logger = cls.get_logger()
        message = cls.get_error_message(info_code, **kwargs)
        logger.info(f"[{info_code}] {message}")


class OptimizerError(Exception):
    """Base exception for optimizer errors"""
    
    def __init__(self, error_code: str, **kwargs):
        self.error_code = error_code
        self.message = TerminalOptimizerLogger.get_error_message(error_code, **kwargs)
        super().__init__(self.message)
        TerminalOptimizerLogger.log_error(error_code, **kwargs)


class FileIOError(OptimizerError):
    """File I/O related errors"""
    pass


class DataValidationError(OptimizerError):
    """Data validation errors"""
    pass


class TankCapacityError(OptimizerError):
    """Tank capacity errors"""
    pass


class ProductCompatibilityError(OptimizerError):
    """Product compatibility errors"""
    pass


class SequenceGenerationError(OptimizerError):
    """Sequence generation errors"""
    pass


class CalculationError(OptimizerError):
    """Calculation errors"""
    pass


class ConfigurationError(OptimizerError):
    """Configuration errors"""
    pass


class WagonManagerError(OptimizerError):
    """Wagon manager errors"""
    pass


class RiskAnalysisError(OptimizerError):
    """Risk analysis errors"""
    pass


# Convenience function to get logger
def get_logger(name: str = "terminal_optimizer") -> logging.Logger:
    """Get logger instance"""
    return TerminalOptimizerLogger.get_logger(name)
