from dataclasses import dataclass
from typing import Any

import pytest
from pydantic import ValidationError

from toolbelt.config.models import (
    ProfileConfig,
    ToolbeltConfig,
    ToolConfig,
    get_tool_command,
)


def test_basic_tool_config() -> None:
    """Test creating a basic tool config."""
    tool = ToolConfig(
        name='test-tool',
        command='test-cmd',
        description='A test tool',
        args=[],
    )
    assert tool.name == 'test-tool'
    assert tool.command == 'test-cmd'
    assert tool.description == 'A test tool'
    assert tool.args == []
    assert tool.output_to_file is False
    # Defaults to files, we need to be explicit about the other modes
    assert tool.file_handling_mode == 'per_file'


@dataclass
class ValidationErrorCase:
    """Test case for validation errors."""

    desc: str
    kwargs: dict[str, Any]
    should_fail: bool


@pytest.mark.parametrize(
    'tcase',
    [
        ValidationErrorCase('no-params', {}, should_fail=True),
        ValidationErrorCase(
            'missing-command',
            {'name': 'test'},
            should_fail=True,
        ),
        ValidationErrorCase(
            'missing-name',
            {'command': 'test'},
            should_fail=True,
        ),
        ValidationErrorCase(
            'valid-minimal',
            {'name': 'test', 'command': 'cmd'},
            should_fail=False,
        ),
    ],
    ids=lambda c: c.desc,
)
def test_tool_config_validation_errors(tcase: ValidationErrorCase) -> None:
    """Test validation errors for required fields."""
    if tcase.should_fail:
        with pytest.raises(ValidationError):
            ToolConfig(**tcase.kwargs)
    else:
        tool = ToolConfig(args=[], **tcase.kwargs)
        assert tool.name == tcase.kwargs['name']
        assert tool.command == tcase.kwargs['command']


@dataclass
class FileHandlingCase:
    """Test case for support modes."""

    desc: str
    kwargs: dict[str, Any]
    expected_file_handling_mode: str
    can_discover_files: bool


@pytest.mark.parametrize(
    'tcase',
    [
        FileHandlingCase(
            'default',
            {},
            expected_file_handling_mode='per_file',
            can_discover_files=False,
        ),
        FileHandlingCase(
            'batch',
            {'file_handling_mode': 'batch'},
            expected_file_handling_mode='batch',
            can_discover_files=True,
        ),
        FileHandlingCase(
            'per_file',
            {'file_handling_mode': 'per_file'},
            expected_file_handling_mode='per_file',
            can_discover_files=False,
        ),
        FileHandlingCase(
            'no_target',
            {'file_handling_mode': 'no_target'},
            expected_file_handling_mode='no_target',
            can_discover_files=True,
        ),
    ],
    ids=lambda c: c.desc,
)
def test_tool_config_file_handling_modes(tcase: FileHandlingCase) -> None:
    """Test file handling modes for tool config."""
    tool = ToolConfig(name='test', command='cmd', args=[], **tcase.kwargs)
    assert tool.file_handling_mode == tcase.expected_file_handling_mode
    assert tool.can_discover_files() == tcase.can_discover_files


def test_extension_normalization() -> None:
    """Test that extensions get normalized with dots."""
    config = ProfileConfig(
        name='test',
        extensions=['py', 'pyx', '.js'],
        check_tools=[],
        format_tools=[],
    )
    assert config.extensions == ['.py', '.pyx', '.js']


def test_toolbelt_config_with_profiles() -> None:
    """Test toolbelt config with profiles."""
    python_config = ProfileConfig(
        name='python',
        extensions=['.py'],
        check_tools=[],
        format_tools=[],
    )
    js_config = ProfileConfig(
        name='javascript',
        extensions=['.js'],
        check_tools=[],
        format_tools=[],
    )

    config = ToolbeltConfig(
        profiles={'python': python_config, 'javascript': js_config},
        global_exclude_patterns=['node_modules/**', '.git/**'],
        variables={
            'TOOLBELT_RUFF_VERSION': '1.2.3',
        },
    )

    assert len(config.profiles) == 2, f'Expected 2 profiles, got {len(config.profiles)}'
    assert config.get_profile('python') == python_config
    assert config.get_profile('javascript') == js_config
    assert config.get_profile('nonexistent') is None
    assert config.get_variables() == {'TOOLBELT_RUFF_VERSION': '1.2.3'}
    assert set(config.list_profiles()) == {'python', 'javascript'}
    assert config.global_exclude_patterns == ['node_modules/**', '.git/**']


@dataclass
class ToolCommandCase:
    """Test case for get_tool_command utility."""

    desc: str
    tool_kwargs: dict[str, Any]
    files: list[str] | None = None
    targets: list[str] | None = None
    variables: dict[str, str] | None = None
    expected_cmd: list[str] | None = None


@pytest.mark.parametrize(
    'tcase',
    [
        ToolCommandCase(
            desc='per_file mode with files',
            tool_kwargs={
                'name': 'test',
                'command': 'cmd',
                'file_handling_mode': 'per_file',
                'args': ['--flag'],
            },
            files=['a.py', 'b.py'],
            expected_cmd=['cmd', '--flag', 'a.py', 'b.py'],
        ),
        ToolCommandCase(
            desc='batch mode with targets',
            tool_kwargs={
                'name': 'test',
                'command': 'cmd',
                'file_handling_mode': 'batch',
                'args': ['--flag'],
            },
            targets=['a.py', 'b.py'],
            expected_cmd=['cmd', '--flag', 'a.py', 'b.py'],
        ),
        ToolCommandCase(
            desc='batch mode with default_target',
            tool_kwargs={
                'name': 'test',
                'command': 'cmd',
                'file_handling_mode': 'batch',
                'args': ['--flag'],
                'default_target': 'src/',
            },
            expected_cmd=['cmd', '--flag', 'src/'],
        ),
        ToolCommandCase(
            desc='no_target mode, no files/targets',
            tool_kwargs={
                'name': 'test',
                'command': 'cmd',
                'file_handling_mode': 'no_target',
                'args': ['--flag'],
            },
            expected_cmd=['cmd', '--flag'],
        ),
        ToolCommandCase(
            desc='args with template variables',
            tool_kwargs={
                'name': 'test',
                'command': 'cmd@${TOOLBELT_RUFF_VERSION}',
                'file_handling_mode': 'per_file',
                'args': ['--flag'],
            },
            files=['main.py'],
            variables={'TOOLBELT_RUFF_VERSION': '1.2.3'},
            expected_cmd=['cmd@1.2.3', '--flag', 'main.py'],
        ),
    ],
    ids=lambda c: c.desc,
)
def test_get_tool_command(tcase: ToolCommandCase) -> None:
    """Test get_tool_command utility for various modes and args."""
    tool = ToolConfig(**tcase.tool_kwargs)
    result = get_tool_command(
        tool,
        files=tcase.files,
        targets=tcase.targets,
        variables=tcase.variables,
    )
    # Check the full command matches expected
    assert result.full_command == tcase.expected_cmd
    # Check base command is correct (expanded)
    expected_base = result.full_command[: len(result.base_command)]
    assert result.base_command == expected_base
    # Check unexpanded_base_command is correct (raw config)
    assert result.unexpanded_base_command == [tool.command, *tool.args]
