"""Configuration management utilities."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Config:
    """Configuration container with attribute access."""
    
    def __init__(self, config_dict: Dict[str, Any]):
        for key, value in config_dict.items():
            if isinstance(value, dict):
                setattr(self, key, Config(value))
            else:
                setattr(self, key, value)
    
    def __getitem__(self, key):
        return getattr(self, key)
    
    def __setitem__(self, key, value):
        setattr(self, key, value)
    
    def get(self, key, default=None):
        return getattr(self, key, default)


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from YAML file.
    
    Args:
        config_path: Path to config file. If None, uses default config.yaml
        
    Returns:
        Config object with loaded configuration
    """
    if config_path is None:
        # Find config file relative to this module
        current_dir = Path(__file__).parent.parent.parent.parent
        config_path = current_dir / "config" / "config.yaml"
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config_dict = yaml.safe_load(f)
    
    return Config(config_dict)


def get_data_dir(config: Config) -> Path:
    """Get data directory path."""
    return Path(config.output.data_dir)


def get_results_dir(config: Config) -> Path:
    """Get results directory path."""
    return Path(config.output.results_dir)


def setup_directories(config: Config) -> None:
    """Create necessary directories if they don't exist."""
    dirs_to_create = [
        get_data_dir(config),
        get_results_dir(config),
        Path(config.output.figures_dir),
        Path(config.output.models_dir),
        Path("logs"),
    ]
    
    for dir_path in dirs_to_create:
        dir_path.mkdir(parents=True, exist_ok=True)


def update_config(config: Config, updates: Dict[str, Any]) -> Config:
    """Update configuration with new values.
    
    Args:
        config: Original configuration
        updates: Dictionary of updates to apply
        
    Returns:
        Updated configuration
    """
    def deep_update(base_dict, update_dict):
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict:
                deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    # Convert config back to dict for updating
    config_dict = config.__dict__.copy()
    deep_update(config_dict, updates)
    
    return Config(config_dict)


# Global config instance
_global_config = None


def get_config() -> Config:
    """Get global configuration instance."""
    global _global_config
    if _global_config is None:
        _global_config = load_config()
        setup_directories(_global_config)
    return _global_config


def set_config(config: Config) -> None:
    """Set global configuration instance."""
    global _global_config
    _global_config = config
    setup_directories(config)