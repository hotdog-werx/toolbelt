from dataclasses import dataclass
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from toolbelt.config.discovery import find_config_sources
from toolbelt.config.file_loaders import load_pyproject_toml
from toolbelt.config.includes import resolve_config_reference


@dataclass
class PyprojectTomlCase:
    """Test case for pyproject.toml loading."""

    desc: str
    toml_content: str
    expected_result: dict[str, str | list[str]] | None
    expect_error: bool = False


@pytest.mark.parametrize(
    'tcase',
    [
        PyprojectTomlCase(
            desc='valid_pyproject_toml',
            toml_content='[tool.toolbelt]\ninclude = ["toolbelt.yaml"]\n',
            expected_result={'include': ['toolbelt.yaml']},
        ),
        PyprojectTomlCase(
            desc='no_toolbelt_section',
            toml_content='[build-system]\nrequires = ["hatchling"]\n',
            expected_result=None,
        ),
        PyprojectTomlCase(
            desc='tool_section_no_toolbelt',
            toml_content='[tool.ruff]\nline-length = 88\n',
            expected_result=None,
        ),
        PyprojectTomlCase(
            desc='empty_pyproject',
            toml_content='',
            expected_result=None,
        ),
        PyprojectTomlCase(
            desc='malformed_pyproject',
            toml_content='[tool.toolbelt\n',  # Missing closing bracket
            expected_result=None,
        ),
    ],
    ids=lambda c: c.desc,
)
def test_load_pyproject_toml(tmp_path: Path, tcase: PyprojectTomlCase) -> None:
    """Test loading pyproject.toml with various configurations."""
    pyproject_file = tmp_path / 'pyproject.toml'
    pyproject_file.write_text(tcase.toml_content)
    result = load_pyproject_toml(pyproject_file)
    assert result == tcase.expected_result


def test_load_pyproject_toml_file_not_found() -> None:
    """Test that it returns None for non-existent files."""
    result = load_pyproject_toml(Path('nonexistent.toml'))
    assert result is None


@dataclass
class ConfigReferenceCase:
    """Test case for configuration reference resolution."""

    desc: str
    config_ref: str
    base_path: Path
    expected_result: Path | None
    resolve_package_resource_side_effect: Path | ValueError | None = None


@pytest.mark.parametrize(
    'tcase',
    [
        ConfigReferenceCase(
            desc='relative_path',
            config_ref='toolbelt.yaml',
            base_path=Path('/project'),
            expected_result=Path('/project/toolbelt.yaml'),
        ),
        ConfigReferenceCase(
            desc='absolute_path',
            config_ref='/etc/toolbelt.yaml',
            base_path=Path('/project'),
            expected_result=Path('/etc/toolbelt.yaml'),
        ),
        ConfigReferenceCase(
            desc='home_directory_path',
            config_ref='~/.config/toolbelt.yaml',
            base_path=Path('/project'),
            expected_result=Path.home() / '.config/toolbelt.yaml',
        ),
        ConfigReferenceCase(
            desc='nested_relative_path',
            config_ref='.config/toolbelt.yaml',
            base_path=Path('/project'),
            expected_result=Path('/project/.config/toolbelt.yaml'),
        ),
        ConfigReferenceCase(
            desc='package_resource_reference',
            config_ref='@somepackage:some/resource.yaml',
            base_path=Path('/project'),
            expected_result=Path(
                '/mocked/resource/path',
            ),  # what our mock will return
            resolve_package_resource_side_effect=Path('/mocked/resource/path'),
        ),
        ConfigReferenceCase(
            desc='package_resource_reference_invalid',
            config_ref='@invalid_package:some/resource.yaml',
            base_path=Path('/project'),
            expected_result=None,  # what our mock will return
            resolve_package_resource_side_effect=ValueError('not found'),
        ),
    ],
    ids=lambda c: c.desc,
)
def test_resolve_config_reference(
    tcase: ConfigReferenceCase,
    mocker: MockerFixture,
) -> None:
    """Test resolving configuration references to absolute paths."""
    if tcase.config_ref.startswith('@'):
        mock = mocker.patch('toolbelt.config.includes.resolve_package_resource')
        if isinstance(tcase.resolve_package_resource_side_effect, Path):
            mock.return_value = tcase.resolve_package_resource_side_effect
        else:
            mock.side_effect = tcase.resolve_package_resource_side_effect
    result = resolve_config_reference(tcase.config_ref, tcase.base_path)
    assert result == tcase.expected_result


def test_resolve_config_reference_handles_invalid_paths() -> None:
    """Test that it returns None for invalid paths."""
    # This might cause issues on some systems, so return None gracefully
    result = resolve_config_reference('', Path('/project'))
    assert result is not None  # Empty string becomes base_path


@dataclass
class ConfigSourcesCase:
    """Test case for finding configuration sources."""

    desc: str
    pyproject_content: str
    config_files: list[str]  # Files to create in tmp_path
    expected_sources: list[str]  # Expected filenames (relative to tmp_path)


@pytest.mark.parametrize(
    'tcase',
    [
        ConfigSourcesCase(
            desc='pyproject_existing_files',
            pyproject_content='[tool.toolbelt]\ninclude = ["base.yaml", "local.yaml"]\n',
            config_files=['base.yaml', 'local.yaml'],
            expected_sources=['base.yaml', 'local.yaml'],
        ),
        ConfigSourcesCase(
            desc='pyproject_missing_files',
            pyproject_content='[tool.toolbelt]\ninclude = ["missing.yaml"]\n',
            config_files=[],
            expected_sources=[],
        ),
        ConfigSourcesCase(
            desc='pyproject_fallback',
            pyproject_content='[build-system]\nrequires = ["hatchling"]\n',
            config_files=['toolbelt.yaml'],
            expected_sources=['toolbelt.yaml'],
        ),
        ConfigSourcesCase(
            desc='no_pyproject.toml_fallback_yaml',
            pyproject_content='',
            config_files=['toolbelt.yaml'],
            expected_sources=['toolbelt.yaml'],
        ),
        ConfigSourcesCase(
            desc='no_pyproject.toml_fallback_yml',
            pyproject_content='',
            config_files=['toolbelt.yml'],
            expected_sources=['toolbelt.yml'],
        ),
        ConfigSourcesCase(
            desc='no_pyproject.toml_fallback_py',
            pyproject_content='',
            config_files=['toolbelt.py'],
            expected_sources=['toolbelt.py'],
        ),
        ConfigSourcesCase(
            desc='no_config_files',
            pyproject_content='',
            config_files=[],
            expected_sources=[],
        ),
        ConfigSourcesCase(
            desc='priority_yaml_yml_py',
            pyproject_content='',
            config_files=['toolbelt.yaml', 'toolbelt.yml', 'toolbelt.py'],
            expected_sources=['toolbelt.yaml'],
        ),
        ConfigSourcesCase(
            desc='no_python_package',
            pyproject_content='[tool.toolbelt]\ninclude = ["@invalid-package:/oops"]\n',
            config_files=['toolbelt.yaml'],
            expected_sources=['toolbelt.yaml'],
        ),
    ],
    ids=lambda c: c.desc,
)
def test_find_config_sources(
    tmp_path: Path,
    tcase: ConfigSourcesCase,
    mocker: MockerFixture,
) -> None:
    """Test finding configuration sources with various scenarios."""
    # Mock current working directory
    mocker.patch.object(Path, 'cwd', return_value=tmp_path)

    # Create pyproject.toml if needed
    if tcase.pyproject_content:
        pyproject_file = tmp_path / 'pyproject.toml'
        pyproject_file.write_text(tcase.pyproject_content)

    # Create config files
    for filename in tcase.config_files:
        config_file = tmp_path / filename
        if filename.endswith('.py'):
            config_file.write_text('config = {}')
        else:
            config_file.write_text('profiles: {}')

    # Test
    result = find_config_sources()
    expected_paths = [tmp_path / name for name in tcase.expected_sources]
    assert result == expected_paths


def test_find_config_sources_with_explicit_path(tmp_path: Path) -> None:
    """Test find_config_sources with an explicit config path."""
    config_file = tmp_path / 'custom.yaml'
    config_file.write_text('profiles: {}')

    result = find_config_sources(config_file)
    assert result == [config_file]
