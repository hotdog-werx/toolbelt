import os
import tempfile
from pathlib import Path
from textwrap import dedent

import pytest
from pytest_mock import MockerFixture

from toolbelt.config import ToolbeltConfig
from toolbelt.config import loader as loader_mod
from toolbelt.config.loader import (
    load_config,
)
from toolbelt.config.file_loaders import (
    load_config_from_file,
    load_python_config,
    load_yaml_config,
)
from toolbelt.config.models import get_tool_command


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


def test_load_config_applies_environment_variables() -> None:
    """Test that environment variables are applied during config loading with correct precedence."""
    # Set up test environment variables
    test_env_vars = {
        'TB_TEST_VAR': 'env_value',
        'TB_OVERRIDE_VAR': 'env_override',
    }

    original_env = {}
    for key, value in test_env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    config_path = None
    try:
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.yaml',
            delete=False,
        ) as f:
            f.write("""
variables:
  config_var: "config_value"
  override_var: "config_override"  # This should be overridden by env var

profiles:
  test:
    name: "test"
    extensions: [".py"]
    check_tools:
      - name: "test_tool"
        command: "echo"
        args: ["${config_var}", "${TB_TEST_VAR}", "${TB_OVERRIDE_VAR}"]
    format_tools: []
""")
            config_path = Path(f.name)

        # Load config and verify environment variables are applied
        config = load_config([config_path])

        # Check that environment variables are in the final variables
        assert 'TB_TEST_VAR' in config.variables
        assert config.variables['TB_TEST_VAR'] == 'env_value'

        # Check that environment variables override config variables
        assert 'TB_OVERRIDE_VAR' in config.variables
        assert config.variables['TB_OVERRIDE_VAR'] == 'env_override'

        # Check that config variables are still present
        assert config.variables['config_var'] == 'config_value'

        # Test template expansion in tool command
        profile = config.get_profile('test')
        assert profile is not None
        tool = profile.check_tools[0]

        command = get_tool_command(tool, variables=config.get_variables())

        # The command should have expanded variables
        expected_args = ['echo', 'config_value', 'env_value', 'env_override']
        assert command.full_command == expected_args

    finally:
        # Clean up
        if config_path:
            config_path.unlink(missing_ok=True)
        # Restore original environment
        for key, original_value in original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value


def test_load_config_environment_variables_precedence_across_multiple_files() -> None:
    """Test that environment variables have highest precedence across multiple config files."""
    # Set up test environment variables
    os.environ['TB_MULTI_VAR'] = 'env_final_value'

    config_path1 = None
    config_path2 = None
    try:
        # Create two temporary config files
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='_base.yaml',
            delete=False,
        ) as f1:
            f1.write("""
variables:
  multi_var: "base_value"
  base_only: "base_only_value"

profiles:
  test:
    name: "test"
    extensions: [".py"]
    check_tools:
      - name: "test_tool"
        command: "echo"
        args: ["base"]
    format_tools: []
""")
            config_path1 = Path(f1.name)

        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='_override.yaml',
            delete=False,
        ) as f2:
            f2.write("""
variables:
  multi_var: "override_value"  # Should be overridden by env
  override_only: "override_only_value"

profiles:
  test:
    extensions: [".py"]
    check_tools:
      - name: "test_tool"
        command: "echo"
        args: ["${multi_var}", "${TB_MULTI_VAR}", "${base_only}", "${override_only}"]
    format_tools: []
""")
            config_path2 = Path(f2.name)

        # Load config from multiple sources
        config = load_config([config_path1, config_path2])

        # Verify final precedence: env > config2 > config1
        assert config.variables['TB_MULTI_VAR'] == 'env_final_value'  # env var
        assert config.variables['multi_var'] == 'override_value'  # config2 overrides config1
        assert config.variables['base_only'] == 'base_only_value'  # from config1
        assert config.variables['override_only'] == 'override_only_value'  # from config2

    finally:
        # Clean up
        if config_path1:
            config_path1.unlink(missing_ok=True)
        if config_path2:
            config_path2.unlink(missing_ok=True)
        os.environ.pop('TB_MULTI_VAR', None)
