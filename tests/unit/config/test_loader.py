from pathlib import Path
from textwrap import dedent

import pytest
from pytest_mock import MockerFixture

from toolbelt.config import ToolbeltConfig
from toolbelt.config import loader as loader_mod
from toolbelt.config.loader import (
    load_config,
    load_config_from_file,
    load_python_config,
    load_yaml_config,
)


def test_load_yaml_config_valid(sample_yaml_config: Path) -> None:
    """Test loading a valid YAML config file."""
    result = load_yaml_config(sample_yaml_config)
    assert isinstance(result, ToolbeltConfig)
    assert result.get_profile('python') is not None
    assert result.global_exclude_patterns == ['**/__pycache__/**', '*.pyc']


def test_load_yaml_config_invalid(tmp_path: Path) -> None:
    """Test that it raises ValueError on invalid YAML."""
    config_file = tmp_path / 'invalid.yaml'
    config_file.write_text('invalid: yaml: content:')
    with pytest.raises(ValueError, match='Error loading YAML config file'):
        load_yaml_config(config_file)


def test_load_yaml_config_not_found() -> None:
    """Test that it raises ValueError on file not found."""
    with pytest.raises(ValueError, match='Error loading YAML config file'):
        load_yaml_config(Path('nonexistent.yaml'))


def test_load_yaml_config_invalid_config(tmp_path: Path) -> None:
    """Test that it raises ValueError on validation error."""
    config_file = tmp_path / 'invalid_structure.yaml'
    # Create a config with invalid tool structure that will fail validation
    config_file.write_text(
        dedent("""
    profiles:
    python:
        extensions: ['.py']
        check:
        - name: 123  # Invalid: name should be string, not number
            command: test
    """),
    )
    with pytest.raises(ValueError, match='Error loading YAML config file'):
        load_yaml_config(config_file)


def test_load_python_config_valid(sample_python_config: Path) -> None:
    """Test loading a valid Python config file with dict config."""
    result = load_python_config(sample_python_config)
    assert isinstance(result, ToolbeltConfig)
    assert 'python' in result.profiles
    assert result.global_exclude_patterns == ['**/__pycache__/**', '*.pyc']


def test_load_python_config_load_instance(tmp_path: Path) -> None:
    """Test loading Python config file with ToolbeltConfig instance."""
    config_file = tmp_path / 'toolbelt_instance.py'
    config_file.write_text(
        dedent("""
        from toolbelt.config import ToolbeltConfig

        config = ToolbeltConfig()
    """),
    )
    result = load_python_config(config_file)
    assert isinstance(result, ToolbeltConfig)


def test_load_python_config_load_dict(tmp_path: Path) -> None:
    """Test loading Python config file with ToolbeltConfig instance."""
    config_file = tmp_path / 'toolbelt_dict.py'
    config_file.write_text(
        dedent("""
        config = {
            'profiles': {
                'python': {
                    'extensions': ['.py'],
                    'check_tools': [],
                    'format_tools': [],
                }
            },
            'global_exclude_patterns': [],
            'variables': {},
        }
    """),
    )
    result = load_python_config(config_file)
    assert isinstance(result, ToolbeltConfig)


def test_load_python_config_missing_config(tmp_path: Path) -> None:
    """Test that it raises ValueError when config variable is missing."""
    config_file = tmp_path / 'no_config.py'
    config_file.write_text('other_variable = 42')
    with pytest.raises(ValueError, match="must define a 'config' variable"):
        load_python_config(config_file)


def test_load_python_config_invalid_config_type(tmp_path: Path) -> None:
    """Test that it raises ValueError when config is wrong type."""
    config_file = tmp_path / 'wrong_type.py'
    config_file.write_text("config = 'not a dict or toolbelt config'")
    with pytest.raises(
        ValueError,
        match='Config must be a dictionary or ToolbeltConfig instance',
    ):
        load_python_config(config_file)


def test_load_python_config_import_error(tmp_path: Path) -> None:
    """Test that it raises ValueError on import error."""
    config_file = tmp_path / 'syntax_error.py'
    config_file.write_text('config = {invalid python syntax')
    with pytest.raises(ValueError, match='Error loading Python config file'):
        load_python_config(config_file)
    with pytest.raises(ValueError, match='Error loading Python config file'):
        load_python_config(Path('nonexistent.py'))


def test_load_python_config_spec_is_none(mocker: MockerFixture) -> None:
    """Test that it raises ValueError when spec is None."""
    mocker.patch('importlib.util.spec_from_file_location', return_value=None)
    with pytest.raises(ValueError, match='Could not load Python config'):
        load_python_config(Path('test.py'))


def test_load_config_from_file_loads_yml_file(tmp_path: Path) -> None:
    """Test loading config from YML file."""
    config_file = tmp_path / 'test.yml'
    config_file.write_text('profiles: {}')
    result = load_config_from_file(config_file)
    assert isinstance(result, ToolbeltConfig)


@pytest.mark.parametrize(
    'config_fixture',
    ['sample_yaml_config', 'sample_python_config'],
)
def test_load_config_from_file_types(
    request: pytest.FixtureRequest,
    config_fixture: str,
) -> None:
    config_path: Path = request.getfixturevalue(config_fixture)
    result = load_config_from_file(config_path)
    assert isinstance(result, ToolbeltConfig)


def test_load_config_unsupported_file_type(tmp_path: Path) -> None:
    """Test that it raises ValueError for unsupported file types."""
    config_file = tmp_path / 'test.json'
    config_file.write_text('{"profiles": {}}')
    with pytest.raises(ValueError, match='Unsupported configuration file type'):
        load_config_from_file(config_file)


def test_load_config_found(
    sample_yaml_config: Path,
    mocker: MockerFixture,
) -> None:
    """Test that load_config loads found config file."""
    mocker.patch.object(
        loader_mod,
        'find_config_sources',
        return_value=[sample_yaml_config],
    )
    result = load_config()
    assert isinstance(result, ToolbeltConfig)
    assert 'python' in result.profiles


def test_load_config_default(mocker: MockerFixture) -> None:
    """Test that load_config returns default config when no file is found."""
    mocker.patch.object(
        loader_mod,
        'find_config_sources',
        return_value=[],
    )
    result = load_config()
    assert isinstance(result, ToolbeltConfig)
    # Should be default config with standard profiles
    assert 'python' in result.profiles
    assert result.sources == ['__default__']


def test_load_config_specific_config_path(sample_yaml_config: Path) -> None:
    """Test that load_config can load a specific config path."""
    result = load_config([sample_yaml_config])
    assert isinstance(result, ToolbeltConfig)
    assert 'python' in result.profiles


def test_load_config_default_when_no_file(mocker: MockerFixture) -> None:
    """Test that load_config calls get_default_config when no file found."""
    mocker.patch.object(
        loader_mod,
        'find_config_sources',
        return_value=[],
    )
    mock_config = ToolbeltConfig(sources=['__made_up_default__'])
    mocker.patch.object(
        loader_mod,
        'get_default_config',
        return_value=mock_config,
    )

    result = load_config([])
    assert result is mock_config
    assert result.sources == ['__made_up_default__']


def test_load_config_multiple(
    sample_yaml_config: Path,
    sample_python_config: Path,
) -> None:
    """Test that load_config can load a specific config path."""
    result = load_config([sample_yaml_config, sample_python_config])
    assert isinstance(result, ToolbeltConfig)
    assert result.sources == [
        str(sample_yaml_config),
        str(sample_python_config),
    ]
