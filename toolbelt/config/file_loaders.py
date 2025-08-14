"""Configuration file loading utilities for different file formats."""

import importlib.util
import tomllib  # Python 3.11+ only
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml

from .models import ToolbeltConfig
from .parser import parse_toolbelt_config


def load_yaml_config(config_path: Path) -> ToolbeltConfig:
    """Load configuration from a YAML file.

    Args:
        config_path: The path to the YAML configuration file.

    Returns:
        A ToolbeltConfig object representing the loaded configuration.
    """
    # Avoid circular import
    from .includes import process_includes  # noqa: PLC0415

    try:
        with Path(config_path).open('r') as f:
            data = yaml.safe_load(f)

        # Process includes before parsing
        processed_data, include_sources = process_includes(
            data,
            config_path.parent,
        )

        config = parse_toolbelt_config(processed_data)

        # Add all sources (includes first, then main file)
        for source in include_sources:
            config.sources.append(source)
        config.sources.append(str(config_path))

    except Exception as e:
        msg = f'Error loading YAML config file {config_path}; {e}'
        raise ValueError(msg) from e
    return config


def _load_python_module(config_path: Path) -> ModuleType:
    """Load a Python module from a file path."""
    spec = importlib.util.spec_from_file_location(
        'toolbelt_config',
        config_path,
    )
    if spec is None or spec.loader is None:
        msg = f'Could not load Python config from {config_path}'
        raise ValueError(msg)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _extract_config_from_module(
    module: ModuleType,
) -> dict[str, Any] | ToolbeltConfig:
    """Extract the config object from a loaded module."""
    if not hasattr(module, 'config'):
        msg = "Python config file must define a 'config' variable"
        raise ValueError(msg)

    config_data = module.config
    if isinstance(config_data, ToolbeltConfig):
        return config_data
    if isinstance(config_data, dict):
        return config_data  # Return raw dict to preserve include statements

    msg = 'Config must be a dictionary or ToolbeltConfig instance'
    raise ValueError(msg)


def load_python_config(config_path: Path) -> ToolbeltConfig:
    """Load configuration from a Python file.

    Args:
        config_path: The path to the Python configuration file.

    Returns:
        A ToolbeltConfig object representing the loaded configuration.
    """
    # Avoid circular import
    from .includes import process_includes  # noqa: PLC0415

    try:
        module = _load_python_module(config_path)
        config_or_data = _extract_config_from_module(module)

        # Convert to dict for include processing
        data = config_or_data.model_dump() if isinstance(config_or_data, ToolbeltConfig) else config_or_data

        # Process includes before final parsing
        processed_data, include_sources = process_includes(
            data,
            config_path.parent,
        )

        config = parse_toolbelt_config(processed_data)

        # Add all sources (includes first, then main file)
        for source in include_sources:
            config.sources.append(source)
        config.sources.append(str(config_path))

    except Exception as e:
        msg = f'Error loading Python config file {config_path}: {e}'
        raise ValueError(msg) from e
    return config


def load_config_from_file(config_path: Path) -> ToolbeltConfig:
    """Load configuration from a specific file path."""
    if config_path.suffix in ['.yaml', '.yml']:
        return load_yaml_config(config_path)
    if config_path.suffix == '.py':
        return load_python_config(config_path)
    msg = f'Unsupported configuration file type: {config_path.suffix}'
    raise ValueError(msg)


def load_pyproject_toml(pyproject_path: Path) -> dict[str, Any] | None:
    """Load pyproject.toml and extract [tool.toolbelt] section.

    Args:
        pyproject_path: Path to pyproject.toml file.

    Returns:
        The [tool.toolbelt] section as a dict, or None if not found.
    """
    try:
        with pyproject_path.open('rb') as f:
            data = tomllib.load(f)
        return data.get('tool', {}).get('toolbelt')
    except (OSError, ValueError, TypeError):
        # If pyproject.toml is malformed or can't be read, skip it
        return None
