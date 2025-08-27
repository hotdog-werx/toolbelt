from pathlib import Path
from textwrap import dedent

from toolbelt.config.loader import load_config


def test_load_config_merges_multiple_sources(tmp_path: Path):
    """Test load_config merges multiple config files correctly."""
    base_file = tmp_path / 'base.yaml'
    base_file.write_text(
        dedent("""\
        profiles:
          python:
            extensions: [".py"]
            check_tools: []
            format_tools: []
        global_exclude_patterns: ["*.pyc"]
    """),
    )
    override_file = tmp_path / 'override.yaml'
    override_file.write_text(
        dedent("""\
        profiles:
          javascript:
            extensions: [".js"]
            check_tools: []
            format_tools: []
        global_exclude_patterns: ["node_modules/**"]
    """),
    )
    config = load_config([base_file, override_file])
    assert set(config.profiles.keys()) == {'python', 'javascript'}
    assert config.global_exclude_patterns == ['*.pyc', 'node_modules/**']


def test_load_config_explicit_path(tmp_path: Path):
    """Test load_config with explicit config path."""
    config_file = tmp_path / 'custom.yaml'
    config_file.write_text('profiles: {}')
    config = load_config([config_file])
    assert config.sources == [str(config_file)]


def test_load_config_with_pyproject_include(tmp_path: Path):
    """Test load_config discovers sources from pyproject.toml include."""
    pyproject_file = tmp_path / 'pyproject.toml'
    pyproject_file.write_text('[tool.toolbelt]\ninclude = ["toolbelt.yaml"]\n')
    yaml_file = tmp_path / 'toolbelt.yaml'
    yaml_file.write_text('profiles:\n  python:\n    extensions: [".py"]')
    config = load_config()
    assert 'python' in config.profiles


def test_load_config_yaml(tmp_path: Path):
    """Test load_config loads a simple YAML config file."""
    yaml_file = tmp_path / 'toolbelt.yaml'
    yaml_file.write_text(
        dedent("""\
        profiles:
          python:
            extensions: [".py"]
            check_tools: []
            format_tools: []
    """),
    )
    config = load_config([yaml_file])
    assert 'python' in config.profiles
    assert config.profiles['python'].extensions == ['.py']


def test_load_config_default_sources():
    """Test that load_config returns default config when no sources found."""
    config = load_config([])
    # Should include hdw.yaml preset as a source
    assert any('hdw.yaml' in src for src in config.sources)
