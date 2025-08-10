import os
import subprocess  # nosec S603
import sys
from os.path import normpath
from pathlib import Path

from toolbelt.config import ToolConfig, get_tool_command
from toolbelt.logging import get_logger
from toolbelt.runner.utils import expand_globs_in_args

logger = get_logger(__name__)


def _log_exception(
    error: Exception,
    *,
    tool: ToolConfig,
    command: list[str] | None = None,
    file: str | None = None,
    context: str = '',
) -> None:
    """Log exceptions in a unified way."""
    error_type = type(error).__name__
    if isinstance(error, FileNotFoundError):
        logger.exception(
            'command_not_found',
            tool=tool.name,
            command=tool.command if command is None else ' '.join(command),
            file=file,
            error=str(error),
            error_type=error_type,
            context=context,
        )
    elif isinstance(error, (OSError, subprocess.SubprocessError)):
        logger.exception(
            'unexpected_error',
            tool=tool.name,
            command=tool.command if command is None else ' '.join(command),
            file=file,
            error=str(error),
            error_type=error_type,
            context=context,
        )
    else:
        logger.exception(
            'failed',
            tool=tool.name,
            command=tool.command if command is None else ' '.join(command),
            file=file,
            error=str(error),
            error_type=error_type,
            context=context,
        )


def get_max_display_files() -> int:
    """Get the maximum number of files to display in logs.

    Returns:
        The maximum number of files to display, defaulting to 5 if not set.
    """
    max_display_raw = os.environ.get('TOOLBELT_MAX_DISPLAY_FILES', '5')
    try:
        return int(max_display_raw)
    except ValueError:
        return 5


def _build_log_context(
    tool: ToolConfig,
    command_parts: list[str],
) -> dict[str, str]:
    """Build logger context with optional working_dir."""
    log_context = {
        'tool': tool.name,
        'command': ' '.join(command_parts),
    }
    work_dir = tool.working_dir
    if work_dir and normpath(str(Path.cwd())) != normpath(str(work_dir)):
        log_context['working_dir'] = work_dir
    return log_context


def _handle_file_processing_error(
    file_path: Path,
    tool: ToolConfig,
    error: Exception,
    failed_files: list[str],
) -> None:
    """Handle errors during file processing."""
    _log_exception(
        error,
        tool=tool,
        command=None,
        file=str(file_path),
        context='file_processing',
    )
    failed_files.append(str(file_path))


def run_tool_with_file_output(
    tool: ToolConfig,
    files: list[Path],
    variables: dict[str, str] | None = None,
) -> int:
    """Run a tool that outputs to stdout, capturing output and writing to files.

    Args:
        tool: The tool configuration to use.
        files: The list of files to process.
        variables: Template variables for expansion.

    Returns:
        The exit code (0 for success, non-zero for failure).
    """
    if variables is None:
        variables = {}

    failed_files: list[str] = []

    for file_path in files:
        try:
            # Build command using new model - for output_to_file, pass individual file
            cmd = get_tool_command(
                tool,
                files=[str(file_path)],
                variables=variables,
            ).full_command

            logger.debug(
                'executing_with_output_capture',
                tool=tool.name,
                file=str(file_path),
            )

            # Run the tool and capture stdout
            # nosec S603: We intentionally allow execution of developer tool commands from config.
            result = subprocess.run(  # noqa: S603
                cmd,
                capture_output=True,
                text=True,
                cwd=tool.working_dir,
                check=False,
            )

            if result.returncode != 0:
                logger.error(
                    'tool_failed',
                    tool=tool.name,
                    file=str(file_path),
                    exit_code=result.returncode,
                    stderr=result.stderr.strip() if result.stderr else '',
                )
                failed_files.append(str(file_path))
                continue

            # Write the output back to the file
            if result.stdout:
                file_path.write_text(result.stdout)
                logger.debug(
                    'updated_file',
                    tool=tool.name,
                    file=str(file_path),
                )
            else:
                logger.warning(
                    'empty_output',
                    tool=tool.name,
                    file=str(file_path),
                )

        except (FileNotFoundError, OSError, subprocess.SubprocessError) as e:
            _handle_file_processing_error(file_path, tool, e, failed_files)

    if failed_files:
        logger.info(
            'completed_with_failures',
            tool=tool.name,
            failed_count=len(failed_files),
            total_count=len(files),
            failed_files=failed_files,
        )
        return 1

    logger.info(
        'completed_successfully',
        tool=tool.name,
        processed_count=len(files),
    )
    return 0


def run_tool_per_file_mode(
    tool: ToolConfig,
    *,
    files: list[Path],
    variables: dict[str, str] | None = None,
) -> int:
    """Run a tool in per-file mode, passing all files to the tool at once.

    Args:
        tool: The tool configuration to use.
        files: The list of files to process.
        variables: Template variables for expansion.

    Returns:
        The exit code of the tool.
    """
    if variables is None:
        variables = {}

    # Build command with all files
    file_strings = [str(f) for f in files]
    cmd = get_tool_command(
        tool,
        files=file_strings,
        variables=variables,
    ).full_command

    # For logging: show up to TOOLBelt_MAX_DISPLAY_FILES
    max_display = get_max_display_files()
    logged_files = file_strings[:max_display] if max_display > 0 else file_strings

    # Build log context with potentially truncated file list
    log_cmd = cmd[:]
    if len(file_strings) > max_display > 0:
        # Replace files in cmd with truncated list for logging
        tool_cmd = get_tool_command(tool, variables=variables)
        log_cmd = tool_cmd.base_command + logged_files + ['...']

    log_context = _build_log_context(tool, log_cmd)
    log_context['file_count'] = str(len(files))

    logger.info('executing', **log_context)
    return execute_command(cmd, tool)


def run_tool_in_discovery_mode(
    tool: ToolConfig,
    *,
    variables: dict[str, str] | None = None,
    targets: list[str] | None = None,
) -> int:
    """Run a tool in discovery/batch mode (let it find files itself or pass targets).

    Args:
        tool: The tool configuration to use.
        variables: Template variables for expansion.
        targets: Target directories/files to append to the command.

    Returns:
        The exit code of the tool.
    """
    if variables is None:
        variables = {}

    # Build command using targets
    cmd = get_tool_command(
        tool,
        targets=targets,
        variables=variables,
    ).full_command

    log_context = _build_log_context(tool, cmd)
    logger.info('executing', **log_context)
    return execute_command(cmd, tool)


def execute_command(cmd: list[str], tool: ToolConfig) -> int:
    """Execute a command and handle errors.

    Args:
        cmd: The command to execute.
        tool: The tool configuration to use.

    Returns:
        The exit code of the tool.
    """
    try:
        # Expand glob patterns in command arguments
        expanded_cmd = expand_globs_in_args(cmd)

        logger.debug('started', tool=tool.name, command=expanded_cmd)

        # Run the tool
        # nosec S603: We intentionally allow execution of developer tool commands from config.
        # See README for security considerations.
        result = subprocess.run(  # noqa: S603
            expanded_cmd,
            check=False,
            cwd=tool.working_dir,
            capture_output=False,  # Let output go to terminal
            text=True,
        )
        logger.debug(
            'completed',
            tool=tool.name,
            exit_code=result.returncode,
            success=result.returncode == 0,
        )
        sys.stdout.write('\n')
    except Exception as e:  # noqa: BLE001 - Broad exception handling for all errors
        _log_exception(
            e,
            tool=tool,
            command=cmd,
            file=None,
            context='execute_command',
        )
        return 1
    return result.returncode
