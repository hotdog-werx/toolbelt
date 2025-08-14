"""Utilities for handling ignore files like .gitignore, .prettierignore, etc."""

from dataclasses import dataclass
from pathlib import Path

import pathspec


@dataclass
class IgnoreManager:
    """Simple container for ignore configuration."""

    ignore_files: list[str]
    root_dir: Path
    _spec: pathspec.PathSpec | None = None

    def should_ignore(self, file_path: Path) -> bool:
        """Check if a file should be ignored using this manager."""
        return should_ignore_file(file_path, self._spec, self.root_dir)

    def filter_files(self, files: list[Path]) -> list[Path]:
        """Filter files using this manager."""
        return filter_ignored_files(files, self._spec, self.root_dir)


def load_ignore_patterns(
    ignore_files: list[str],
    root_dir: Path,
) -> pathspec.PathSpec:
    """Load patterns from ignore files and create a PathSpec.

    Args:
        ignore_files: List of ignore file names (e.g., [".gitignore", ".prettierignore"])
        root_dir: Root directory to search from

    Returns:
        PathSpec object with loaded patterns
    """
    all_patterns = []

    for ignore_file in ignore_files:
        ignore_path = root_dir / ignore_file
        if ignore_path.exists():
            try:
                with ignore_path.open(encoding='utf-8') as f:
                    patterns = f.read().splitlines()
                    # Filter out empty lines and comments
                    patterns = [
                        pattern.strip()
                        for pattern in patterns
                        if pattern.strip() and not pattern.strip().startswith('#')
                    ]
                    all_patterns.extend(patterns)
            except (OSError, UnicodeDecodeError):
                # Silently skip files we can't read
                continue

    if all_patterns:
        return pathspec.PathSpec.from_lines('gitwildmatch', all_patterns)
    # Return empty spec if no patterns found
    return pathspec.PathSpec([])


def should_ignore_file(
    file_path: Path,
    spec: pathspec.PathSpec | None,
    root_dir: Path,
) -> bool:
    """Check if a file should be ignored based on patterns.

    Args:
        file_path: Path to check (can be absolute or relative)
        spec: PathSpec object with ignore patterns
        root_dir: Root directory for relative path calculation

    Returns:
        True if the file should be ignored, False otherwise
    """
    if spec is None:
        return False

    # Convert to relative path from root_dir for pattern matching
    try:
        rel_path = file_path.relative_to(root_dir) if file_path.is_absolute() else file_path
    except ValueError:
        # Path is outside root_dir, don't ignore
        return False

    # Convert to forward slashes for consistent pattern matching
    path_str = str(rel_path).replace('\\', '/')

    return spec.match_file(path_str)


def filter_ignored_files(
    files: list[Path],
    spec: pathspec.PathSpec | None,
    root_dir: Path,
) -> list[Path]:
    """Filter a list of files, removing those that should be ignored.

    Args:
        files: List of file paths to filter
        spec: PathSpec object with ignore patterns
        root_dir: Root directory for relative path calculation

    Returns:
        Filtered list with ignored files removed
    """
    return [f for f in files if not should_ignore_file(f, spec, root_dir)]


def create_ignore_manager(
    ignore_files: list[str],
    root_dir: Path | None = None,
) -> IgnoreManager:
    """Create an IgnoreManager with the specified ignore files.

    Args:
        ignore_files: List of ignore file names
        root_dir: Root directory (defaults to current working directory)

    Returns:
        Configured IgnoreManager instance with loaded patterns
    """
    root_dir = root_dir or Path.cwd()
    spec = load_ignore_patterns(ignore_files, root_dir)
    return IgnoreManager(
        ignore_files=ignore_files,
        root_dir=root_dir,
        _spec=spec,
    )


# Convenience methods for the dataclass
def should_ignore(manager: IgnoreManager, file_path: Path) -> bool:
    """Check if a file should be ignored using an IgnoreManager."""
    return should_ignore_file(file_path, manager._spec, manager.root_dir)


def filter_files(manager: IgnoreManager, files: list[Path]) -> list[Path]:
    """Filter files using an IgnoreManager."""
    return filter_ignored_files(files, manager._spec, manager.root_dir)
