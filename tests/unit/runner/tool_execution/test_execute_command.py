import subprocess
from dataclasses import dataclass
from typing import Any, TypedDict
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

import toolbelt.runner.tool_execution as tool_exec_mod
from toolbelt.config.models import ToolConfig
from toolbelt.runner.tool_execution import execute_command


# Fixture for common command execution mocks
class CommandEnvMocks(TypedDict):
    expand: MagicMock
    run: MagicMock
    stdout_write: MagicMock
    log_exception: MagicMock


@pytest.fixture
def mock_command_env(mocker) -> CommandEnvMocks:
    expand = mocker.patch.object(tool_exec_mod, 'expand_globs_in_args')
    run = mocker.patch.object(tool_exec_mod.subprocess, 'run')
    stdout_write = mocker.patch.object(tool_exec_mod.sys.stdout, 'write')
    # log_exception is only needed for error tests, but always patch for consistency
    log_exception = mocker.patch.object(tool_exec_mod, '_log_exception')
    return CommandEnvMocks(
        expand=expand,
        run=run,
        stdout_write=stdout_write,
        log_exception=log_exception,
    )


def assert_dict_subset(
    subset: dict[str, Any],
    superset: dict[str, Any],
) -> None:
    """Assert that all items in subset are present in superset with the same values."""
    missing = {k: v for k, v in subset.items() if k not in superset or superset[k] != v}
    assert not missing, (
        f'Missing or mismatched items in dict: {missing}\nExpected subset: {subset}\nActual: {superset}'
    )


@dataclass
class ErrorCase:
    desc: str
    tool: ToolConfig
    cmd: list[str]
    exception: Exception
    exception_type: type


@pytest.mark.parametrize(
    'case',
    [
        ErrorCase(
            desc='file_not_found',
            tool=ToolConfig(
                name='test-tool',
                command='nonexistent-command',
                args=[],
                description='Test tool',
                file_handling_mode='batch',
            ),
            cmd=['nonexistent-command'],
            exception=FileNotFoundError('Command not found'),
            exception_type=FileNotFoundError,
        ),
        ErrorCase(
            desc='os_error',
            tool=ToolConfig(
                name='test-tool',
                command='restricted-command',
                args=[],
                description='Test tool',
                file_handling_mode='batch',
            ),
            cmd=['restricted-command'],
            exception=OSError('Permission denied'),
            exception_type=OSError,
        ),
        ErrorCase(
            desc='subprocess_error',
            tool=ToolConfig(
                name='test-tool',
                command='problem-command',
                args=[],
                description='Test tool',
                file_handling_mode='batch',
            ),
            cmd=['problem-command'],
            exception=subprocess.CalledProcessError(1, 'problem-command'),
            exception_type=subprocess.CalledProcessError,
        ),
        ErrorCase(
            desc='other_exception',
            tool=ToolConfig(
                name='test-tool',
                command='weird-command',
                args=[],
                description='Test tool',
                file_handling_mode='batch',
            ),
            cmd=['weird-command'],
            exception=ValueError('Unexpected error'),
            exception_type=ValueError,
        ),
    ],
    ids=lambda c: c.desc,
)
def test_execute_command_error_cases(
    mock_command_env: CommandEnvMocks,
    case: ErrorCase,
):
    mock_command_env['expand'].return_value = case.cmd
    mock_command_env['run'].side_effect = case.exception
    result = execute_command(case.cmd, case.tool)
    mock_command_env['log_exception'].assert_called_once()
    call_args = mock_command_env['log_exception'].call_args
    assert isinstance(call_args[0][0], case.exception_type)
    expected_kwargs = {
        'tool': case.tool,
        'command': case.cmd,
        'file': None,
        'context': 'execute_command',
    }
    assert_dict_subset(expected_kwargs, call_args[1])
    assert result == 1


@dataclass
class SuccessCase:
    desc: str
    tool: ToolConfig
    cmd: list[str]
    expand_return: list[str]
    run_returncode: int
    run_return_args: list[str] | None = None
    working_dir: str | None = None
    expect_result: int = 0


@pytest.mark.parametrize(
    'case',
    [
        SuccessCase(
            desc='success',
            tool=ToolConfig(
                name='test-tool',
                command='echo',
                args=['hello'],
                description='Test tool',
                file_handling_mode='batch',
            ),
            cmd=['echo', 'hello'],
            expand_return=['echo', 'hello'],
            run_returncode=0,
            expect_result=0,
        ),
        SuccessCase(
            desc='failure',
            tool=ToolConfig(
                name='test-tool',
                command='false',
                args=[],
                description='Test tool',
                file_handling_mode='batch',
            ),
            cmd=['false'],
            expand_return=['false'],
            run_returncode=1,
            expect_result=1,
        ),
        SuccessCase(
            desc='custom_working_dir',
            tool=ToolConfig(
                name='test-tool',
                command='echo',
                args=['hello'],
                description='Test tool',
                file_handling_mode='batch',
                working_dir='/custom/path',
            ),
            cmd=['echo', 'hello'],
            expand_return=['echo', 'hello'],
            run_returncode=0,
            working_dir='/custom/path',
            expect_result=0,
        ),
        SuccessCase(
            desc='glob_expansion',
            tool=ToolConfig(
                name='test-tool',
                command='ls',
                args=[],
                description='Test tool',
                file_handling_mode='batch',
            ),
            cmd=['ls', '*.py'],
            expand_return=['ls', 'file1.py', 'file2.py'],
            run_returncode=0,
            expect_result=0,
        ),
    ],
    ids=lambda c: c.desc,
)
def test_execute_command_success_cases(
    mocker: MockerFixture,
    mock_command_env: CommandEnvMocks,
    case: SuccessCase,
):
    mock_command_env['expand'].return_value = case.expand_return
    mock_result = mocker.Mock()
    mock_result.returncode = case.run_returncode
    mock_command_env['run'].return_value = mock_result
    result = execute_command(case.cmd, case.tool)
    mock_command_env['expand'].assert_called_once_with(case.cmd)
    mock_command_env['run'].assert_called_once_with(
        case.expand_return,
        check=False,
        cwd=case.tool.working_dir,
        capture_output=False,
        text=True,
    )
    assert mock_command_env['stdout_write'].called
    assert result == case.expect_result
