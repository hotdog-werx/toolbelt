"""Utility for resolving package resource references to absolute filesystem paths.

This module provides a simple function to resolve @package:path/to/resource references
to absolute filesystem paths, making package resources accessible to any tool that
works with regular files.

Requires Python 3.11+.
"""

import importlib
import tempfile
from importlib import resources
from pathlib import Path


def _validate_package_reference(package_resource_ref: str) -> list[str]:
    """Validate and parse package resource reference."""
    if not package_resource_ref.startswith('@'):
        msg = f'Package resource reference must start with @, got: {package_resource_ref}'
        raise ValueError(msg)

    # Remove @ prefix
    package_ref = package_resource_ref[1:]

    if ':' not in package_ref:
        msg = f'Invalid package reference: {package_resource_ref}. Expected format: @package-name:path/to/resource'
        raise ValueError(msg)

    return package_ref.split(':', 1)


def _extract_resource_to_temp_file(
    resource_content: bytes,
    package_name: str,
    resource_path: str,
) -> Path:
    """Extract resource content to a temporary file."""
    with tempfile.NamedTemporaryFile(
        mode='wb',
        suffix=f'_{Path(resource_path).name}',
        prefix=f'{package_name}_',
        delete=False,
    ) as temp_file:
        temp_file.write(resource_content)
        return Path(temp_file.name)


def _resolve_package_resource_internal(
    package_name: str,
    resource_path: str,
) -> Path:
    """Resolve using importlib.resources API."""
    resource_file = resources.files(package_name).joinpath(resource_path)

    if not resource_file.is_file():
        msg = f"Resource '{resource_path}' not found in package '{package_name}'"
        raise FileNotFoundError(msg)

    # Optimization: If the resource exists as a real filesystem path, return it directly
    # This avoids creating unnecessary temp files for development installs or extracted packages
    try:
        # Try to get the actual filesystem path
        with resources.as_file(resource_file) as actual_path:
            # If we can get a stable filesystem path (not in tempdir), use it
            temp_dir = Path(tempfile.gettempdir())
            if actual_path.exists() and not Path(actual_path).is_relative_to(
                temp_dir,
            ):
                return Path(actual_path)
    except (AttributeError, OSError):
        # Fall through to temp file extraction
        pass

    # Fallback: Extract to temp file (needed for zip-based installations)
    return _extract_resource_to_temp_file(
        resource_file.read_bytes(),
        package_name,
        resource_path,
    )


def resolve_package_resource(package_resource_ref: str) -> Path:
    """Resolve a package resource reference to an absolute filesystem path.

    Takes a reference in the format '@package-name:path/to/resource' and returns
    an absolute Path to the resource on the filesystem.

    Optimization: If the resource already exists as a regular file on the filesystem
    (e.g., development installs, extracted packages), returns the direct path.
    Otherwise, extracts the resource to a temporary location.

    Args:
        package_resource_ref: Package resource reference in format '@package:path/to/resource'

    Returns:
        Absolute Path to the resource on the filesystem

    Raises:
        ValueError: If the reference format is invalid
        ImportError: If the specified package is not installed
        FileNotFoundError: If the resource doesn't exist in the package

    Example:
        >>> path = resolve_package_resource('@mypackage:configs/settings.yaml')
        >>> print(path)
        /home/user/.local/lib/python3.11/site-packages/mypackage/configs/settings.yaml
        >>> # or /tmp/mypackage_settings.yaml_abc123 if extracted from zip
        >>> assert path.exists() and path.is_file()
    """
    package_name, resource_path = _validate_package_reference(
        package_resource_ref,
    )
    importlib.import_module(package_name)
    return _resolve_package_resource_internal(package_name, resource_path)


def is_package_resource_reference(ref: str) -> bool:
    """Check if a string is a package resource reference.

    Args:
        ref: String to check

    Returns:
        True if the string is a package resource reference (@package:path format)

    Example:
        >>> is_package_resource_reference('@mypackage:config.yaml')
        True
        >>> is_package_resource_reference('local_file.yaml')
        False
    """
    return isinstance(ref, str) and ref.startswith('@') and ':' in ref
