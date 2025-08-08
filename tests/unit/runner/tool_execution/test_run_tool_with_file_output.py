from pathlib import Path
from unittest.mock import MagicMock

from pytest_mock import MockerFixture
from dataclasses import dataclass

import pytest
import toolbelt.runner.tool_execution as tool_exec_mod
from toolbelt.config.models import ToolConfig
from toolbelt.runner.tool_execution import run_tool_with_file_output


def test_run_tool_with_file_output_success(mocker: MockerFixture):
    tool = ToolConfig(
        name='formatter',
        command='yq',
        args=['eval', '.'],
        description='Format YAML',
        file_handling_mode='per_file',
        output_to_file=True,
    )
    test_file = Path('test.yaml')
    files = [test_file]

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = 'formatted: yaml\ncontent: here\n'
    mock_result.stderr = ''
    mock_subprocess = mocker.patch.object(
        tool_exec_mod.subprocess,
        'run',
        return_value=mock_result,
    )
    mock_write = mocker.patch.object(Path, 'write_text')
    result = run_tool_with_file_output(tool, files)
    mock_subprocess.assert_called_once()
    mock_write.assert_called_once_with('formatted: yaml\ncontent: here\n')
    assert result == 0


def test_run_tool_with_file_output_with_variables(mocker: MockerFixture):
    tool = ToolConfig(
        name='formatter',
        command='${FORMATTER_CMD}',
        args=['--config=${CONFIG_PATH}'],
        description='Format files',
        file_handling_mode='per_file',
        output_to_file=True,
    )
    test_file = Path('test.py')
    files = [test_file]
    variables = {'FORMATTER_CMD': 'black', 'CONFIG_PATH': 'pyproject.toml'}

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = 'formatted python code\n'
    mock_result.stderr = ''
    mock_subprocess = mocker.patch.object(
        tool_exec_mod.subprocess,
        'run',
        return_value=mock_result,
    )
    mock_write = mocker.patch.object(Path, 'write_text')
    result = run_tool_with_file_output(tool, files, variables)
    cmd_called = mock_subprocess.call_args[0][0]
    assert 'black' in cmd_called
    assert '--config=pyproject.toml' in cmd_called
    assert str(test_file) in cmd_called
    mock_write.assert_called_once_with('formatted python code\n')
    assert result == 0


@dataclass
class FileOutputCase:
    tool: ToolConfig
    files: list
    mock_results: list
    expected_write_count: int
    expected_return: int
    desc: str


@pytest.mark.parametrize(
    'case',
    [
        FileOutputCase(
            tool=ToolConfig(
                name='formatter',
                command='prettier',
                args=['--write'],
                description='Format JS',
                file_handling_mode='per_file',
                output_to_file=True,
            ),
            files=[Path('file1.js'), Path('file2.js')],
            mock_results=[
                MagicMock(returncode=0, stdout='formatted file1\n', stderr=''),
                MagicMock(returncode=0, stdout='formatted file2\n', stderr=''),
            ],
            expected_write_count=2,
            expected_return=0,
            desc='all files succeed',
        ),
        FileOutputCase(
            tool=ToolConfig(
                name='formatter',
                command='flaky-tool',
                args=[],
                description='Sometimes works',
                file_handling_mode='per_file',
                output_to_file=True,
            ),
            files=[Path('good.txt'), Path('bad.txt'), Path('good2.txt')],
            mock_results=[
                MagicMock(
                    returncode=0,
                    stdout='good content\n',
                    stderr='',
                ),  # Success
                MagicMock(returncode=1, stdout='', stderr='error\n'),  # Failure
                MagicMock(
                    returncode=0,
                    stdout='more good content\n',
                    stderr='',
                ),  # Success
            ],
            expected_write_count=2,
            expected_return=1,
            desc='mixed success and failure',
        ),
        FileOutputCase(
            tool=ToolConfig(
                name='formatter',
                command='failing-tool',
                args=[],
                description='Failing formatter',
                file_handling_mode='per_file',
                output_to_file=True,
            ),
            files=[Path('test.txt')],
            mock_results=[
                MagicMock(
                    returncode=1,
                    stdout='',
                    stderr='Tool error occurred\n',
                ),
            ],
            expected_write_count=0,
            expected_return=1,
            desc='tool failure',
        ),
        FileOutputCase(
            tool=ToolConfig(
                name='validator',
                command='check-tool',
                args=[],
                description='Validator that produces no output',
                file_handling_mode='per_file',
                output_to_file=True,
            ),
            files=[Path('test.txt')],
            mock_results=[
                MagicMock(returncode=0, stdout='', stderr=''),
            ],
            expected_write_count=0,
            expected_return=0,
            desc='empty output',
        ),
    ],
    ids=lambda c: c.desc,
)
def test_run_tool_with_file_output_cases(mocker: MockerFixture, case):
    """Test run_tool_with_file_output for multiple files, error, and empty output cases."""
    mock_subprocess = mocker.patch.object(
        tool_exec_mod.subprocess,
        'run',
        side_effect=case.mock_results,
    )
    mock_write = mocker.patch.object(Path, 'write_text')
    result = run_tool_with_file_output(case.tool, case.files)
    assert mock_subprocess.call_count == len(case.files), (
        f'Expected subprocess.run called {len(case.files)} times, got {mock_subprocess.call_count}'
    )
    assert mock_write.call_count == case.expected_write_count, (
        f'Expected write_text called {case.expected_write_count} times, got {mock_write.call_count}'
    )
    assert result == case.expected_return, f'Expected return {case.expected_return}, got {result}'


def test_run_tool_with_file_output_file_not_found_error(mocker: MockerFixture):
    tool = ToolConfig(
        name='missing-tool',
        command='nonexistent-command',
        args=[],
        description='Missing tool',
        file_handling_mode='per_file',
        output_to_file=True,
    )
    test_file = Path('test.txt')
    files = [test_file]
    mock_subprocess = mocker.patch.object(
        tool_exec_mod.subprocess,
        'run',
        side_effect=FileNotFoundError('Command not found'),
    )
    mock_write = mocker.patch.object(Path, 'write_text')
    result = run_tool_with_file_output(tool, files)
    mock_write.assert_not_called()
    assert result == 1, f'Expected failure code 1, got {result}'


def test_run_tool_with_file_output_working_directory(mocker: MockerFixture):
    tool = ToolConfig(
        name='formatter',
        command='tool',
        args=[],
        description='Tool with custom working dir',
        file_handling_mode='per_file',
        output_to_file=True,
        working_dir='/custom/workdir',
    )
    test_file = Path('test.txt')
    files = [test_file]

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = 'formatted\n'
    mock_result.stderr = ''
    mock_subprocess = mocker.patch.object(
        tool_exec_mod.subprocess,
        'run',
        return_value=mock_result,
    )
    mocker.patch.object(Path, 'write_text')
    result = run_tool_with_file_output(tool, files)
    mock_subprocess.assert_called_once()
    call_kwargs = mock_subprocess.call_args[1]
    assert call_kwargs['cwd'] == '/custom/workdir'
    assert result == 0


def test_run_tool_with_file_output_no_variables(mocker: MockerFixture):
    tool = ToolConfig(
        name='formatter',
        command='tool',
        args=[],
        description='Simple tool',
        file_handling_mode='per_file',
        output_to_file=True,
    )
    test_file = Path('test.txt')
    files = [test_file]

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = 'output\n'
    mock_result.stderr = ''
    mock_subprocess = mocker.patch.object(
        tool_exec_mod.subprocess,
        'run',
        return_value=mock_result,
    )
    mocker.patch.object(Path, 'write_text')
    result = run_tool_with_file_output(tool, files)
    assert result == 0
