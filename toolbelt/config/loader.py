"""Configuration file loading utilities."""

import importlib.util
import os
import tomllib  # Python 3.11+ only
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml

from toolbelt.logging import get_logger
from toolbelt.package_resources import resolve_package_resource

from .defaults import get_default_config
from .models import ToolbeltConfig
from .parser import parse_toolbelt_config

log = get_logger(__name__)


def get_env_variables_context() -> dict[str, str]:
    """Get environment variables that are safe to use in templates.

    Only allows variables with specific prefixes to avoid exposing sensitive data.

    Returns:
        Dictionary of filtered environment variables.
    """
    allowed_prefixes = ('TOOLBELT_', 'TB_', 'TBELT_', 'CI_', 'BUILD_')
    return {k: v for k, v in os.environ.items() if any(k.startswith(prefix) for prefix in allowed_prefixes)}


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
        
        # Process includes before parsing
        processed_data, include_sources = _process_includes(data, config_path.parent)
        
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


def _extract_config_from_module(module: ModuleType) -> dict[str, Any] | ToolbeltConfig:
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
    try:
        module = _load_python_module(config_path)
        config_or_data = _extract_config_from_module(module)
        
        # Convert to dict for include processing
        if isinstance(config_or_data, ToolbeltConfig):
            data = config_or_data.model_dump()
        else:
            data = config_or_data
        
        # Process includes before final parsing
        processed_data, include_sources = _process_includes(data, config_path.parent)
        
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
        # Return default configuration with environment variables
        config = get_default_config()
    elif len(sources) == 1:
        # Single source: load it directly
        config = load_config_from_file(sources[0])
    else:
        # Multiple sources: merge them in order
        config = load_config_from_file(sources[0])
        for source in sources[1:]:
            override_config = load_config_from_file(source)
            config = merge_configs(config, override_config)

    # Apply environment variables as final step (highest precedence)
    env_variables = get_env_variables_context()
    if env_variables:
        # Create a new config with environment variables merged
        # Environment variables override all other variable sources
        final_variables = {**config.variables, **env_variables}
        config = config.model_copy(update={'variables': final_variables})

    return config


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

    # Merge variables: base < override (config files only)
    # Environment variables will be applied later in load_config()
    merged_variables = {**base.variables, **override.variables}

    return ToolbeltConfig(
        sources=[*base.sources, *override.sources],
        profiles=merged_languages,
        global_exclude_patterns=merged_excludes,
        variables=merged_variables,
    )


def _process_includes(
    data: dict[str, Any], 
    base_path: Path, 
    processed_sources: set[str] | None = None
) -> tuple[dict[str, Any], list[str]]:
    """Process include statements in config data, resolving and merging included configs.
    
    Args:
        data: Raw configuration data that may contain 'include' key.
        base_path: Base path for resolving relative includes.
        processed_sources: Set of already processed file paths to detect circular deps.
        
    Returns:
        Tuple of (merged_data, sources_list) where merged_data has includes resolved
        and sources_list contains all processed file paths in order.
    """
    if processed_sources is None:
        processed_sources = set()
    
    sources = []
    
    # If no includes, return data as-is
    if 'include' not in data:
        return data, sources
    
    includes = data['include']
    if not isinstance(includes, list):
        includes = [includes]
    
    # Start with base data (without the include key)
    merged_data = {k: v for k, v in data.items() if k != 'include'}
    
    # Process each include
    for include_ref in includes:
        resolved_path = resolve_config_reference(include_ref, base_path)
        if not resolved_path:
            log.warning(f'Failed to resolve include reference: {include_ref}')
            continue
            
        resolved_path_str = str(resolved_path)
        
        # Check for circular dependency
        if resolved_path_str in processed_sources:
            log.warning(f'Circular dependency detected, skipping: {include_ref}')
            continue
            
        # Check if file exists (for non-package resources)
        if not include_ref.startswith('@') and not resolved_path.exists():
            log.warning(f'Include file not found: {resolved_path}')
            continue
            
        try:
            # Load the included file
            processed_sources.add(resolved_path_str)
            
            if resolved_path.suffix in ['.yaml', '.yml']:
                with resolved_path.open('r') as f:
                    included_data = yaml.safe_load(f)
            elif resolved_path.suffix == '.py':
                module = _load_python_module(resolved_path)
                included_config_or_data = _extract_config_from_module(module)
                if isinstance(included_config_or_data, ToolbeltConfig):
                    included_data = included_config_or_data.model_dump()
                else:
                    included_data = included_config_or_data
            else:
                log.warning(f'Unsupported include file type: {resolved_path.suffix}')
                continue
                
            # Recursively process includes in the included file
            included_data, included_sources = _process_includes(
                included_data, 
                resolved_path.parent, 
                processed_sources.copy()
            )
            
            sources.extend(included_sources)
            sources.append(resolved_path_str)
            
            # Merge the included data with current data
            merged_data = _merge_config_data(merged_data, included_data)
            
        except Exception as e:
            log.warning(f'Failed to load include {include_ref}: {e}')
            continue
        finally:
            # Remove from processed sources after processing to allow same file 
            # to be included in different branches
            processed_sources.discard(resolved_path_str)
    
    return merged_data, sources


def _merge_config_data(base_data: dict[str, Any], override_data: dict[str, Any]) -> dict[str, Any]:
    """Merge two raw config data dictionaries.
    
    Args:
        base_data: Base configuration data.
        override_data: Override configuration data.
        
    Returns:
        Merged configuration data.
    """
    merged = base_data.copy()
    
    for key, value in override_data.items():
        if key == 'profiles' and key in merged:
            # Merge profiles dict
            merged_profiles = merged[key].copy()
            merged_profiles.update(value)
            merged[key] = merged_profiles
        elif key == 'global_exclude_patterns' and key in merged:
            # Concatenate exclude patterns
            merged[key] = merged[key] + value
        elif key == 'variables' and key in merged:
            # Merge variables dict
            merged_vars = merged[key].copy()
            merged_vars.update(value)
            merged[key] = merged_vars
        else:
            # Override other keys
            merged[key] = value
    
    return merged
