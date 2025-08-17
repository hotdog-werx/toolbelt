import re
import shlex
from re import Match


def _replace_template_var(match: Match[str], variables: dict[str, str]) -> str:
    var_name = match.group(1)
    default_value = match.group(2) if match.group(2) is not None else ''
    return variables.get(var_name, default_value)


def expand_template_string(arg: str, variables: dict[str, str]) -> str:
    """Expand ${VAR:default} placeholders in a string using variables dict.

    Args:
        arg: The string containing template variables.
        variables: Dictionary of variable values.

    Returns:
        The string with template variables expanded.
    """
    pattern = re.compile(r'\$\{([^:}]+)(?::([^}]*))?\}')
    return pattern.sub(lambda m: _replace_template_var(m, variables), arg)


def _process_expanded_argument(expanded: str, original_arg: str) -> list[str]:
    """Process a single expanded argument, splitting if necessary.

    Args:
        expanded: The expanded argument string.
        original_arg: The original argument before expansion.

    Returns:
        List of argument strings (may be split or single item).
    """
    # Skip empty strings to keep commands clean
    if not expanded:
        return []

    # If the expanded string contains spaces and the original contained a template,
    # split it into multiple arguments using shell-like parsing
    if ' ' in expanded and '${' in original_arg:
        try:
            # Use shlex to properly handle quoted arguments
            split_args = shlex.split(expanded)
            # Filter out any empty strings from splitting
            return [arg for arg in split_args if arg]
        except ValueError:
            # If shlex parsing fails, treat as single argument
            return [expanded]

    return [expanded]


def expand_template_strings(
    args: list[str],
    variables: dict[str, str],
) -> list[str]:
    """Expand ${VAR:default} placeholders in a list of strings using variables dict.

    If a template variable expands to a string containing spaces, it will be
    automatically split into multiple arguments using shell-like parsing.
    This enables dynamic argument lists like:

    args: ["${TB_COVERAGE_PATHS:--cov=src}"]
    TB_COVERAGE_PATHS="--cov=toolbelt --cov=tests"
    Result: ["--cov=toolbelt", "--cov=tests"]

    Empty strings are automatically filtered out to keep commands clean.

    Args:
        args: List of strings containing template variables.
        variables: Dictionary of variable values.

    Returns:
        List of strings with template variables expanded and split if needed.
    """
    expanded_args: list[str] = []

    for arg in args:
        expanded = expand_template_string(arg, variables)
        processed_args = _process_expanded_argument(expanded, arg)
        expanded_args.extend(processed_args)

    return expanded_args


def normalize_extensions(extensions: list[str]) -> list[str]:
    """Ensure extensions start with a dot.

    Args:
        extensions: List of file extensions to normalize.

    Returns:
        List of normalized file extensions.
    """
    validated: list[str] = []
    for ext in extensions:
        ext_to_append = ext
        if not ext.startswith('.'):
            ext_to_append = f'.{ext}'
        validated.append(ext_to_append)
    return validated
