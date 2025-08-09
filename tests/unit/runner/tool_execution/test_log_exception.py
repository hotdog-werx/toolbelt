import subprocess
from dataclasses import dataclass
from typing import TypedDict
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from toolbelt.config.models import ToolConfig
from toolbelt.runner import tool_execution as tool_exec_mod
from toolbelt.runner.tool_execution import _log_exception, execute_command


class ToolExecMocks(TypedDict):
    expand_globs_in_args: MagicMock
    subprocess_run: MagicMock
    logger: MagicMock
    stdout_write: MagicMock


@dataclass
class LogExceptionCase:
    side_effect: Exception
    expected_log: str
    expected_error_type: str
    description: str


@pytest.fixture
def patch_tool_exec_common(mocker: MockerFixture) -> ToolExecMocks:
    """Fixture to patch common tool_exec_mod dependencies and return mocks as a dataclass."""
    patch_expand = mocker.patch.object(tool_exec_mod, 'expand_globs_in_args')
    patch_run = mocker.patch.object(tool_exec_mod.subprocess, 'run')
    patch_logger = mocker.patch.object(tool_exec_mod, 'logger')
    patch_stdout = mocker.patch.object(tool_exec_mod.sys.stdout, 'write')
    return ToolExecMocks(
        expand_globs_in_args=patch_expand,
        subprocess_run=patch_run,
        logger=patch_logger,
        stdout_write=patch_stdout,
    )


@pytest.mark.parametrize(
    'tcase',
    [
        LogExceptionCase(
            side_effect=FileNotFoundError('Command not found'),
            expected_log='command_not_found',
            expected_error_type='FileNotFoundError',
            description='filenotfounderror_triggers_command_not_found',
        ),
        LogExceptionCase(
            side_effect=OSError('Permission denied'),
            expected_log='unexpected_error',
            expected_error_type='OSError',
            description='oserror_triggers_unexpected_error',
        ),
        LogExceptionCase(
            side_effect=subprocess.CalledProcessError(1, 'some-command'),
            expected_log='unexpected_error',
            expected_error_type='CalledProcessError',
            description='calledprocesserror_triggers_unexpected_error',
        ),
        LogExceptionCase(
            side_effect=ValueError('Some unexpected error'),
            expected_log='failed',
            expected_error_type='ValueError',
            description='valueerror_triggers_failed',
        ),
    ],
    ids=lambda c: c.description,
)
def test_log_exception_variants(
    patch_tool_exec_common: ToolExecMocks,
    tcase: LogExceptionCase,
):
    tool = ToolConfig(
        name='test-tool',
        command='some-command',
        args=[],
        description='Test tool',
        file_handling_mode='batch',
    )
    patch_tool_exec_common['expand_globs_in_args'].return_value = [
        'some-command',
    ]
    patch_tool_exec_common['subprocess_run'].side_effect = tcase.side_effect
    mock_logger = patch_tool_exec_common['logger']

    result = execute_command(['some-command'], tool)
    assert result == 1
    mock_logger.exception.assert_called_once()
    call_args = mock_logger.exception.call_args
    assert call_args[0][0] == tcase.expected_log
    assert call_args[1]['tool'] == 'test-tool'
    assert call_args[1]['error_type'] == tcase.expected_error_type
    assert call_args[1]['context'] == 'execute_command'


def test_log_exception_with_custom_command_and_file(mocker: MockerFixture):
    """Test _log_exception with custom command and file parameters."""
    tool = ToolConfig(
        name='test-tool',
        command='default-cmd',
        args=[],
        description='Test tool',
        file_handling_mode='batch',
    )

    # Mock the logger to capture the call
    mock_logger = mocker.patch.object(tool_exec_mod, 'logger')

    # Create a custom exception
    error = RuntimeError('Test error')

    # Call _log_exception directly with custom parameters
    _log_exception(
        error,
        tool=tool,
        command=['custom', 'command'],
        file='/path/to/file.py',
        context='test_context',
    )

    # Should log the exception with 'failed' (since RuntimeError is not FileNotFoundError or OSError)
    mock_logger.exception.assert_called_once()
    call_args = mock_logger.exception.call_args
    assert call_args[0][0] == 'failed'  # First positional arg
    assert call_args[1]['tool'] == 'test-tool'
    assert call_args[1]['command'] == 'custom command'  # Should use provided command, not tool.command
    assert call_args[1]['file'] == '/path/to/file.py'
    assert call_args[1]['error'] == 'Test error'
    assert call_args[1]['error_type'] == 'RuntimeError'
    assert call_args[1]['context'] == 'test_context'
