"""
Configuration Management for Terminal Optimizer

This module provides centralized configuration management with YAML base config
and environment variable overrides for different environments (dev, prod, testing).

Environment variables should be prefixed with TERMINAL_OPTIMIZER_ and use
double underscores for nested keys, e.g.:
TERMINAL_OPTIMIZER_RATES__SHIP_DISCHARGE__LINE1=950
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """
    Centralized configuration manager.

    Loads base configuration from config.yaml and applies environment variable overrides.
    Environment variables should be prefixed with TERMINAL_OPTIMIZER_ and use
    double underscores for nested keys.
    """

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_file: Path to YAML config file (defaults to config.yaml in same directory)
        """
        if config_file is None:
            self.config_file = Path(__file__).parent / "config.yaml"
        else:
            self.config_file = Path(config_file)

        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load base configuration from YAML file."""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")

        with open(self.config_file, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f) or {}

        # Apply environment variable overrides
        self._apply_env_overrides()

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides to configuration."""
        prefix = "TERMINAL_OPTIMIZER_"

        for env_key, env_value in os.environ.items():
            if not env_key.startswith(prefix):
                continue

            # Remove prefix and convert to nested keys
            config_key = env_key[len(prefix):].lower()

            # Convert double underscores to nested structure
            keys = config_key.split("__")
            self._set_nested_value(self._config, keys, self._parse_env_value(env_value))

    def _set_nested_value(self, config: Dict[str, Any], keys: list, value: Any) -> None:
        """Set a value in nested dictionary structure."""
        current = config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def _parse_env_value(self, value: str) -> Any:
        """Parse environment variable value to appropriate type."""
        # Try to parse as boolean
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'

        # Try to parse as number
        try:
            # Try int first
            if '.' not in value:
                return int(value)
            # Then float
            return float(value)
        except ValueError:
            pass

        # Return as string
        return value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated key.

        Args:
            key: Dot-separated key path (e.g., 'rates.ship_discharge.line1')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        current = self._config

        try:
            for k in keys:
                current = current[k]
            return current
        except (KeyError, TypeError):
            return default

    def __getitem__(self, key: str) -> Any:
        """Get configuration value by key."""
        value = self.get(key)
        if value is None:
            raise KeyError(f"Configuration key not found: {key}")
        return value

    def __contains__(self, key: str) -> bool:
        """Check if configuration key exists."""
        return self.get(key) is not None

    def to_dict(self) -> Dict[str, Any]:
        """Return a copy of the full configuration dictionary."""
        return self._config.copy()


# Global configuration instance
config = Config()


def get_config() -> Config:
    """Get the global configuration instance."""
    return config