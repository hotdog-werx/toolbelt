from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

import toolbelt.runner.tool_execution as tool_exec_mod
from toolbelt.config.models import ToolConfig
from toolbelt.runner.tool_execution import run_tool_per_file_mode


# Grouped mocks for per-file mode tests
class PerFileModeMocks(TypedDict):
    execute_command: MagicMock
    logger: MagicMock
    get_max_display_files: MagicMock


@pytest.fixture
def per_file_mode_mocks(mocker: MockerFixture) -> PerFileModeMocks:
    return PerFileModeMocks(
        execute_command=mocker.patch.object(
            tool_exec_mod,
            'execute_command',
            return_value=0,
        ),
        logger=mocker.patch.object(tool_exec_mod, 'logger'),
        get_max_display_files=mocker.patch.object(
            tool_exec_mod,
            'get_max_display_files',
            return_value=0,
        ),
    )


@dataclass
class PerFileModeCase:
    desc: str
    tool: ToolConfig
    files: list[Path]
    variables: dict[str, str] | None = None
    expected_cmd_substrings: list[str] | None = None
    expected_cmd_exact: list[str] | None = None
    expected_result: int = 0


@pytest.mark.parametrize(
    'case',
    [
        PerFileModeCase(
            desc='basic file list',
            tool=ToolConfig(
                name='test-tool',
                command='echo',
                args=['hello'],
                description='Test tool',
                file_handling_mode='per_file',
            ),
            files=[Path('file1.py'), Path('file2.py')],
            expected_cmd_substrings=['file1.py', 'file2.py'],
        ),
        PerFileModeCase(
            desc='template variables',
            tool=ToolConfig(
                name='test-tool',
                command='${TOOL_CMD}',
                args=['--flag=${FLAG_VALUE}'],
                description='Test tool',
                file_handling_mode='per_file',
            ),
            files=[Path('test.py')],
            variables={'TOOL_CMD': 'ruff', 'FLAG_VALUE': 'check'},
            expected_cmd_substrings=['ruff', '--flag=check', 'test.py'],
        ),
        PerFileModeCase(
            desc='execute_command failure',
            tool=ToolConfig(
                name='test-tool',
                command='failing-tool',
                args=[],
                description='Test tool',
                file_handling_mode='per_file',
            ),
            files=[Path('test.py')],
            expected_cmd_substrings=['failing-tool', 'test.py'],
            expected_result=1,
        ),
        PerFileModeCase(
            desc='no variables',
            tool=ToolConfig(
                name='test-tool',
                command='tool',
                args=[],
                description='Test tool',
                file_handling_mode='per_file',
            ),
            files=[Path('test.py')],
            expected_cmd_substrings=['tool', 'test.py'],
        ),
    ],
    ids=lambda c: c.desc,
)
def test_run_tool_per_file_mode_parametrized(
    mocker: MockerFixture,
    case: PerFileModeCase,
):
    """Parametrized test for run_tool_per_file_mode command construction and result."""
    mock_execute = mocker.patch.object(
        tool_exec_mod,
        'execute_command',
        return_value=case.expected_result,
    )
    kwargs = {}
    if case.variables is not None:
        kwargs['variables'] = case.variables
    result = run_tool_per_file_mode(case.tool, files=case.files, **kwargs)
    mock_execute.assert_called_once()
    cmd_called = mock_execute.call_args[0][0]
    if case.expected_cmd_substrings:
        for substr in case.expected_cmd_substrings:
            assert any(substr in str(part) for part in cmd_called)
    if case.expected_cmd_exact:
        assert cmd_called == case.expected_cmd_exact
    assert result == case.expected_result


@pytest.mark.parametrize(
    'tcase',
    [
        (3, 10),
        (0, 3),
    ],
    ids=['limit_3', 'show_all'],
)
def test_run_tool_per_file_mode_display_limit(
    tcase: tuple[int, int],
    per_file_mode_mocks: PerFileModeMocks,
):
    """Parametrized test for file display limit in logging."""
    max_display, expected_file_count = tcase
    tool = ToolConfig(
        name='test-tool',
        command='tool',
        args=[],
        description='Test tool',
        file_handling_mode='per_file',
    )
    if max_display == 3:
        files = [Path(f'file{i}.py') for i in range(10)]
    else:
        files = [Path(f'file{i}.py') for i in range(1, 4)]
    per_file_mode_mocks['get_max_display_files'].return_value = max_display
    per_file_mode_mocks['execute_command'].return_value = 0
    result = run_tool_per_file_mode(tool, files=files)
    cmd_called = per_file_mode_mocks['execute_command'].call_args[0][0]
    assert len([arg for arg in cmd_called if arg.endswith('.py')]) == expected_file_count
    per_file_mode_mocks['logger'].info.assert_called_once()
    log_call = per_file_mode_mocks['logger'].info.call_args
    assert 'file_count' in log_call.kwargs
    assert log_call.kwargs['file_count'] == str(expected_file_count)
    assert result == 0


def test_run_tool_per_file_mode_max_display_zero(
    per_file_mode_mocks: PerFileModeMocks,
):
    """Test behavior when max display files is set to 0 (show all)."""
    tool = ToolConfig(
        name='test-tool',
        command='tool',
        args=[],
        description='Test tool',
        file_handling_mode='per_file',
    )
    files = [Path('file1.py'), Path('file2.py'), Path('file3.py')]
    per_file_mode_mocks['get_max_display_files'].return_value = 0
    per_file_mode_mocks['execute_command'].return_value = 0
    result = run_tool_per_file_mode(tool, files=files)
    # Should execute with all files
    cmd_called = per_file_mode_mocks['execute_command'].call_args[0][0]
    assert all(f'file{i}.py' in cmd_called for i in range(1, 4))
    assert result == 0


def test_run_tool_per_file_mode_working_dir_in_log_context(
    mocker: MockerFixture,
    per_file_mode_mocks: PerFileModeMocks,
):
    """Test that working_dir is included in log context when different from cwd."""
    tool = ToolConfig(
        name='test-tool',
        command='tool',
        args=[],
        description='Test tool',
        file_handling_mode='per_file',
        working_dir='/custom/dir',
    )
    files = [Path('test.py')]
    mocker.patch.object(
        tool_exec_mod.Path,
        'cwd',
        return_value=Path('/current/dir'),
    )
    result = run_tool_per_file_mode(tool, files=files)
    per_file_mode_mocks['logger'].info.assert_called_once()
    log_call = per_file_mode_mocks['logger'].info.call_args
    assert 'working_dir' in log_call.kwargs
    assert log_call.kwargs['working_dir'] == '/custom/dir'
    assert result == 0


def test_run_tool_per_file_mode_working_dir_same_as_cwd_not_logged(
    mocker: MockerFixture,
    per_file_mode_mocks: PerFileModeMocks,
):
    """Test that working_dir is NOT logged when it's the same as cwd."""
    current_dir = Path.cwd()
    tool = ToolConfig(
        name='test-tool',
        command='tool',
        args=[],
        description='Test tool',
        file_handling_mode='per_file',
        working_dir=str(current_dir),
    )
    files = [Path('test.py')]
    mocker.patch.object(tool_exec_mod.Path, 'cwd', return_value=current_dir)
    result = run_tool_per_file_mode(tool, files=files)
    per_file_mode_mocks['logger'].info.assert_called_once()
    log_call = per_file_mode_mocks['logger'].info.call_args
    assert 'working_dir' not in log_call.kwargs
    assert result == 0
