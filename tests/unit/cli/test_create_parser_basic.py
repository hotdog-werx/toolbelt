import sys
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock  # Only for type annotations

import pytest
from pytest_mock import MockerFixture

from toolbelt.cli.main import main


@dataclass
class MainTestCase:
    desc: str
    args: list[str]
    expected_exit_code: int
    config_load_success: bool = True
    runner_success: bool = True
    config_load_error: str | None = None
    should_call_run_check: bool = False
    should_call_run_format: bool = False
    should_call_list_tools: bool = False
    verbose: bool = False
    config_path: Path | None = None


# --- Helper functions for main function scenario assertions ---
def assert_exit_code(result: int, tcase: MainTestCase) -> None:
    assert result == tcase.expected_exit_code


def assert_logging_config(
    mock_configure_logging: MagicMock,
    tcase: MainTestCase,
) -> None:
    mock_configure_logging.assert_called_once_with(verbose=tcase.verbose)


@dataclass
class AssertRunnerCallsParams:
    mock_run_check: MagicMock
    mock_run_format: MagicMock
    mock_list_tools: MagicMock
    tcase: MainTestCase
    mock_config: MagicMock


def assert_runner_calls(params: AssertRunnerCallsParams) -> None:
    # Check runner function calls
    tcase = params.tcase
    if tcase.should_call_run_check:
        if tcase.config_load_success:
            params.mock_run_check.assert_called_once()
            call_args = params.mock_run_check.call_args[0]
            assert call_args[0] is params.mock_config
        else:
            params.mock_run_check.assert_not_called()
    else:
        params.mock_run_check.assert_not_called()

    if tcase.should_call_run_format:
        if tcase.config_load_success:
            params.mock_run_format.assert_called_once()
        else:
            params.mock_run_format.assert_not_called()
    else:
        params.mock_run_format.assert_not_called()

    if tcase.should_call_list_tools:
        if tcase.config_load_success:
            params.mock_list_tools.assert_called_once()
        else:
            params.mock_list_tools.assert_not_called()
    else:
        params.mock_list_tools.assert_not_called()


# Main function tests using parametrization
@pytest.mark.parametrize(
    'tcase',
    [
        MainTestCase(
            desc='check_command_success',
            args=['toolbelt', 'check', 'python', 'file1.py'],
            expected_exit_code=0,
            should_call_run_check=True,
        ),
        MainTestCase(
            desc='format_command_success',
            args=['toolbelt', 'format', 'javascript'],
            expected_exit_code=0,
            should_call_run_format=True,
        ),
        MainTestCase(
            desc='list_command_success',
            args=['toolbelt', 'list'],
            expected_exit_code=0,
            should_call_list_tools=True,
        ),
        MainTestCase(
            desc='check_command_with_verbose',
            args=['toolbelt', '--verbose', 'check', 'python'],
            expected_exit_code=0,
            should_call_run_check=True,
            verbose=True,
        ),
        MainTestCase(
            desc='check_command_with_custom_config',
            args=['toolbelt', '--config', 'custom.yaml', 'check', 'python'],
            expected_exit_code=0,
            should_call_run_check=True,
            config_path=Path('custom.yaml'),
        ),
        MainTestCase(
            desc='config_loading_error',
            args=['toolbelt', 'check', 'python'],
            expected_exit_code=1,
            config_load_success=False,
            config_load_error='Config loading failed',
        ),
        MainTestCase(
            desc='run_check_failure',
            args=['toolbelt', 'check', 'python'],
            expected_exit_code=1,
            should_call_run_check=True,
            runner_success=False,
        ),
        MainTestCase(
            desc='run_format_failure',
            args=['toolbelt', 'format', 'javascript'],
            expected_exit_code=1,
            should_call_run_format=True,
            runner_success=False,
        ),
    ],
    ids=lambda c: c.desc,
)
def test_main_function_scenarios(
    tcase: MainTestCase,
    mocker: MockerFixture,
) -> None:
    """Test main function with various scenarios using parametrization."""
    # Mock dependencies
    mock_configure_logging = mocker.patch('toolbelt.cli.main.configure_logging')
    mock_run_check = mocker.patch('toolbelt.cli.check.run_check')
    mock_run_format = mocker.patch('toolbelt.cli.format.run_format')
    mock_list_tools = mocker.patch('toolbelt.cli.list.list_tools')
    load_config_mock = mocker.patch('toolbelt.cli.main.load_config')

    # Setup config manager
    mock_config = mocker.MagicMock()
    if tcase.config_load_success:
        load_config_mock.return_value = mock_config
    else:
        load_config_mock.side_effect = Exception(
            tcase.config_load_error,
        )

    # Setup runner return values
    exit_code = 0 if tcase.runner_success else 1
    mock_run_check.return_value = exit_code
    mock_run_format.return_value = exit_code
    mock_list_tools.return_value = exit_code

    # Mock sys.argv
    mocker.patch.object(sys, 'argv', tcase.args)

    # Run main
    result = main()

    # Use helper functions for assertions
    assert_exit_code(result, tcase)
    assert_logging_config(mock_configure_logging, tcase)
    assert_runner_calls(
        AssertRunnerCallsParams(
            mock_run_check=mock_run_check,
            mock_run_format=mock_run_format,
            mock_list_tools=mock_list_tools,
            tcase=tcase,
            mock_config=mock_config,
        ),
    )
