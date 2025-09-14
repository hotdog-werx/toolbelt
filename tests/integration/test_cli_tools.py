"""Integration tests for toolbelt CLI with different tool types.

These tests verify that toolbelt correctly handles:
1. Batch tools (like ruff) - process multiple files, output to stdout
2. Per-file tools (like add-trailing-comma) - process one file at a time
3. Write-to-file tools (like sed) - modify files in-place

Tests use fixture files with intentional issues to verify tool behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:  # moved to type-checking block per TC00x
    from collections.abc import Callable
    from pathlib import Path

    from .conftest import RunToolbeltCLI


@dataclass
class ToolTestCase:
    """Test case for a specific tool type."""

    name: str
    config_file: str
    test_files: list[str]
    command_args: list[str]
    expected_exit_code: int
    expected_output_fragments: list[str] | None = None
    expected_file_changes: dict[str, str] | None = None  # filename -> expected content fragment

    def __post_init__(self) -> None:
        """Post-initialization to normalize optional mutable defaults."""
        if self.expected_output_fragments is None:
            self.expected_output_fragments = []
        if self.expected_file_changes is None:
            self.expected_file_changes = {}


@pytest.mark.parametrize(
    'test_case',
    [
        ToolTestCase(
            name='ruff_batch_tool',
            config_file='ruff_batch.yaml',
            test_files=['bad_python_for_ruff.py'],
            command_args=['check', 'python'],
            expected_exit_code=1,  # Ruff should find issues
            expected_output_fragments=['bad_python_for_ruff.py'],
        ),
        ToolTestCase(
            name='add_trailing_comma_per_file',
            config_file='add_trailing_comma_per_file.yaml',
            test_files=['needs_trailing_comma.py'],
            command_args=['format', 'python'],
            expected_exit_code=0,  # add-trailing-comma returns 0 with --exit-zero-even-if-changed
            expected_file_changes={
                'needs_trailing_comma.py': 'arg3,',  # Should add trailing comma after multiline param list
            },
        ),
        ToolTestCase(
            name='text_replace_per_file',
            config_file='sed_write_to_file.yaml',
            test_files=['needs_sed_replacement.txt'],
            command_args=['format', 'text'],
            expected_exit_code=0,  # Should succeed
            expected_file_changes={
                'needs_sed_replacement.txt': 'new',  # Should replace 'old' with 'new'
            },
        ),
    ],
)
def test_tool_integration(
    test_case: ToolTestCase,
    tmp_path: Path,
    setup_test_environment: Callable[[str, list[str]], tuple[Path, list[Path]]],
    run_toolbelt_cli: RunToolbeltCLI,
) -> None:
    """Test different tool types work correctly through the CLI."""
    # Set up test environment
    _, file_paths = setup_test_environment(
        test_case.config_file,
        test_case.test_files,
    )

    # Store original file contents for comparison
    original_contents: dict[str, str] = {}
    for file_path in file_paths:
        original_contents[file_path.name] = file_path.read_text()

    # Run toolbelt command
    result = run_toolbelt_cli(test_case.command_args, cwd=tmp_path)

    # Check exit code
    assert result.returncode == test_case.expected_exit_code, (
        f"Test '{test_case.name}' failed with exit code {result.returncode}, "
        f'expected {test_case.expected_exit_code}.\n'
        f'Stdout: {result.stdout}\n'
        f'Stderr: {result.stderr}'
    )

    # Check output contains expected fragments
    combined_output = result.stdout + result.stderr
    for expected_fragment in test_case.expected_output_fragments or []:
        assert expected_fragment in combined_output, (
            f"Expected '{expected_fragment}' in output for test '{test_case.name}'.\nGot: {combined_output}"
        )

    # Check file changes
    for filename, expected_content_fragment in (test_case.expected_file_changes or {}).items():
        file_path = tmp_path / filename
        current_content = file_path.read_text()

        # Verify the expected change occurred
        assert expected_content_fragment in current_content, (
            f"Expected '{expected_content_fragment}' in {filename} after tool execution.\n"
            f'Original: {original_contents[filename]}\n'
            f'Current: {current_content}'
        )

        # Verify file actually changed (for tools that modify files)
        if filename in original_contents:
            original = original_contents[filename]
            if expected_content_fragment not in original:
                assert current_content != original, (
                    f'File {filename} should have been modified but appears unchanged.\nContent: {current_content}'
                )


def test_toolbelt_help_command(run_toolbelt_cli: RunToolbeltCLI) -> None:
    """Test that toolbelt --help works."""
    result = run_toolbelt_cli(['--help'])

    assert result.returncode == 0
    assert 'toolbelt' in result.stdout
    assert 'check' in result.stdout
    assert 'format' in result.stdout


def test_toolbelt_list_command(
    tmp_path: Path,
    setup_test_environment: Callable[[str, list[str]], tuple[Path, list[Path]]],
    run_toolbelt_cli: RunToolbeltCLI,
) -> None:
    """Test that toolbelt list shows configured profiles."""
    # Set up with any config
    _, _ = setup_test_environment('ruff_batch.yaml', [])

    result = run_toolbelt_cli(['list'], cwd=tmp_path)

    assert result.returncode == 0
    assert 'python' in result.stdout


def test_invalid_profile(
    tmp_path: Path,
    setup_test_environment: Callable[[str, list[str]], tuple[Path, list[Path]]],
    run_toolbelt_cli: RunToolbeltCLI,
) -> None:
    """Test error handling with invalid profile."""
    _, _ = setup_test_environment('ruff_batch.yaml', [])

    result = run_toolbelt_cli(['check', 'nonexistent'], cwd=tmp_path)

    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert 'invalid_profile' in output.lower()


def test_no_files_found(
    tmp_path: Path,
    setup_test_environment: Callable[[str, list[str]], tuple[Path, list[Path]]],
    run_toolbelt_cli: RunToolbeltCLI,
) -> None:
    """Test behavior when no matching files are found."""
    _, _ = setup_test_environment('ruff_batch.yaml', [])

    # Run check on empty directory
    result = run_toolbelt_cli(['check', 'python'], cwd=tmp_path)

    # Should handle gracefully (different tools may return different codes)
    assert result.returncode in [0, 1, 2]


def test_verbose_output(
    tmp_path: Path,
    setup_test_environment: Callable[[str, list[str]], tuple[Path, list[Path]]],
    run_toolbelt_cli: RunToolbeltCLI,
) -> None:
    """Test that verbose flag provides more detailed output."""
    _, _ = setup_test_environment(
        'ruff_batch.yaml',
        ['bad_python_for_ruff.py'],
    )

    # Run without verbose
    normal_result = run_toolbelt_cli(['check', 'python'], cwd=tmp_path)

    # Run with verbose
    verbose_result = run_toolbelt_cli(
        ['--verbose', 'check', 'python'],
        cwd=tmp_path,
    )

    # Verbose should provide more output
    verbose_output = verbose_result.stdout + verbose_result.stderr
    normal_output = normal_result.stdout + normal_result.stderr

    assert len(verbose_output) >= len(normal_output)


def test_specific_file_targeting(
    tmp_path: Path,
    setup_test_environment: Callable[[str, list[str]], tuple[Path, list[Path]]],
    run_toolbelt_cli: RunToolbeltCLI,
) -> None:
    """Test running tools on specific files rather than discovery mode."""
    _, file_paths = setup_test_environment(
        'ruff_batch.yaml',
        ['bad_python_for_ruff.py'],
    )

    # Run on specific file
    target_file = file_paths[0]
    result = run_toolbelt_cli(
        ['check', 'python', str(target_file)],
        cwd=tmp_path,
    )

    # Should work on the specific file
    assert result.returncode == 1  # Ruff should find issues
    output = result.stdout + result.stderr
    assert target_file.name in output


def test_multiple_files(
    tmp_path: Path,
    copy_fixture_config: Callable[[str, Path], Path],
    copy_fixture_file: Callable[[str, Path], Path],
    run_toolbelt_cli: RunToolbeltCLI,
) -> None:
    """Test running tools on multiple files."""
    # Set up multiple Python files
    copy_fixture_config('ruff_batch.yaml', tmp_path)
    file1 = copy_fixture_file('bad_python_for_ruff.py', tmp_path)
    file2 = copy_fixture_file('needs_trailing_comma.py', tmp_path)

    # Run check on all Python files
    result = run_toolbelt_cli(['check', 'python'], cwd=tmp_path)

    # Should process both files
    assert result.returncode == 1  # Should find issues in at least one file
    output = result.stdout + result.stderr
    # At least one of the files should be mentioned
    assert file1.name in output or file2.name in output
