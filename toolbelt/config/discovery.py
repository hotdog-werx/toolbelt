"""Configuration file discovery and source resolution."""

from pathlib import Path

from .file_loaders import load_pyproject_toml
from .includes import resolve_config_reference


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
