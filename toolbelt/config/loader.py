import os
from pathlib import Path

from .defaults import get_default_config
from .discovery import find_config_sources
from .file_loaders import load_config_from_file
from .models import ToolbeltConfig


def get_env_variables_context() -> dict[str, str]:
    """Get environment variables that are safe to use in templates.

    Only allows variables with specific prefixes to avoid exposing sensitive data.

    Returns:
        Dictionary of filtered environment variables.
    """
    allowed_prefixes = ('TOOLBELT_', 'TB_', 'TBELT_', 'CI_', 'BUILD_')
    return {k: v for k, v in os.environ.items() if any(k.startswith(prefix) for prefix in allowed_prefixes)}


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
