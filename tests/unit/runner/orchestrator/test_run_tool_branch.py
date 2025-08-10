"""Tests for _run_tool_branch function."""

from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, Unpack
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

import toolbelt.runner.orchestrator as orchestrator_mod
from toolbelt.config.models import ProfileConfig, ToolConfig
from toolbelt.runner.orchestrator import ToolBranchContext, _run_tool_branch


# Grouped mocks for tool branch tests
class ToolBranchMocks(TypedDict):
    get_target_files: MagicMock
    run_tool_with_file_output: MagicMock
    run_tool_per_file_mode: MagicMock
    run_tool_in_discovery_mode: MagicMock
    logger: MagicMock


@pytest.fixture
def tool_branch_mocks(mocker: MockerFixture) -> ToolBranchMocks:
    return ToolBranchMocks(
        get_target_files=mocker.patch.object(
            orchestrator_mod,
            'get_target_files',
            return_value=[Path('test.py')],
        ),
        run_tool_with_file_output=mocker.patch.object(
            orchestrator_mod,
            'run_tool_with_file_output',
            return_value=0,
        ),
        run_tool_per_file_mode=mocker.patch.object(
            orchestrator_mod,
            'run_tool_per_file_mode',
            return_value=0,
        ),
        run_tool_in_discovery_mode=mocker.patch.object(
            orchestrator_mod,
            'run_tool_in_discovery_mode',
            return_value=0,
        ),
        logger=mocker.patch.object(orchestrator_mod, 'logger'),
    )


@dataclass
class ToolBranchCase:
    desc: str
    tool: ToolConfig
    context_overrides: dict | None = None
    variables: dict[str, str] | None = None
    get_target_files_return: list[Path] | None = None
    expected_execution_mode: str = ''  # 'file_output', 'per_file', 'batch', 'error'
    expected_result: int = 0


class ToolConfigOverrides(TypedDict):
    use_file_mode: bool
    target_files: list[Path] | None


def create_base_context(
    tool: ToolConfig,
    **overrides: Unpack[ToolConfigOverrides],
) -> ToolBranchContext:
    """Create a base ToolBranchContext with optional overrides."""
    defaults = {
        'profile': ProfileConfig(
            name='test-profile',
            extensions=['.py'],
            check_tools=[],
            format_tools=[],
        ),
        'use_file_mode': False,
        'target_files': None,
        'global_exclude_patterns': [],
        'verbose': False,
    }
    defaults.update(overrides or {})
    return ToolBranchContext(tool=tool, **defaults)


@pytest.mark.parametrize(
    'case',
    [
        ToolBranchCase(
            desc='output_to_file_with_target_files',
            tool=ToolConfig(
                name='test-tool',
                command='tool',
                args=[],
                description='Test tool',
                output_to_file=True,
                file_handling_mode='per_file',
            ),
            context_overrides={
                'use_file_mode': True,
                'target_files': [Path('src/')],
            },
            get_target_files_return=[Path('file1.py'), Path('file2.py')],
            expected_execution_mode='file_output',
        ),
        ToolBranchCase(
            desc='output_to_file_discovery_mode',
            tool=ToolConfig(
                name='test-tool',
                command='tool',
                args=[],
                description='Test tool',
                output_to_file=True,
                file_handling_mode='per_file',
            ),
            context_overrides={'use_file_mode': False, 'target_files': None},
            get_target_files_return=[Path('discovered.py')],
            expected_execution_mode='file_output',
        ),
        ToolBranchCase(
            desc='output_to_file_no_files_found',
            tool=ToolConfig(
                name='test-tool',
                command='tool',
                args=[],
                description='Test tool',
                output_to_file=True,
                file_handling_mode='per_file',
            ),
            context_overrides={'use_file_mode': False, 'target_files': None},
            get_target_files_return=[],
            expected_execution_mode='no_files_warning',
            expected_result=0,
        ),
        ToolBranchCase(
            desc='per_file_mode_with_target_files',
            tool=ToolConfig(
                name='test-tool',
                command='tool',
                args=[],
                description='Test tool',
                file_handling_mode='per_file',
            ),
            context_overrides={
                'use_file_mode': True,
                'target_files': [Path('src/')],
            },
            get_target_files_return=[Path('file1.py')],
            expected_execution_mode='per_file',
        ),
        ToolBranchCase(
            desc='per_file_mode_discovery',
            tool=ToolConfig(
                name='test-tool',
                command='tool',
                args=[],
                description='Test tool',
                file_handling_mode='per_file',
            ),
            context_overrides={'use_file_mode': False, 'target_files': None},
            get_target_files_return=[Path('discovered.py')],
            expected_execution_mode='per_file',
        ),
        ToolBranchCase(
            desc='per_file_mode_no_files_found',
            tool=ToolConfig(
                name='test-tool',
                command='tool',
                args=[],
                description='Test tool',
                file_handling_mode='per_file',
            ),
            context_overrides={'use_file_mode': False, 'target_files': None},
            get_target_files_return=[],
            expected_execution_mode='no_files_warning',
            expected_result=0,
        ),
        ToolBranchCase(
            desc='batch_mode_with_target_files',
            tool=ToolConfig(
                name='test-tool',
                command='tool',
                args=[],
                description='Test tool',
                file_handling_mode='batch',
            ),
            context_overrides={
                'use_file_mode': True,
                'target_files': [Path('src/'), Path('tests/')],
            },
            expected_execution_mode='batch',
        ),
        ToolBranchCase(
            desc='batch_mode_discovery_with_default_target',
            tool=ToolConfig(
                name='test-tool',
                command='tool',
                args=[],
                description='Test tool',
                file_handling_mode='batch',
                default_target='src/',
            ),
            context_overrides={'use_file_mode': False, 'target_files': None},
            expected_execution_mode='batch',
        ),
        ToolBranchCase(
            desc='batch_mode_discovery_no_default_target',
            tool=ToolConfig(
                name='test-tool',
                command='tool',
                args=[],
                description='Test tool',
                file_handling_mode='batch',
            ),
            context_overrides={'use_file_mode': False, 'target_files': None},
            expected_execution_mode='batch',
        ),
        ToolBranchCase(
            desc='invalid_file_handling_mode',
            tool=ToolConfig(
                name='test-tool',
                command='tool',
                args=[],
                description='Test tool',
                file_handling_mode='batch',  # We'll patch this in the test
            ),
            expected_execution_mode='error',
            expected_result=1,
        ),
    ],
    ids=lambda c: c.desc,
)
def test_run_tool_branch(
    tool_branch_mocks: ToolBranchMocks,
    case: ToolBranchCase,
):
    """Test _run_tool_branch function behavior."""
    # Create context with tool
    context = create_base_context(case.tool, **(case.context_overrides or {}))

    # Handle invalid file handling mode test by patching the tool
    if case.desc == 'invalid_file_handling_mode':
        context.tool.file_handling_mode = 'invalid'  # type: ignore - testing invalid value

    # Set up get_target_files mock if specified
    if case.get_target_files_return is not None:
        tool_branch_mocks['get_target_files'].return_value = case.get_target_files_return

    # Set up execution mode mocks to return expected result
    for mock_name in [
        'run_tool_with_file_output',
        'run_tool_per_file_mode',
        'run_tool_in_discovery_mode',
    ]:
        tool_branch_mocks[mock_name].return_value = case.expected_result

    # Execute function
    result = _run_tool_branch(context, case.variables)

    # Verify result
    assert result == case.expected_result

    # Verify correct execution path was taken
    if case.expected_execution_mode == 'file_output':
        tool_branch_mocks['run_tool_with_file_output'].assert_called_once()
        tool_branch_mocks['run_tool_per_file_mode'].assert_not_called()
        tool_branch_mocks['run_tool_in_discovery_mode'].assert_not_called()
    elif case.expected_execution_mode == 'per_file':
        tool_branch_mocks['run_tool_per_file_mode'].assert_called_once()
        tool_branch_mocks['run_tool_with_file_output'].assert_not_called()
        tool_branch_mocks['run_tool_in_discovery_mode'].assert_not_called()
    elif case.expected_execution_mode == 'batch':
        tool_branch_mocks['run_tool_in_discovery_mode'].assert_called_once()
        tool_branch_mocks['run_tool_with_file_output'].assert_not_called()
        tool_branch_mocks['run_tool_per_file_mode'].assert_not_called()
    elif case.expected_execution_mode == 'no_files_warning':
        tool_branch_mocks['logger'].warning.assert_called_once()
        # Verify warning message
        warning_call = tool_branch_mocks['logger'].warning.call_args
        assert warning_call[0][0] == 'no_files_found'
        assert warning_call[1]['tool'] == case.tool.name
    elif case.expected_execution_mode == 'error':
        tool_branch_mocks['logger'].error.assert_called_once()
        # Verify error message
        error_call = tool_branch_mocks['logger'].error.call_args
        assert error_call[0][0] == 'invalid_file_handling_mode'
        assert error_call[1]['tool'] == case.tool.name
        assert error_call[1]['file_handling_mode'] == 'invalid'


def test_run_tool_branch_batch_mode_targets(tool_branch_mocks: ToolBranchMocks):
    """Test that batch mode passes correct targets to run_tool_in_discovery_mode."""
    # Test with target files
    tool = ToolConfig(
        name='test-tool',
        command='tool',
        args=[],
        description='Test tool',
        file_handling_mode='batch',
    )
    context = create_base_context(
        tool,
        use_file_mode=True,
        target_files=[Path('src/'), Path('tests/')],
    )

    _run_tool_branch(context)

    tool_branch_mocks['run_tool_in_discovery_mode'].assert_called_once_with(
        tool,
        targets=['src', 'tests'],  # Path.str() removes trailing slash
        variables=None,
    )


def test_run_tool_branch_batch_mode_default_target(
    tool_branch_mocks: ToolBranchMocks,
):
    """Test that batch mode uses default_target when in discovery mode."""
    tool = ToolConfig(
        name='test-tool',
        command='tool',
        args=[],
        description='Test tool',
        file_handling_mode='batch',
        default_target='custom/',
    )
    context = create_base_context(tool, use_file_mode=False, target_files=None)

    _run_tool_branch(context)

    tool_branch_mocks['run_tool_in_discovery_mode'].assert_called_once_with(
        tool,
        targets=['custom/'],
        variables=None,
    )


def test_run_tool_branch_batch_mode_no_default_target(
    tool_branch_mocks: ToolBranchMocks,
):
    """Test that batch mode uses '.' when no default_target and in discovery mode."""
    tool = ToolConfig(
        name='test-tool',
        command='tool',
        args=[],
        description='Test tool',
        file_handling_mode='batch',
    )
    context = create_base_context(tool, use_file_mode=False, target_files=None)

    _run_tool_branch(context)

    tool_branch_mocks['run_tool_in_discovery_mode'].assert_called_once_with(
        tool,
        targets=['.'],
        variables=None,
    )
