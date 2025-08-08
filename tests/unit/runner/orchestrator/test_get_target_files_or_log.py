"""Tests for _get_target_files_or_log function."""

from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict
from unittest.mock import MagicMock

import pytest

import toolbelt.runner.orchestrator as orchestrator_mod
from toolbelt.config.models import ProfileConfig
from toolbelt.runner.orchestrator import (
    TargetFilesContext,
    _get_target_files_or_log,
)


# Grouped mocks for target files tests
class TargetFilesMocks(TypedDict):
    get_target_files: MagicMock
    logger: MagicMock


@pytest.fixture
def target_files_mocks(mocker) -> TargetFilesMocks:
    return TargetFilesMocks(
        get_target_files=mocker.patch.object(
            orchestrator_mod,
            'get_target_files',
            return_value=[],
        ),
        logger=mocker.patch.object(orchestrator_mod, 'logger'),
    )


@dataclass
class TargetFilesCase:
    desc: str
    context: TargetFilesContext
    mock_return_value: list[Path] | None
    expected_result: list[Path] | None
    should_log_warning: bool = False


@pytest.mark.parametrize(
    'case',
    [
        TargetFilesCase(
            desc='files_found_success',
            context=TargetFilesContext(
                profile=ProfileConfig(
                    name='test-profile',
                    extensions=['.py'],
                    check_tools=[],
                    format_tools=[],
                ),
                files=[Path('file1.py'), Path('file2.py')],
                global_exclude_patterns=[],
                verbose=False,
                provided_files=['file1.py', 'file2.py'],
                log_type='no_files',
            ),
            mock_return_value=[Path('file1.py'), Path('file2.py')],
            expected_result=[Path('file1.py'), Path('file2.py')],
            should_log_warning=False,
        ),
        TargetFilesCase(
            desc='no_files_found_logs_warning',
            context=TargetFilesContext(
                profile=ProfileConfig(
                    name='test-profile',
                    extensions=['.py'],
                    check_tools=[],
                    format_tools=[],
                ),
                files=[Path('nonexistent.py')],
                global_exclude_patterns=[],
                verbose=False,
                provided_files=['nonexistent.py'],
                log_type='no_files',
            ),
            mock_return_value=[],
            expected_result=None,
            should_log_warning=True,
        ),
        TargetFilesCase(
            desc='empty_files_list_logs_warning',
            context=TargetFilesContext(
                profile=ProfileConfig(
                    name='test-profile',
                    extensions=['.py'],
                    check_tools=[],
                    format_tools=[],
                ),
                files=None,
                global_exclude_patterns=[],
                verbose=True,
                provided_files=None,
                log_type='no_matching_files',
            ),
            mock_return_value=None,
            expected_result=None,
            should_log_warning=True,
        ),
    ],
    ids=lambda c: c.desc,
)
def test_get_target_files_or_log(
    target_files_mocks: TargetFilesMocks,
    case: TargetFilesCase,
):
    """Test _get_target_files_or_log function behavior."""
    target_files_mocks['get_target_files'].return_value = case.mock_return_value

    result = _get_target_files_or_log(case.context)

    # Verify get_target_files was called with correct arguments
    target_files_mocks['get_target_files'].assert_called_once_with(
        case.context.profile,
        case.context.files,
        case.context.global_exclude_patterns,
        verbose=case.context.verbose,
    )

    # Verify result
    assert result == case.expected_result

    # Verify logging behavior
    if case.should_log_warning:
        target_files_mocks['logger'].warning.assert_called_once_with(
            case.context.log_type,
            profile=case.context.profile,
            provided_files=case.context.provided_files,
        )
    else:
        target_files_mocks['logger'].warning.assert_not_called()
