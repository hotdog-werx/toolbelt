from pathlib import Path

from .file_loaders import load_yaml_config
from .models import ToolbeltConfig


def get_default_config() -> ToolbeltConfig:
    """Return a default configuration using the hdw.yaml preset."""
    # Load the hdw.yaml preset as the default config
    preset_path = Path(__file__).parent.parent / 'resources' / 'presets' / 'hdw.yaml'
    return load_yaml_config(preset_path)
