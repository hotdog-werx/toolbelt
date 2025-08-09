"""Configuration file loading utilities."""

import importlib.util
import tomllib  # Python 3.11+ only
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol

import yaml

from toolbelt.logging import get_logger
from toolbelt.package_resources import resolve_package_resource

from .defaults import get_default_config
from .models import ToolbeltConfig
from .parser import parse_toolbelt_config

log = get_logger(__name__)


class HasConfig(Protocol):
    config: Any


def load_yaml_config(config_path: Path) -> ToolbeltConfig:
    """Load configuration from a YAML file.

    Args:
        config_path: The path to the YAML configuration file.

    Returns:
        A ToolbeltConfig object representing the loaded configuration.
    """
    try:
        with Path(config_path).open('r') as f:
            data = yaml.safe_load(f)
        config = parse_toolbelt_config(data)
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


def _extract_config_from_module(module: ModuleType) -> ToolbeltConfig:
    """Extract the config object from a loaded module."""
    if hasattr(module, 'config'):
        config_data = module.config
        if isinstance(config_data, dict):
            return parse_toolbelt_config(config_data)
        if isinstance(config_data, ToolbeltConfig):
            return config_data
        msg = 'Config must be a dictionary or ToolbeltConfig instance'
        raise ValueError(msg)
    msg = "Python config file must define a 'config' variable"
    raise ValueError(msg)


def load_python_config(config_path: Path) -> ToolbeltConfig:
    """Load configuration from a Python file.

    Args:
        config_path: The path to the Python configuration file.

    Returns:
        A ToolbeltConfig object representing the loaded configuration.
    """
    try:
        module = _load_python_module(config_path)
        config = _extract_config_from_module(module)
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


def resolve_config_reference(config_ref: str, base_path: Path) -> Path | None:
    """Resolve a configuration reference to an absolute path.

    Args:
        config_ref: Configuration reference. Supports:
            - Relative path: 'config.yaml'
            - Absolute path: '/path/to/config.yaml'
            - Home directory: '~/config.yaml'
            - Package resource: '@package-name:path/to/resource.yaml'
        base_path: Base directory for resolving relative paths.

    Returns:
        Resolved Path object, or None if reference is invalid.
    """
    try:
        if config_ref.startswith('@'):
            # Handle package resource reference: @package:path
            return resolve_package_resource(config_ref)
        if config_ref.startswith('~/'):
            # Expand user home directory
            return Path(config_ref).expanduser()
        if config_ref.startswith('/'):
            # Absolute path
            return Path(config_ref)
        # Relative path - resolve relative to base_path
        return base_path / config_ref
    except (ValueError, OSError) as e:
        log.exception(
            'config_reference_resolution_failed',
            config_ref=config_ref,
            base_path=str(base_path),
            error=str(e),
        )
        return None


def _load_from_pyproject_includes(cwd: Path) -> list[Path]:
    """Load configuration sources from pyproject.toml [tool.toolbelt] include."""
    pyproject_path = cwd / 'pyproject.toml'
    if not pyproject_path.exists():
        return []

    toolbelt_config = load_pyproject_toml(pyproject_path)
    if not toolbelt_config or 'include' not in toolbelt_config:
        return []

    sources = []
    for config_ref in toolbelt_config['include']:
        try:
            resolved_path = resolve_config_reference(config_ref, cwd)
            # For regular files, check if they exist
            # For package resources, the resolve function already validates existence
            if resolved_path and (config_ref.startswith('@') or resolved_path.exists()):
                sources.append(resolved_path)
        except (ValueError, ImportError, FileNotFoundError):
            # Skip invalid references (package not found, resource not found, etc.)
            # This allows graceful degradation when optional packages aren't installed
            continue

    return sources


def _find_standalone_config(cwd: Path) -> list[Path]:
    """Find standalone configuration files in current directory."""
    for fname in ['toolbelt.yaml', 'toolbelt.yml', 'toolbelt.py']:
        config_file = cwd / fname
        if config_file.exists():
            return [config_file]
    return []


def find_config_sources(config_path: Path | None = None) -> list[Path]:
    """Find configuration sources in priority order.

    Args:
        config_path: Explicit config path, if provided.

    Returns:
        List of Path objects to configuration files, in load order.
    """
    if config_path:
        return [config_path] if config_path.exists() else []

    cwd = Path.cwd()

    # 1. Check for pyproject.toml with [tool.toolbelt] include
    sources = _load_from_pyproject_includes(cwd)
    if sources:
        return sources

    # 2. Fallback to standalone config files
    return _find_standalone_config(cwd)


def load_config(config_paths: list[Path] | None = None) -> ToolbeltConfig:
    """Load and merge configuration from multiple sources.

    Args:
        config_paths: List of configuration file paths to load. If None, uses default search.

    Returns:
        Merged ToolbeltConfig object from all sources.
    """
    sources = config_paths if config_paths is not None else find_config_sources()

    if not sources:
        # Return default configuration
        return get_default_config()

    # If only one source, load it directly
    if len(sources) == 1:
        return load_config_from_file(sources[0])

    # Multiple sources: merge them in order
    merged_config = load_config_from_file(sources[0])
    for source in sources[1:]:
        override_config = load_config_from_file(source)
        merged_config = merge_configs(merged_config, override_config)

    return merged_config


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


def merge_configs(
    base: ToolbeltConfig,
    override: ToolbeltConfig,
) -> ToolbeltConfig:
    """Merge two ToolbeltConfig objects, with override taking precedence.

    Args:
        base: Base configuration.
        override: Override configuration (takes precedence).

    Returns:
        New merged ToolbeltConfig.
    """
    # For now, implement simple override semantics
    # Later can be enhanced for more sophisticated merging
    merged_languages = base.profiles.copy()

    # Override profiles, but allow per-profile field overrides (exclusions, ignore_files, etc.)
    # TODO(jmlopez): Implement more sophisticated merge strategies (e.g., merge tool lists, deduplicate extensions)
    # https://github.com/hotdog-werx/toolbelt/issues/TBD
    for profile_name, override_profile in override.profiles.items():
        base_profile = merged_languages.get(profile_name)
        if base_profile:
            # Merge exclusions and ignore_files, override tools and extensions
            merged_languages[profile_name] = base_profile.model_copy(
                update={
                    'exclude_patterns': override_profile.exclude_patterns or base_profile.exclude_patterns,
                    'ignore_files': override_profile.ignore_files or base_profile.ignore_files,
                    'check_tools': override_profile.check_tools or base_profile.check_tools,
                    'format_tools': override_profile.format_tools or base_profile.format_tools,
                    'extensions': override_profile.extensions or base_profile.extensions,
                },
            )
        else:
            merged_languages[profile_name] = override_profile

    # Merge global exclude patterns
    merged_excludes = base.global_exclude_patterns + override.global_exclude_patterns

    return ToolbeltConfig(
        sources=[*base.sources, *override.sources],
        profiles=merged_languages,
        global_exclude_patterns=merged_excludes,
        variables={**base.variables, **override.variables},
    )
