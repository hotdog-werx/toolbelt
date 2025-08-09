from dataclasses import dataclass
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from toolbelt.config.models import ToolConfig
from toolbelt.runner import tool_execution as tool_exec_mod
from toolbelt.runner.tool_execution import run_tool_in_discovery_mode


@dataclass
class DiscoveryModeCase:
    desc: str
    tool: ToolConfig
    targets: list | None = None
    variables: dict | None = None
    expected_cmd_substrings: list | None = None
    expected_cmd_exact: list | None = None
    expected_result: int = 0


@pytest.mark.parametrize(
    'case',
    [
        DiscoveryModeCase(
            desc='basic config with default target',
            tool=ToolConfig(
                name='test-tool',
                command='ruff',
                args=['check'],
                description='Test tool',
                file_handling_mode='batch',
                default_target='.',
            ),
            expected_cmd_substrings=['ruff', 'check', '.'],
        ),
        DiscoveryModeCase(
            desc='explicit targets',
            tool=ToolConfig(
                name='test-tool',
                command='mypy',
                args=['--strict'],
                description='Test tool',
                file_handling_mode='batch',
            ),
            targets=['src/', 'tests/'],
            expected_cmd_substrings=['mypy', '--strict', 'src/', 'tests/'],
        ),
        DiscoveryModeCase(
            desc='template variables',
            tool=ToolConfig(
                name='test-tool',
                command='${TOOL_CMD}',
                args=['--config=${CONFIG_FILE}'],
                description='Test tool',
                file_handling_mode='batch',
                default_target='.',
            ),
            variables={'TOOL_CMD': 'black', 'CONFIG_FILE': 'pyproject.toml'},
            expected_cmd_substrings=['black', '--config=pyproject.toml'],
        ),
        DiscoveryModeCase(
            desc='no targets, no default',
            tool=ToolConfig(
                name='test-tool',
                command='tool',
                args=[],
                description='Test tool',
                file_handling_mode='batch',
            ),
            expected_cmd_exact=['tool'],
        ),
        DiscoveryModeCase(
            desc='execute_command failure',
            tool=ToolConfig(
                name='test-tool',
                command='failing-tool',
                args=[],
                description='Test tool',
                file_handling_mode='batch',
            ),
            expected_cmd_substrings=['failing-tool'],
            expected_result=2,
        ),
    ],
    ids=lambda c: c.desc,
)
def test_run_tool_in_discovery_mode_parametrized(
    mocker: MockerFixture,
    case: DiscoveryModeCase,
):
    ret_val = case.expected_result
    mock_execute = mocker.patch.object(
        tool_exec_mod,
        'execute_command',
        return_value=ret_val,
    )
    kwargs = {}
    if case.targets is not None:
        kwargs['targets'] = case.targets
    if case.variables is not None:
        kwargs['variables'] = case.variables
    result = run_tool_in_discovery_mode(case.tool, **kwargs)
    mock_execute.assert_called_once()
    cmd_called = mock_execute.call_args[0][0]
    if case.expected_cmd_substrings:
        for substr in case.expected_cmd_substrings:
            assert any(substr in str(part) for part in cmd_called), f"'{substr}' not found in command: {cmd_called}"
    if case.expected_cmd_exact:
        assert cmd_called == case.expected_cmd_exact
    assert result == case.expected_result


def test_run_tool_in_discovery_mode_working_dir_in_log_context(
    mocker: MockerFixture,
):
    """Test that working_dir is included in log context when different from cwd."""
    tool = ToolConfig(
        name='test-tool',
        command='tool',
        args=[],
        description='Test tool',
        file_handling_mode='batch',
        working_dir='/custom/dir',
    )

    mocker.patch.object(
        tool_exec_mod.Path,
        'cwd',
        return_value=Path('/current/dir'),
    )
    mocker.patch.object(tool_exec_mod, 'execute_command', return_value=0)
    mock_logger = mocker.patch.object(tool_exec_mod, 'logger')

    result = run_tool_in_discovery_mode(tool)

    # Check that working_dir is in log context
    mock_logger.info.assert_called_once()
    log_call = mock_logger.info.call_args
    assert 'working_dir' in log_call.kwargs
    assert log_call.kwargs['working_dir'] == '/custom/dir'

    assert result == 0


def test_run_tool_in_discovery_mode_working_dir_same_as_cwd_not_logged(
    mocker: MockerFixture,
):
    """Test that working_dir is not logged when it's the same as cwd."""
    current_dir = Path.cwd()

    tool = ToolConfig(
        name='test-tool',
        command='tool',
        args=[],
        description='Test tool',
        file_handling_mode='batch',
        working_dir=str(current_dir),  # Same as current working directory
    )

    mocker.patch.object(tool_exec_mod, 'execute_command', return_value=0)
    mock_logger = mocker.patch.object(tool_exec_mod, 'logger')

    result = run_tool_in_discovery_mode(tool)

    # Check that working_dir is NOT in log context
    mock_logger.info.assert_called_once()
    log_call = mock_logger.info.call_args
    assert 'working_dir' not in log_call.kwargs

    assert result == 0
