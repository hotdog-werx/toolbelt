import re
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


def expand_template_strings(
    args: list[str],
    variables: dict[str, str],
) -> list[str]:
    """Expand ${VAR:default} placeholders in a list of strings using variables dict.

    Args:
        args: List of strings containing template variables.
        variables: Dictionary of variable values.

    Returns:
        List of strings with template variables expanded.
    """
    return [expand_template_string(arg, variables) for arg in args]


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
