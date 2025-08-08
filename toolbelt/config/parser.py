from typing import Any

from .models import ToolbeltConfig


def parse_toolbelt_config(data: dict[str, Any]) -> ToolbeltConfig:
    """Parse configuration data into ToolbeltConfig using full Pydantic validation.

    Args:
        data: Raw configuration data as a dictionary.

    Returns:
        ToolbeltConfig: Parsed configuration object.
    """
    # Add name if missing
    for profile_name, profile_data in data.get('profiles', {}).items():
        if not profile_data.get('name'):
            profile_data['name'] = profile_name

    # Let Pydantic validate and parse everything
    return ToolbeltConfig.model_validate(data)
