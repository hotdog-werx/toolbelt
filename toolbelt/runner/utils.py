"""Utility functions for the runner package."""

from pathlib import Path


def expand_globs_in_args(args: list[str]) -> list[str]:
    """Expand glob patterns in command arguments.

    Args:
        args: A list of command-line arguments.

    Returns:
        A list of expanded command-line arguments.
    """
    expanded_args = []

    for arg in args:
        # Check if the argument looks like a glob pattern (contains *, ?, or [])
        if any(char in arg for char in ['*', '?', '[']):
            # Try to expand as a glob pattern
            matches = [str(p) for p in Path().glob(arg)]
            if matches:
                # If we found matches, use them
                expanded_args.extend(matches)
            else:
                # If no matches, keep the original arg (might be a literal * or ?)
                expanded_args.append(arg)
        else:
            # Not a glob pattern, keep as-is
            expanded_args.append(arg)

    return expanded_args
