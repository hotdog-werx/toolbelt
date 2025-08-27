"""Configuration file include processing and reference resolution."""

from pathlib import Path
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
    processed_sources: set[str] | None = None,
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

    includes = _normalize_includes_list(data['include'])
    # Start with an empty config, merge all includes first
    merged_data = {}
    for include_ref in includes:
        include_result = _process_single_include(
            include_ref,
            base_path,
            processed_sources,
        )
        if include_result:
            included_data, included_sources = include_result
            sources.extend(included_sources)
            merged_data = _merge_config_data(merged_data, included_data)
    # Merge the current config last, so it overrides includes
    merged_data = _merge_config_data(
        merged_data,
        {k: v for k, v in data.items() if k != 'include'},
    )
    return merged_data, sources


def _normalize_includes_list(includes: str | list[str]) -> list[str]:
    """Normalize includes to a list format."""
    if not isinstance(includes, list):
        return [includes]
    return includes


def _process_single_include(
    include_ref: str,
    base_path: Path,
    processed_sources: set[str],
) -> tuple[dict[str, Any], list[str]] | None:
    """Process a single include reference and return the merged data and sources.

    Returns:
        Tuple of (included_data, sources) on success, None on failure/skip.
    """
    resolved_path = resolve_config_reference(include_ref, base_path)
    if not resolved_path:
        log.warning(
            'include_reference_resolution_failed',
            include_ref=include_ref,
        )
        return None

    resolved_path_str = str(resolved_path)

    # Check for circular dependency
    if resolved_path_str in processed_sources:
        log.warning(
            'circular_dependency_detected',
            include_ref=include_ref,
            resolved_path=resolved_path_str,
        )
        return None

    # Check if file exists (for non-package resources)
    if not include_ref.startswith('@') and not resolved_path.exists():
        log.warning(
            'include_file_not_found',
            include_ref=include_ref,
            resolved_path=str(resolved_path),
        )
        return None

    try:
        processed_sources.add(resolved_path_str)
        included_data = _load_include_file(resolved_path)

        # Recursively process includes in the included file
        included_data, included_sources = process_includes(
            included_data,
            resolved_path.parent,
            processed_sources.copy(),
        )

    except Exception as e:  # noqa: BLE001
        log.warning(
            'include_load_failed',
            include_ref=include_ref,
            error=str(e),
        )
        return None
    else:
        sources = [*included_sources, resolved_path_str]
        return included_data, sources
    finally:
        # Remove from processed sources after processing to allow same file
        # to be included in different branches
        processed_sources.discard(resolved_path_str)


def _load_include_file(resolved_path: Path) -> dict[str, Any]:
    """Load data from an include file based on its extension."""
    if resolved_path.suffix in ['.yaml', '.yml']:
        with resolved_path.open('r') as f:
            return yaml.safe_load(f)
    elif resolved_path.suffix == '.py':
        return _load_python_include_file(resolved_path)
    else:
        msg = f'Unsupported include file type: {resolved_path.suffix}'
        raise ValueError(msg)


def _load_python_include_file(resolved_path: Path) -> dict[str, Any]:
    """Load data from a Python include file."""
    # Import file_loaders functions here to avoid circular import
    from .file_loaders import _extract_config_from_module, _load_python_module  # noqa: PLC0415
    from .models import ToolbeltConfig  # noqa: PLC0415

    module = _load_python_module(resolved_path)
    included_config_or_data = _extract_config_from_module(module)
    if isinstance(included_config_or_data, ToolbeltConfig):
        return included_config_or_data.model_dump()
    return included_config_or_data


def _merge_config_data(
    base_data: dict[str, Any],
    override_data: dict[str, Any],
) -> dict[str, Any]:
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
            # For each profile in override, fully replace the base profile
            merged_profiles = merged[key].copy()
            for profile_name, profile_value in value.items():
                merged_profiles[profile_name] = profile_value
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
