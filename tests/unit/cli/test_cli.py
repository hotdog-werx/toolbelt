"""Unit tests for toolbelt CLI functionality - Function-based approach."""

from pydoc import cli
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

import toolbelt.cli.main
from toolbelt.cli import main as cli_mod
from toolbelt.cli import _utils as cli_utils
from toolbelt.cli.main import create_parser, main, show_config_sources


@dataclass
class MainCommandTestCase:
    """Test case for main command execution."""

    command: str
    args: list[str]
    expected_runner_func: str
    expected_args: list[Any]
    desc: str


@dataclass
class ExceptionHandlingTestCase:
    """Test case for exception handling."""

    verbose: bool
    desc: str


@dataclass
class ConfigSourcesTestCase:
    """Test case for show_config_sources function."""

    sources: list[str]
    expected_calls: list[str]
    desc: str


def test_missing_command_fails() -> None:
    """Test that missing command raises SystemExit."""
    parser = create_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_invalid_command_fails() -> None:
    """Test that invalid command raises SystemExit."""
    parser = create_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(['invalid'])


# Main Command Tests - Parameterized
@pytest.mark.parametrize(
    'tcase',
    [
        MainCommandTestCase(
            command='check',
            args=['toolbelt', 'check', 'python', 'file1.py', 'file2.py'],
            expected_runner_func='handle_check_command',
            expected_args=['mock_config', 'mock_args'],
            desc='check command with files',
        ),
        MainCommandTestCase(
            command='format',
            args=['toolbelt', 'format', 'javascript'],
            expected_runner_func='handle_format_command',
            expected_args=['mock_config', 'mock_args'],
            desc='format command without files',
        ),
        MainCommandTestCase(
            command='list',
            args=['toolbelt', 'list', 'python'],
            expected_runner_func='handle_list_command',
            expected_args=['mock_config', 'mock_args'],
            desc='list command',
        ),
    ],
    ids=lambda tc: tc.desc,
)
def test_main_commands_detailed(
    tcase: MainCommandTestCase,
    mocker: MockerFixture,
) -> None:
    """Test main function commands with detailed argument verification."""
    # Mock dependencies
    mock_handler = mocker.patch(
        f'toolbelt.cli.main.{tcase.expected_runner_func}',
        return_value=0,
    )
    load_config_mock = mocker.patch.object(cli_mod, 'load_config')

    # Setup config
    mock_config = mocker.MagicMock()
    mock_config.profiles = {'python': Mock(), 'javascript': Mock()}
    load_config_mock.return_value = mock_config

    # Mock sys.argv
    mocker.patch.object(sys, 'argv', tcase.args)

    # Run main
    result = main()

    # Verify result
    assert result == 0, f'Expected result 0, got {result}'

    # Verify handler was called
    mock_handler.assert_called_once()

    # Verify the arguments passed to handler (config and args namespace)
    call_args = mock_handler.call_args[0]
    assert len(call_args) == 2, f'Expected 2 args (config, args), got {len(call_args)}'
    assert call_args[0] == mock_config, 'First argument should be config'

    # Verify the args namespace has the expected command
    args_namespace = call_args[1]
    assert args_namespace.command == tcase.command, f'Expected command {tcase.command}, got {args_namespace.command}'


# Exception Handling Tests - Parameterized
@pytest.mark.parametrize(
    'tcase',
    [
        ExceptionHandlingTestCase(
            verbose=True,
            desc='verbose mode exception handling',
        ),
        ExceptionHandlingTestCase(
            verbose=False,
            desc='non-verbose mode exception handling',
        ),
    ],
    ids=lambda tc: tc.desc,
)
def test_main_exception_handling(
    tcase: ExceptionHandlingTestCase,
    mocker: MockerFixture,
) -> None:
    """Test main function exception handling for different verbosity modes."""
    # Mock dependencies
    mock_configure_logging = mocker.patch('toolbelt.cli.main.configure_logging')
    load_config_mock = mocker.patch.object(cli_mod, 'load_config')

    # Make config loading fail
    load_config_mock.side_effect = Exception(
        'Test error',
    )

    # Mock sys.argv based on verbosity
    test_args = ['toolbelt', 'check', 'python']
    if tcase.verbose:
        test_args.insert(1, '--verbose')
    mocker.patch.object(sys, 'argv', test_args)

    # Run main
    result = main()

    # Verify error handling - main should return 1 on exception
    assert result == 1, f'Expected result 1, got {result}'
    # Verify logging was configured with correct verbosity
    mock_configure_logging.assert_called_once_with(verbose=tcase.verbose)


# Configuration Sources Tests - Parameterized
@pytest.mark.parametrize(
    'tcase',
    [
        ConfigSourcesTestCase(
            sources=['/path/to/config1.yaml', '/path/to/config2.yaml'],
            expected_calls=[
                '[bold bright_blue]Configuration sources (in load order):[/bold bright_blue]',
                '  [cyan]1.[/cyan] [white]/path/to/config1.yaml[/white]',
                '  [cyan]2.[/cyan] [white]/path/to/config2.yaml[/white]',
            ],
            desc='with_multiple_sources',
        ),
        ConfigSourcesTestCase(
            sources=[],
            expected_calls=[
                '[bold yellow]No configuration sources found, using defaults.[/bold yellow]',
            ],
            desc='with_no_sources',
        ),
    ],
    ids=lambda tc: tc.desc,
)
def test_show_config_sources(
    tcase: ConfigSourcesTestCase,
    mocker: MockerFixture,
) -> None:
    """Test show_config_sources function with different source scenarios."""
    mock_console = mocker.patch.object(cli_utils, 'console')
    mocker.patch.object(
        cli_utils,
        'find_config_sources',
        return_value=tcase.sources,
    )

    show_config_sources(None)

    # Check that all expected messages were printed
    for expected_call in tcase.expected_calls:
        mock_console.print.assert_any_call(expected_call)

    # Check for the empty line at the end
    mock_console.print.assert_any_call()


# Additional Specific Tests
def test_main_verbose_logging_configuration(mocker: MockerFixture) -> None:
    """Test that verbose flag properly configures logging."""
    # Mock dependencies
    mock_configure_logging = mocker.patch('toolbelt.cli.main.configure_logging')
    mocker.patch('toolbelt.cli.main.get_logger')
    mock_run_check = mocker.patch(
        'toolbelt.cli.check.run_check',
        return_value=0,
    )

    # Setup config
    mock_config = mocker.MagicMock()
    load_config_mock = mocker.patch.object(cli_mod, 'load_config')
    load_config_mock.return_value = mock_config

    # Mock sys.argv with verbose flag
    test_args = ['toolbelt', '--verbose', 'check', 'python']
    mocker.patch.object(sys, 'argv', test_args)

    # Run main
    result = main()

    # Verify verbose logging was configured
    mock_configure_logging.assert_called_once_with(verbose=True)
    mock_run_check.assert_called_once_with(
        mock_config,
        'python',
        files=[],
        verbose=True,
    )
    assert result == 0


def test_main_custom_config_path(mocker: MockerFixture) -> None:
    """Test main function with custom config file path."""
    # Mock dependencies
    mocker.patch('toolbelt.cli.main.configure_logging')
    mocker.patch('toolbelt.cli.main.get_logger')
    mocker.patch('toolbelt.cli.check.run_check', return_value=0)

    # Setup config
    mock_config = mocker.MagicMock()
    load_config_mock = mocker.patch.object(cli_mod, 'load_config')
    load_config_mock.return_value = mock_config

    # Mock sys.argv with custom config
    test_args = ['toolbelt', '--config', 'custom.yaml', 'check', 'python']
    mocker.patch.object(sys, 'argv', test_args)

    # Run main
    result = main()

    # Verify custom config path was passed
    load_config_mock.assert_called_once_with([Path('custom.yaml')])
    assert result == 0


def test_main_logs_startup_information(mocker: MockerFixture) -> None:
    """Test that main function executes successfully and calls expected functions."""
    # Mock dependencies
    mock_configure_logging = mocker.patch('toolbelt.cli.main.configure_logging')
    mock_run_check = mocker.patch(
        'toolbelt.cli.check.run_check',
        return_value=0,
    )

    # Setup config
    mock_config = mocker.MagicMock()
    mock_config.languages = {
        'python': mocker.MagicMock(),
        'javascript': mocker.MagicMock(),
    }
    load_config_mock = mocker.patch.object(cli_mod, 'load_config')
    load_config_mock.return_value = mock_config

    # Mock sys.argv
    test_args = ['toolbelt', '--config', 'test.yaml', 'check', 'python']
    mocker.patch.object(sys, 'argv', test_args)

    # Run main
    result = main()

    # Verify successful execution and proper function calls
    assert result == 0
    mock_configure_logging.assert_called_once_with(verbose=False)
    mock_run_check.assert_called_once_with(
        mock_config,
        'python',
        files=[],
        verbose=False,
    )


# Legacy Handler Tests (for coverage of the new handler system)
def test_main_check_command(mocker: MockerFixture) -> None:
    """Test main() with check command using new handler system."""
    mock_parser = mocker.patch('toolbelt.cli.main.create_parser')
    mock_args = SimpleNamespace(
        verbose=False,
        config=None,
        sources=False,
        command='check',
        profile='python',
        files=[],
    )
    mock_parser.return_value.parse_args.return_value = mock_args
    # Create a proper mock config object with profiles attribute
    mock_config = Mock()
    mock_config.profiles = {'python': Mock(), 'javascript': Mock()}
    load_config_mock = mocker.patch.object(cli_mod, 'load_config')
    load_config_mock.return_value = mock_config
    # Patch handler in toolbelt.cli module to ensure lookup works
    mock_handler = mocker.patch(
        'toolbelt.cli.check.handle_check_command',
        return_value=0,
    )
    mocker.patch.object(toolbelt.cli.main, 'handle_check_command', mock_handler)

    result = main()

    assert result == 0, f'main() returned {result}, expected 0'
    mock_handler.assert_called_once()


def test_main_with_sources_flag(mocker: MockerFixture) -> None:
    """Test main() with --sources flag to trigger show_config_sources."""
    mock_parser = mocker.patch('toolbelt.cli.main.create_parser')
    mock_args = SimpleNamespace(
        verbose=False,
        config=None,
        sources=True,
        command='check',
        profile='python',
        files=[],
    )
    mock_parser.return_value.parse_args.return_value = mock_args
    load_config_mock = mocker.patch.object(cli_mod, 'load_config')

    # Create a proper mock config object with profiles attribute
    mock_config = Mock()
    mock_config.profiles = {'python': Mock(), 'javascript': Mock()}
    load_config_mock.return_value = mock_config

    # Don't mock show_config_sources - let it execute to get coverage
    mock_console = mocker.patch.object(cli_utils, 'console')

    # Patch handler in toolbelt.cli module to ensure lookup works
    mock_handler = mocker.patch(
        'toolbelt.cli.check.handle_check_command',
        return_value=0,
    )
    mocker.patch.object(toolbelt.cli.main, 'handle_check_command', mock_handler)

    result = main()

    assert result == 0, f'main() returned {result}, expected 0'
    # Verify that console.print was called (show_config_sources was executed)
    assert mock_console.print.called
    mock_handler.assert_called_once()
