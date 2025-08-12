"""Configuration file include processing and reference resolution."""

import os
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml

from toolbelt.logging import get_logger
from toolbelt.package_resources import resolve_package_resource

log = get_logger(__name__)


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


def process_includes(
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
                # Import file_loaders functions here to avoid circular import
                from .file_loaders import _load_python_module, _extract_config_from_module
                from .models import ToolbeltConfig
                
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
            included_data, included_sources = process_includes(
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
