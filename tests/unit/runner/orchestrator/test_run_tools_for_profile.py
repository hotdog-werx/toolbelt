from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict
from unittest.mock import MagicMock

import pytest

import toolbelt.runner.orchestrator as orchestrator_mod
from toolbelt.config import ToolbeltConfig
from toolbelt.config.models import ProfileConfig, ToolConfig
from toolbelt.runner.orchestrator import _run_tools_for_profile


# Grouped mocks for tools profile tests
class ToolsProfileMocks(TypedDict):
    get_target_files_or_log: MagicMock
    run_tool_branch: MagicMock
    logger: MagicMock


@pytest.fixture
def tools_profile_mocks(mocker) -> ToolsProfileMocks:
    return ToolsProfileMocks(
        get_target_files_or_log=mocker.patch.object(
            orchestrator_mod,
            '_get_target_files_or_log',
            return_value=None,  # Default to None, tests will override as needed
        ),
        run_tool_branch=mocker.patch.object(
            orchestrator_mod,
            '_run_tool_branch',
            return_value=0,
        ),
        logger=mocker.patch.object(orchestrator_mod, 'logger'),
    )


@dataclass
class ToolsProfileCase:
    desc: str
    profile_name: str
    files: list[Path] | None
    tool_type: str
    profile_config: ProfileConfig | None = None
    get_target_files_return: list[Path] | None = None
    run_tool_branch_results: list[int] | None = None
    expected_result: int = 0
    should_log_error: bool = False
    should_log_warning: bool = False


def create_test_config(profile: ProfileConfig | None = None) -> ToolbeltConfig:
    """Create a test ToolbeltConfig with optional profile."""
    config = ToolbeltConfig(
        global_exclude_patterns=[],
        variables={},
        profiles={},
    )
    if profile:
        config.profiles[profile.name] = profile
    return config


@pytest.mark.parametrize(
    'case',
    [
        ToolsProfileCase(
            desc='invalid_profile_returns_error',
            profile_name='nonexistent',
            files=None,
            tool_type='check',
            expected_result=1,
            should_log_error=True,
        ),
        ToolsProfileCase(
            desc='no_check_tools_returns_success_with_warning',
            profile_name='test-profile',
            files=None,
            tool_type='check',
            profile_config=ProfileConfig(
                name='test-profile',
                extensions=['.py'],
                check_tools=[],
                format_tools=[],
            ),
            expected_result=0,
            should_log_warning=True,
        ),
        ToolsProfileCase(
            desc='no_format_tools_returns_success_with_warning',
            profile_name='test-profile',
            files=None,
            tool_type='format',
            profile_config=ProfileConfig(
                name='test-profile',
                extensions=['.py'],
                check_tools=[],
                format_tools=[],
            ),
            expected_result=0,
            should_log_warning=True,
        ),
        ToolsProfileCase(
            desc='discovery_mode_success',
            profile_name='test-profile',
            files=None,
            tool_type='check',
            profile_config=ProfileConfig(
                name='test-profile',
                extensions=['.py'],
                check_tools=[
                    ToolConfig(
                        name='test-tool',
                        command='tool',
                        args=[],
                        description='Test tool',
                        file_handling_mode='batch',
                    ),
                ],
                format_tools=[],
            ),
            get_target_files_return=[
                Path('test.py'),
            ],  # Add explicit return value
            run_tool_branch_results=[0],
            expected_result=0,
        ),
        ToolsProfileCase(
            desc='file_mode_batch_tools_success',
            profile_name='test-profile',
            files=[Path('src/'), Path('tests/')],
            tool_type='check',
            profile_config=ProfileConfig(
                name='test-profile',
                extensions=['.py'],
                check_tools=[
                    ToolConfig(
                        name='batch-tool',
                        command='tool',
                        args=[],
                        description='Batch tool',
                        file_handling_mode='batch',
                    ),
                ],
                format_tools=[],
            ),
            get_target_files_return=[
                Path('test.py'),
            ],  # Add explicit return value
            run_tool_branch_results=[0],
            expected_result=0,
        ),
        ToolsProfileCase(
            desc='file_mode_per_file_tools_success',
            profile_name='test-profile',
            files=[Path('file1.py'), Path('file2.py')],
            tool_type='check',
            profile_config=ProfileConfig(
                name='test-profile',
                extensions=['.py'],
                check_tools=[
                    ToolConfig(
                        name='per-file-tool',
                        command='tool',
                        args=[],
                        description='Per file tool',
                        file_handling_mode='per_file',
                    ),
                ],
                format_tools=[],
            ),
            get_target_files_return=[Path('file1.py'), Path('file2.py')],
            run_tool_branch_results=[0],
            expected_result=0,
        ),
        ToolsProfileCase(
            desc='file_mode_per_file_no_target_files_found',
            profile_name='test-profile',
            files=[Path('nonexistent.py')],
            tool_type='check',
            profile_config=ProfileConfig(
                name='test-profile',
                extensions=['.py'],
                check_tools=[
                    ToolConfig(
                        name='per-file-tool',
                        command='tool',
                        args=[],
                        description='Per file tool',
                        file_handling_mode='per_file',
                    ),
                ],
                format_tools=[],
            ),
            get_target_files_return=None,
            expected_result=0,
        ),
        ToolsProfileCase(
            desc='tool_failure_propagates',
            profile_name='test-profile',
            files=None,
            tool_type='check',
            profile_config=ProfileConfig(
                name='test-profile',
                extensions=['.py'],
                check_tools=[
                    ToolConfig(
                        name='failing-tool',
                        command='tool',
                        args=[],
                        description='Failing tool',
                        file_handling_mode='batch',
                    ),
                ],
                format_tools=[],
            ),
            get_target_files_return=[
                Path('test.py'),
            ],  # Add explicit return value
            run_tool_branch_results=[1],
            expected_result=1,
        ),
        ToolsProfileCase(
            desc='multiple_tools_first_fails',
            profile_name='test-profile',
            files=None,
            tool_type='check',
            profile_config=ProfileConfig(
                name='test-profile',
                extensions=['.py'],
                check_tools=[
                    ToolConfig(
                        name='failing-tool',
                        command='tool1',
                        args=[],
                        description='Failing tool',
                        file_handling_mode='batch',
                    ),
                    ToolConfig(
                        name='success-tool',
                        command='tool2',
                        args=[],
                        description='Success tool',
                        file_handling_mode='batch',
                    ),
                ],
                format_tools=[],
            ),
            get_target_files_return=[
                Path('test.py'),
            ],  # Add explicit return value
            run_tool_branch_results=[1, 0],
            expected_result=1,
        ),
        ToolsProfileCase(
            desc='multiple_tools_second_fails',
            profile_name='test-profile',
            files=None,
            tool_type='check',
            profile_config=ProfileConfig(
                name='test-profile',
                extensions=['.py'],
                check_tools=[
                    ToolConfig(
                        name='success-tool',
                        command='tool1',
                        args=[],
                        description='Success tool',
                        file_handling_mode='batch',
                    ),
                    ToolConfig(
                        name='failing-tool',
                        command='tool2',
                        args=[],
                        description='Failing tool',
                        file_handling_mode='batch',
                    ),
                ],
                format_tools=[],
            ),
            get_target_files_return=[
                Path('test.py'),
            ],  # Add explicit return value
            run_tool_branch_results=[0, 1],
            expected_result=1,
        ),
    ],
    ids=lambda c: c.desc,
)
def test_run_tools_for_profile(
    tools_profile_mocks: ToolsProfileMocks,
    case: ToolsProfileCase,
):
    """Test _run_tools_for_profile function behavior."""
    # Create config with test profile
    config = create_test_config(case.profile_config)

    # Set up mocks
    if case.get_target_files_return is not None:
        tools_profile_mocks['get_target_files_or_log'].return_value = case.get_target_files_return

    if case.run_tool_branch_results:
        tools_profile_mocks['run_tool_branch'].side_effect = case.run_tool_branch_results

    # Execute function
    result = _run_tools_for_profile(
        config,
        case.profile_name,
        files=case.files,
        verbose=False,
        tool_type=case.tool_type,
    )

    # Verify result
    assert result == case.expected_result

    # Verify logging behavior
    if case.should_log_error:
        tools_profile_mocks['logger'].error.assert_called_once()
        error_call = tools_profile_mocks['logger'].error.call_args
        assert error_call[0][0] == 'invalid_profile'

    if case.should_log_warning:
        tools_profile_mocks['logger'].warning.assert_called_once()
        warning_call = tools_profile_mocks['logger'].warning.call_args
        expected_msg = f'no_{case.tool_type}ers'
        assert warning_call[0][0] == expected_msg

    # Verify tool execution
    if case.profile_config and getattr(
        case.profile_config,
        f'{case.tool_type}_tools',
    ):
        # Check if this is a case where execution should be skipped
        is_per_file_only = not any(
            tool.file_handling_mode == 'batch' for tool in getattr(case.profile_config, f'{case.tool_type}_tools')
        )
        should_skip = case.get_target_files_return is None and case.files and is_per_file_only

        if should_skip:
            # Per-file mode with no target files found should skip tool execution entirely
            assert tools_profile_mocks['run_tool_branch'].call_count == 0
        else:
            expected_calls = len(
                getattr(case.profile_config, f'{case.tool_type}_tools'),
            )
            assert tools_profile_mocks['run_tool_branch'].call_count == expected_calls


def test_run_tools_for_profile_mixed_tool_types_batch_priority(
    tools_profile_mocks: ToolsProfileMocks,
):
    """Test that when profile has both batch and per_file tools, batch takes priority for file handling."""
    profile = ProfileConfig(
        name='mixed-profile',
        extensions=['.py'],
        check_tools=[
            ToolConfig(
                name='batch-tool',
                command='batch',
                args=[],
                description='Batch tool',
                file_handling_mode='batch',
            ),
            ToolConfig(
                name='per-file-tool',
                command='perfile',
                args=[],
                description='Per file tool',
                file_handling_mode='per_file',
            ),
        ],
        format_tools=[],
    )
    config = create_test_config(profile)

    files = [Path('src/'), Path('nonexistent.py')]

    # Set explicit return value for mixed mode
    tools_profile_mocks['get_target_files_or_log'].return_value = [
        Path('test.py'),
    ]
    tools_profile_mocks['run_tool_branch'].return_value = 0

    result = _run_tools_for_profile(
        config,
        'mixed-profile',
        files=files,
        verbose=False,
        tool_type='check',
    )

    # Should use batch mode (pass files directly) and not call get_target_files_or_log
    assert result == 0
    tools_profile_mocks['get_target_files_or_log'].assert_not_called()

    # Should log with provided_paths (batch mode)
    tools_profile_mocks['logger'].info.assert_called_once()
    log_call = tools_profile_mocks['logger'].info.call_args
    assert log_call[0][0] == 'checking'
    assert 'provided_paths' in log_call[1]


def test_run_tools_for_profile_per_file_only_filters_files(
    tools_profile_mocks: ToolsProfileMocks,
):
    """Test that when profile has only per_file tools, files are filtered."""
    profile = ProfileConfig(
        name='per-file-profile',
        extensions=['.py'],
        check_tools=[
            ToolConfig(
                name='per-file-tool',
                command='perfile',
                args=[],
                description='Per file tool',
                file_handling_mode='per_file',
            ),
        ],
        format_tools=[],
    )
    config = create_test_config(profile)

    files = [Path('file1.py'), Path('file2.py')]
    tools_profile_mocks['get_target_files_or_log'].return_value = [
        Path('file1.py'),
    ]
    tools_profile_mocks['run_tool_branch'].return_value = 0

    result = _run_tools_for_profile(
        config,
        'per-file-profile',
        files=files,
        verbose=False,
        tool_type='check',
    )

    # Should filter files and call get_target_files_or_log
    assert result == 0
    tools_profile_mocks['get_target_files_or_log'].assert_called_once()

    # Should log with file_count (per_file mode)
    tools_profile_mocks['logger'].info.assert_called_once()
    log_call = tools_profile_mocks['logger'].info.call_args
    assert log_call[0][0] == 'checking'
    assert 'file_count' in log_call[1]
