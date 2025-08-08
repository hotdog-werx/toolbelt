import pytest
from pydantic import ValidationError

from toolbelt.config.models import ToolbeltConfig
from toolbelt.config.parser import parse_toolbelt_config


def test_parse_minimal_config() -> None:
    config = parse_toolbelt_config({'profiles': {}})
    assert isinstance(config, ToolbeltConfig)
    assert config.profiles == {}
    assert config.global_exclude_patterns == []


def test_parse_complete_config() -> None:
    raw = {
        'profiles': {
            'python': {
                'extensions': ['.py'],
                'check_tools': [
                    {'name': 'ruff', 'command': 'ruff', 'args': ['check']},
                ],
                'format_tools': [
                    {
                        'name': 'pyright',
                        'command': 'pyright',
                        'args': ['--check'],
                    },
                ],
                'exclude_patterns': ['__pycache__/**'],
                'ignore_files': ['.gitignore', '.flake8ignore'],
            },
        },
        'global_exclude_patterns': ['*.pyc'],
        'variables': {'TOOLBELT_RUFF_VERSION': 'latest'},
    }
    config = parse_toolbelt_config(raw)
    assert 'python' in config.profiles
    profile = config.profiles['python']
    assert profile.extensions == ['.py']
    assert len(profile.check_tools) == 1
    assert len(profile.format_tools) == 1
    assert profile.exclude_patterns == ['__pycache__/**']
    assert profile.ignore_files == ['.gitignore', '.flake8ignore']
    assert config.global_exclude_patterns == ['*.pyc']
    assert config.variables == {'TOOLBELT_RUFF_VERSION': 'latest'}


def test_parse_invalid_config_raises() -> None:
    raw = {
        'profiles': {
            'python': {
                'extensions': [123],  # Invalid type
            },
        },
    }
    with pytest.raises(ValidationError):
        parse_toolbelt_config(raw)
