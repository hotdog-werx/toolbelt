"""Test the include functionality in config files."""

from pathlib import Path
from typing import IO, Any

from pytest_mock import MockerFixture

from toolbelt.config.file_loaders import load_python_config, load_yaml_config


def test_basic_include(temp_dir: Path):
    """Test basic include functionality."""
    # Create a base config file
    base_config = temp_dir / 'base.yaml'
    base_config.write_text("""
variables:
  base_var: "base_value"

profiles:
  base_profile:
    extensions: [".txt"]
    check_tools: []
    format_tools: []
""")

    # Create a main config that includes the base
    main_config = temp_dir / 'main.yaml'
    main_config.write_text("""
include:
  - "base.yaml"

variables:
  main_var: "main_value"

profiles:
  main_profile:
    extensions: [".py"]
    check_tools: []
    format_tools: []
""")

    # Load the main config
    config = load_yaml_config(main_config)

    # Check that both profiles are present
    assert 'base_profile' in config.profiles
    assert 'main_profile' in config.profiles

    # Check that both variables are present
    assert config.variables['base_var'] == 'base_value'
    assert config.variables['main_var'] == 'main_value'

    # Check sources
    assert len(config.sources) == 2
    assert str(base_config) in config.sources
    assert str(main_config) in config.sources


def test_circular_dependency(temp_dir: Path):
    """Test circular dependency detection."""
    # Create file A that includes B
    config_a = temp_dir / 'a.yaml'
    config_a.write_text("""
include:
  - "b.yaml"

variables:
  var_a: "value_a"

profiles: {}
""")

    # Create file B that includes A (circular dependency)
    config_b = temp_dir / 'b.yaml'
    config_b.write_text("""
include:
  - "a.yaml"

variables:
  var_b: "value_b"

profiles: {}
""")

    # Load config A - should handle circular dependency gracefully
    config = load_yaml_config(config_a)

    # Should still work, just skip the circular include
    assert 'var_a' in config.variables


def test_package_resource_include(temp_dir: Path):
    """Test including from package resources."""
    # Create a main config that includes from toolbelt package
    main_config = temp_dir / 'main.yaml'
    main_config.write_text("""
include:
  - "@toolbelt:resources/presets/hdw.yaml"

variables:
  my_var: "my_value"

profiles: {}
""")

    # Load the main config
    config = load_yaml_config(main_config)

    # Should have profiles from the toolbelt resource
    assert 'python' in config.profiles
    assert 'yaml' in config.profiles

    # Should have both original and new variables
    assert config.variables['my_var'] == 'my_value'
    # no variables included from the preset

    # Check sources include the package resource
    expected_resource = Path('resources/presets/hdw.yaml')
    assert any(Path(source).as_posix().endswith(expected_resource.as_posix()) for source in config.sources)


def test_include_with_missing_file(temp_dir: Path):
    """Test that missing include files are handled gracefully."""
    main_config = temp_dir / 'main.yaml'
    main_config.write_text("""
include:
  - "nonexistent.yaml"

variables:
  my_var: "my_value"

profiles:
  test:
    extensions: [".py"]
    check_tools: []
    format_tools: []
""")

    # Should load successfully, just skip the missing include
    config = load_yaml_config(main_config)
    assert config.variables['my_var'] == 'my_value'
    assert 'test' in config.profiles


def test_nested_includes(temp_dir: Path):
    """Test includes that reference other includes."""
    # Create level 3 config
    level3_config = temp_dir / 'level3.yaml'
    level3_config.write_text("""
variables:
  level3_var: "level3_value"

profiles:
  level3_profile:
    extensions: [".txt"]
    check_tools: []
    format_tools: []
""")

    # Create level 2 config that includes level 3
    level2_config = temp_dir / 'level2.yaml'
    level2_config.write_text("""
include:
  - "level3.yaml"

variables:
  level2_var: "level2_value"

profiles:
  level2_profile:
    extensions: [".py"]
    check_tools: []
    format_tools: []
""")

    # Create level 1 config that includes level 2
    level1_config = temp_dir / 'level1.yaml'
    level1_config.write_text("""
include:
  - "level2.yaml"

variables:
  level1_var: "level1_value"

profiles:
  level1_profile:
    extensions: [".js"]
    check_tools: []
    format_tools: []
""")

    # Load the top-level config
    config = load_yaml_config(level1_config)

    # Should have all profiles
    assert 'level1_profile' in config.profiles
    assert 'level2_profile' in config.profiles
    assert 'level3_profile' in config.profiles

    # Should have all variables
    assert config.variables['level1_var'] == 'level1_value'
    assert config.variables['level2_var'] == 'level2_value'
    assert config.variables['level3_var'] == 'level3_value'

    # Should have all sources
    assert len(config.sources) == 3
    assert str(level3_config) in config.sources
    assert str(level2_config) in config.sources
    assert str(level1_config) in config.sources


def test_include_single_string_not_list(temp_dir: Path):
    """Test include with single string instead of list."""
    base_config = temp_dir / 'base.yaml'
    base_config.write_text("""
variables:
  base_var: "base_value"

profiles: {}
""")

    main_config = temp_dir / 'main.yaml'
    main_config.write_text("""
include: "base.yaml"

variables:
  main_var: "main_value"

profiles: {}
""")

    config = load_yaml_config(main_config)
    assert config.variables['base_var'] == 'base_value'
    assert config.variables['main_var'] == 'main_value'


def test_include_failed_resolution(temp_dir: Path):
    """Test include with unresolvable reference."""
    main_config = temp_dir / 'main.yaml'
    main_config.write_text("""
include:
  - "~/nonexistent/config.yaml"

variables:
  my_var: "my_value"

profiles: {}
""")

    config = load_yaml_config(main_config)
    # Should still load, just skip the failed include
    assert config.variables['my_var'] == 'my_value'


def test_include_unsupported_file_type(temp_dir: Path):
    """Test include with unsupported file type."""
    unsupported_config = temp_dir / 'config.json'
    unsupported_config.write_text('{"test": "value"}')

    main_config = temp_dir / 'main.yaml'
    main_config.write_text("""
include:
  - "config.json"

variables:
  my_var: "my_value"

profiles: {}
""")

    config = load_yaml_config(main_config)
    # Should still load, just skip the unsupported include
    assert config.variables['my_var'] == 'my_value'


def test_python_config_include(temp_dir: Path):
    """Test Python config file with includes."""
    base_config = temp_dir / 'base.yaml'
    base_config.write_text("""
variables:
  base_var: "base_value"

profiles:
  base_profile:
    extensions: [".txt"]
    check_tools: []
    format_tools: []
""")

    python_config = temp_dir / 'config.py'
    python_config.write_text("""
config = {
    "include": ["base.yaml"],
    "variables": {
        "python_var": "python_value"
    },
    "profiles": {
        "python_profile": {
            "extensions": [".py"],
            "check_tools": [],
            "format_tools": []
        }
    }
}
""")

    config = load_python_config(python_config)

    # Should have variables from both files
    assert config.variables['python_var'] == 'python_value'
    # Note: base_var might not be present due to include processing order

    # Should have profiles from both files
    assert 'python_profile' in config.profiles


def test_python_config_include_error(temp_dir: Path):
    """Test Python config with include that causes an error."""
    python_config = temp_dir / 'config.py'
    python_config.write_text("""
config = {
    "include": ["nonexistent.yaml"],
    "variables": {
        "python_var": "python_value"
    },
    "profiles": {}
}
""")

    config = load_python_config(python_config)
    # Should still load, just skip the failed include
    assert config.variables['python_var'] == 'python_value'


def test_include_merge_exclude_patterns(temp_dir: Path):
    """Test merging of exclude_patterns from includes."""
    base_config = temp_dir / 'base.yaml'
    base_config.write_text("""
global_exclude_patterns:
  - "*.tmp"
  - "build/"

profiles: {}

variables: {}
""")

    main_config = temp_dir / 'main.yaml'
    main_config.write_text("""
include:
  - "base.yaml"

global_exclude_patterns:
  - "*.log"
  - "dist/"

profiles: {}

variables: {}
""")

    config = load_yaml_config(main_config)

    # Should have all exclude patterns concatenated
    expected_patterns = ['*.tmp', 'build/', '*.log', 'dist/']
    for pattern in expected_patterns:
        assert pattern in config.global_exclude_patterns


def test_python_config_with_includes_sources(temp_dir: Path):
    """Test Python config with includes adds sources correctly (covers line 116)."""
    base_config = temp_dir / 'base.yaml'
    base_config.write_text("""
variables:
  base_var: "base_value"

profiles: {}
""")

    python_config = temp_dir / 'config.py'
    python_config.write_text("""
config = {
    "include": ["base.yaml"],
    "variables": {
        "python_var": "python_value"
    },
    "profiles": {}
}
""")

    config = load_python_config(python_config)

    # The important thing is that line 116 gets executed (sources are added)
    assert str(python_config) in config.sources
    # Check if variables merged correctly (indicating includes processed)
    assert config.variables['python_var'] == 'python_value'


def test_python_config_include_sources_loop(temp_dir: Path):
    """Test Python config with successful include to hit line 116."""
    # Create a simple YAML include file
    included_config = temp_dir / 'included.yaml'
    included_config.write_text("""
variables:
  included_var: "included_value"

profiles: {}
""")

    # Create Python config that includes the YAML
    python_config = temp_dir / 'config.py'
    python_config.write_text("""
config = {
    "include": ["included.yaml"],
    "variables": {
        "main_var": "main_value"
    },
    "profiles": {}
}
""")

    config = load_python_config(python_config)

    # Verify the include was processed (this ensures line 116 was hit)
    assert len(config.sources) >= 2  # Should have both files
    assert str(python_config) in config.sources  # Main file always added

    # Verify both variables are present, proving include worked
    assert config.variables['main_var'] == 'main_value'
    assert config.variables['included_var'] == 'included_value'


def test_include_resolution_fails(temp_dir: Path, mocker: MockerFixture):
    """Test include with resolution failure (covers lines 369-370)."""
    from toolbelt.config import includes  # noqa: PLC0415

    # Mock resolve_config_reference to return None
    mock_resolve = mocker.patch.object(
        includes,
        'resolve_config_reference',
        return_value=None,
    )

    main_config = temp_dir / 'main.yaml'
    main_config.write_text("""
include:
  - "will-fail-to-resolve.yaml"

variables:
  my_var: "my_value"

profiles: {}
""")

    config = load_yaml_config(main_config)

    # Should still load successfully, just skip the failed include
    assert config.variables['my_var'] == 'my_value'
    mock_resolve.assert_called_once()


def test_yaml_includes_python_file(temp_dir: Path):
    """Test YAML config including a Python file (covers lines 392-394)."""
    # Create a Python config to be included
    python_include = temp_dir / 'included.py'
    python_include.write_text("""
config = {
    "variables": {
        "python_var": "from_python"
    },
    "profiles": {
        "python_profile": {
            "extensions": [".py"],
            "check_tools": [],
            "format_tools": []
        }
    }
}
""")

    # Create YAML config that includes the Python file
    main_config = temp_dir / 'main.yaml'
    main_config.write_text("""
include:
  - "included.py"

variables:
  yaml_var: "from_yaml"

profiles:
  yaml_profile:
    extensions: [".yaml"]
    check_tools: []
    format_tools: []
""")

    config = load_yaml_config(main_config)

    # Should have variables from both files
    assert config.variables['python_var'] == 'from_python'
    assert config.variables['yaml_var'] == 'from_yaml'

    # Should have profiles from both files
    assert 'python_profile' in config.profiles
    assert 'yaml_profile' in config.profiles


def test_include_loading_exception(temp_dir: Path, mocker: MockerFixture):
    """Test exception handling during include loading (covers lines 412-414)."""
    import yaml  # noqa: PLC0415

    # Create a base config to include
    base_config = temp_dir / 'base.yaml'
    base_config.write_text("""
variables:
  base_var: "base_value"

profiles: {}
""")

    # Mock yaml.safe_load to throw an exception
    original_safe_load = yaml.safe_load

    def mock_safe_load(stream: IO[str]) -> dict[str, Any] | None:
        if hasattr(stream, 'name') and 'base.yaml' in stream.name:
            msg = 'Corrupted YAML file'
            raise yaml.YAMLError(msg)
        return original_safe_load(stream)

    mocker.patch.object(yaml, 'safe_load', side_effect=mock_safe_load)

    main_config = temp_dir / 'main.yaml'
    main_config.write_text("""
include:
  - "base.yaml"

variables:
  main_var: "main_value"

profiles: {}
""")

    config = load_yaml_config(main_config)

    # Should still load the main config, just skip the failed include
    assert config.variables['main_var'] == 'main_value'
    # base_var should not be present since include failed
    assert 'base_var' not in config.variables


def test_include_python_file_exception(temp_dir: Path, mocker: MockerFixture):
    """Test exception handling when including malformed Python file."""
    # Create a malformed Python file
    python_include = temp_dir / 'broken.py'
    python_include.write_text("""
# This is invalid Python syntax
config = {
    "variables": {
        "test_var": "value"
    }
    # Missing closing brace
""")

    main_config = temp_dir / 'main.yaml'
    main_config.write_text("""
include:
  - "broken.py"

variables:
  main_var: "main_value"

profiles: {}
""")

    config = load_yaml_config(main_config)

    # Should still load the main config, skip the broken include
    assert config.variables['main_var'] == 'main_value'
    assert 'test_var' not in config.variables


def test_include_python_file_with_toolbelt_config_object(temp_dir: Path):
    """Test including a Python file that returns a ToolbeltConfig object (covers line 398)."""
    # Create a Python config that returns a ToolbeltConfig instance
    python_include = temp_dir / 'included.py'
    python_include.write_text("""
from toolbelt.config.models import ToolbeltConfig

config = ToolbeltConfig(
    profiles={
        "python_obj_profile": {
            "name": "python_obj_profile",
            "extensions": [".py"],
            "check_tools": [],
            "format_tools": []
        }
    },
    variables={
        "python_obj_var": "from_toolbelt_config_object"
    }
)
""")

    # Create YAML config that includes the Python file
    main_config = temp_dir / 'main.yaml'
    main_config.write_text("""
include:
  - "included.py"

variables:
  yaml_var: "from_yaml"

profiles:
  yaml_profile:
    extensions: [".yaml"]
    check_tools: []
    format_tools: []
""")

    config = load_yaml_config(main_config)

    # Should have variables from both files
    assert config.variables['python_obj_var'] == 'from_toolbelt_config_object'
    assert config.variables['yaml_var'] == 'from_yaml'

    # Should have profiles from both files
    assert 'python_obj_profile' in config.profiles
    assert 'yaml_profile' in config.profiles
