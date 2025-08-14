from pathlib import Path

from toolbelt.config import ProfileConfig
from toolbelt.ignore import IgnoreManager, create_ignore_manager
from toolbelt.logging import get_logger

logger = get_logger(__name__)


def get_target_files(
    profile: ProfileConfig,
    files: list[Path] | None,
    global_exclude_patterns: list[str],
    *,
    verbose: bool = False,
) -> list[Path]:
    """Get the list of files to process."""
    if files:
        return _filter_existing_and_matching_files(profile, files)
    return find_files_by_extensions(
        profile.extensions,
        profile.exclude_patterns,
        profile.ignore_files,
        global_exclude_patterns,
        verbose=verbose,
    )


def find_files_by_extensions(
    extensions: list[str],
    exclude_patterns: list[str],
    ignore_files: list[str],
    global_exclude_patterns: list[str],
    *,
    verbose: bool = False,
) -> list[Path]:
    """Find all files with the specified extensions, excluding patterns and respecting ignore files."""
    ignore_manager = create_ignore_manager(ignore_files or ['.gitignore'])
    all_exclude_patterns = exclude_patterns + global_exclude_patterns
    all_files = []

    for extension in extensions:
        all_files.extend(
            _find_files_for_extension(
                extension,
                ignore_manager,
                all_exclude_patterns,
            ),
        )

    if verbose and all_files:
        logger.info(
            'Found files after applying ignore rules',
            count=len(all_files),
        )

    return sorted(all_files)


def _file_matches_extensions(file_path: Path, extensions: list[str]) -> bool:
    """Return True if file_path exists and matches extensions (or '.*')."""
    if not file_path.exists():
        logger.warning('File not found', file=str(file_path))
        return False
    return '.*' in extensions or file_path.suffix in extensions


def _filter_existing_and_matching_files(
    profile: ProfileConfig,
    files: list[Path],
) -> list[Path]:
    """Return only files that exist and match the language extensions."""
    extensions = profile.extensions
    result = []
    for file_path in files:
        if file_path.is_dir():
            result.extend(
                [f for ext in extensions for f in file_path.rglob(f'*{ext}') if f.is_file()],
            )
        elif _file_matches_extensions(file_path, extensions):
            result.append(file_path)
    return sorted(result)


def _find_files_for_extension(
    extension: str,
    ignore_manager: IgnoreManager,
    all_exclude_patterns: list[str],
) -> list[Path]:
    """Find files for a single extension, applying ignore and exclude patterns."""
    files = list(Path().rglob(f'*{extension}'))
    result = []
    for file_path in files:
        if ignore_manager.should_ignore(file_path):
            continue
        if _should_exclude_file(file_path, all_exclude_patterns):
            continue
        result.append(file_path)
    return result


def _should_exclude_file(file_path: Path, exclude_patterns: list[str]) -> bool:
    return any(file_path.match(pattern) for pattern in exclude_patterns)
