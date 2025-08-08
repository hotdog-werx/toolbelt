"""Tests for run_check and run_format public API functions."""

from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict
from unittest.mock import MagicMock

import pytest

import toolbelt.runner.orchestrator as orchestrator_mod
from toolbelt.config import ToolbeltConfig
from toolbelt.runner.orchestrator import run_check, run_format


# Grouped mocks for public API tests
class PublicApiMocks(TypedDict):
    run_tools_for_profile: MagicMock


@pytest.fixture
def public_api_mocks(mocker) -> PublicApiMocks:
    return PublicApiMocks(
        run_tools_for_profile=mocker.patch.object(
            orchestrator_mod,
            '_run_tools_for_profile',
            return_value=0,
        ),
    )


@dataclass
class PublicApiCase:
    desc: str
    function_name: str
    config: ToolbeltConfig
    profile: str
    files: list[Path] | None = None
    verbose: bool = False
    expected_result: int = 0


def create_test_config() -> ToolbeltConfig:
    """Create a minimal test ToolbeltConfig."""
    return ToolbeltConfig(
        global_exclude_patterns=[],
        variables={},
        profiles={},
    )


@pytest.mark.parametrize(
    'case',
    [
        PublicApiCase(
            desc='run_check_default_args',
            function_name='run_check',
            config=create_test_config(),
            profile='test-profile',
            expected_result=0,
        ),
        PublicApiCase(
            desc='run_check_with_files',
            function_name='run_check',
            config=create_test_config(),
            profile='test-profile',
            files=[Path('file1.py'), Path('file2.py')],
            expected_result=0,
        ),
        PublicApiCase(
            desc='run_check_verbose',
            function_name='run_check',
            config=create_test_config(),
            profile='test-profile',
            verbose=True,
            expected_result=0,
        ),
        PublicApiCase(
            desc='run_check_failure',
            function_name='run_check',
            config=create_test_config(),
            profile='test-profile',
            expected_result=1,
        ),
        PublicApiCase(
            desc='run_format_default_args',
            function_name='run_format',
            config=create_test_config(),
            profile='test-profile',
            expected_result=0,
        ),
        PublicApiCase(
            desc='run_format_with_files',
            function_name='run_format',
            config=create_test_config(),
            profile='test-profile',
            files=[Path('file1.py'), Path('file2.py')],
            expected_result=0,
        ),
        PublicApiCase(
            desc='run_format_verbose',
            function_name='run_format',
            config=create_test_config(),
            profile='test-profile',
            verbose=True,
            expected_result=0,
        ),
        PublicApiCase(
            desc='run_format_failure',
            function_name='run_format',
            config=create_test_config(),
            profile='test-profile',
            expected_result=1,
        ),
    ],
    ids=lambda c: c.desc,
)
def test_public_api_functions(
    public_api_mocks: PublicApiMocks,
    case: PublicApiCase,
):
    """Test run_check and run_format public API functions."""
    # Set up mock return value
    public_api_mocks['run_tools_for_profile'].return_value = case.expected_result

    # Call the appropriate function
    if case.function_name == 'run_check':
        result = run_check(
            case.config,
            case.profile,
            files=case.files,
            verbose=case.verbose,
        )
        expected_tool_type = 'check'
    else:  # run_format
        result = run_format(
            case.config,
            case.profile,
            files=case.files,
            verbose=case.verbose,
        )
        expected_tool_type = 'format'

    # Verify result
    assert result == case.expected_result

    # Verify _run_tools_for_profile was called with correct arguments
    public_api_mocks['run_tools_for_profile'].assert_called_once_with(
        case.config,
        case.profile,
        files=case.files,
        verbose=case.verbose,
        tool_type=expected_tool_type,
    )


def test_run_check_delegates_to_run_tools_for_profile(
    public_api_mocks: PublicApiMocks,
):
    """Test that run_check is a thin wrapper around _run_tools_for_profile."""
    config = create_test_config()
    files = [Path('test.py')]

    run_check(config, 'python', files=files, verbose=True)

    public_api_mocks['run_tools_for_profile'].assert_called_once_with(
        config,
        'python',
        files=files,
        verbose=True,
        tool_type='check',
    )


def test_run_format_delegates_to_run_tools_for_profile(
    public_api_mocks: PublicApiMocks,
):
    """Test that run_format is a thin wrapper around _run_tools_for_profile."""
    config = create_test_config()
    files = [Path('test.py')]

    run_format(config, 'python', files=files, verbose=True)

    public_api_mocks['run_tools_for_profile'].assert_called_once_with(
        config,
        'python',
        files=files,
        verbose=True,
        tool_type='format',
    )
