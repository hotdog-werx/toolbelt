import subprocess
from pathlib import Path

from pytest_mock import MockerFixture

from toolbelt.config.models import ToolConfig
from toolbelt.runner.tool_execution import run_tool_with_file_output


def test_run_tool_with_file_output_subprocess_error(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    """Test handling subprocess errors."""
    # Create test file
    test_file = tmp_path / 'test.yaml'
    test_file.write_text('original: content')

    # Create tool config
    tool = ToolConfig(
        name='problematic',
        command='problematic-command',
        description='Tool that raises subprocess error',
        args=['format'],
        file_handling_mode='per_file',
        output_to_file=True,
        working_dir=None,
    )

    # Mock subprocess.run to raise subprocess error
    mock_run = mocker.patch(
        'toolbelt.runner.tool_execution.subprocess.run',
        side_effect=subprocess.SubprocessError('Subprocess failed'),
    )

    # Run the function
    exit_code = run_tool_with_file_output(tool, [test_file])

    # Verify behavior
    assert mock_run.call_count == 1, f'Expected 1 subprocess call, got {mock_run.call_count}'
    assert exit_code == 1, f'Expected failure exit code 1, got {exit_code}'

    # Verify file was not modified
    content = test_file.read_text()
    assert content == 'original: content', f'Expected original content preserved, got {content!r}'
