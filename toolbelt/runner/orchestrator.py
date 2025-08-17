from dataclasses import dataclass
from pathlib import Path

from toolbelt.config import ProfileConfig, ToolbeltConfig
from toolbelt.config.models import ToolConfig
from toolbelt.logging import get_logger
from toolbelt.runner.file_discovery import get_target_files
from toolbelt.runner.tool_execution import (
    run_tool_in_discovery_mode,
    run_tool_per_file_mode,
    run_tool_with_file_output,
)


@dataclass
class ToolExecutionContext:
    """Context for executing multiple tools within a profile.

    This groups parameters needed when executing all tools for a profile,
    encapsulating the tool list, profile configuration, and execution mode.

    Args:
        tools: List of tools to execute
        profile: The profile configuration containing file patterns and settings
        config: Global toolbelt configuration with variables and settings
        use_file_mode: True if specific files provided, False for discovery mode
        target_files: Resolved list of files to process (None for discovery mode)
        verbose: Whether to enable verbose logging during execution
    """

    tools: list[ToolConfig]
    profile: ProfileConfig
    config: ToolbeltConfig
    use_file_mode: bool
    target_files: list[Path] | None
    verbose: bool


@dataclass
class TargetDeterminationContext:
    """Context for determining target files based on tool types and provided files.

    This groups parameters needed when deciding how to handle file targeting
    for different tool types (batch vs per-file) and execution modes.

    Args:
        files: Optional list of specific files/paths provided by user
        profile: The profile configuration containing file patterns and excludes
        config: Global toolbelt configuration with exclude patterns
        verbose: Whether to enable verbose logging during file discovery
        tool_type: Type of tools ('check' or 'format') for logging purposes
        tools: List of tools that will be executed
    """

    files: list[Path] | None
    profile: ProfileConfig
    config: ToolbeltConfig
    verbose: bool
    tool_type: str
    tools: list[ToolConfig]


@dataclass
class TargetFilesContext:
    """Context for target files discovery.

    This groups parameters needed when discovering files for per_file mode tools.
    Used when we need to filter provided files to only existing, valid files
    that match the profile's file patterns.

    Args:
        profile: The profile configuration containing file patterns and excludes
        files: Optional list of specific files/paths provided by user
        global_exclude_patterns: Global exclude patterns from config
        verbose: Whether to enable verbose logging during file discovery
        provided_files: String representation of provided files for logging
        log_type: Type of log message to emit if no files found
    """

    profile: ProfileConfig
    files: list[Path] | None
    global_exclude_patterns: list[str]
    verbose: bool
    provided_files: list[str] | None = None
    log_type: str = 'no_files'


@dataclass
class ToolBranchContext:
    """Context for tool execution within a specific profile branch.

    This groups all parameters needed to execute a single tool, encapsulating
    the decision logic about file handling modes and target resolution.

    The "branch" refers to the execution path taken based on:
    - Tool's file_handling_mode ('batch' vs 'per_file')
    - Whether tool outputs to file
    - Whether specific files were provided vs discovery mode

    Args:
        tool: The specific tool configuration to execute
        profile: The profile containing file patterns and settings
        use_file_mode: True if specific files were provided, False for discovery
        target_files: Resolved list of files to process (None for discovery mode)
        global_exclude_patterns: Global exclude patterns from config
        verbose: Whether to enable verbose logging during execution
    """

    tool: ToolConfig
    profile: ProfileConfig
    use_file_mode: bool
    target_files: list[Path] | None
    global_exclude_patterns: list[str]
    verbose: bool


logger = get_logger(__name__)


def _get_target_files_or_log(ctx: TargetFilesContext) -> list[Path] | None:
    """Get target files for per_file mode tools, with logging if none found.

    This is used when specific files are provided but we need to filter them
    to only existing files that match the profile's patterns.

    Args:
        ctx: Context containing profile, files, and logging parameters

    Returns:
        List of valid target files, or None if no files found
    """
    target_files = get_target_files(
        ctx.profile,
        ctx.files,
        ctx.global_exclude_patterns,
        verbose=ctx.verbose,
    )
    if not target_files:
        logger.warning(
            ctx.log_type,
            profile=ctx.profile,
            provided_files=ctx.provided_files,
        )
        return None
    return target_files


def _run_tool_branch(
    ctx: ToolBranchContext,
    variables: dict[str, str] | None = None,
) -> int:
    """Run a tool using the appropriate execution mode based on tool configuration.

    This implements the decision tree for tool execution:

    1. If tool.output_to_file: Use file output mode (processes files individually)
    2. If tool.file_handling_mode == 'per_file': Find files, pass all to tool at once
    3. If tool.file_handling_mode == 'batch': Let tool discover files itself

    The "branch" refers to which execution path is taken based on tool configuration.

    Args:
        ctx: Context containing tool, profile, and target information
        variables: Optional environment variables for template substitution

    Returns:
        Exit code from tool execution (0 for success)
    """
    tool = ctx.tool

    # Decision 1: Check if tool outputs to file (requires special handling)
    if tool.output_to_file:
        return _run_tool_with_file_output_mode(ctx, variables)

    # Decision 2: Check file handling mode
    if tool.file_handling_mode == 'per_file':
        return _run_tool_per_file_mode(ctx, variables)

    if tool.file_handling_mode == 'batch':
        return _run_tool_batch_mode(ctx, variables)

    logger.error(
        'invalid_file_handling_mode',
        tool=tool.name,
        file_handling_mode=tool.file_handling_mode,
        supported_modes=['batch', 'per_file'],
    )
    return 1


def _run_tool_with_file_output_mode(
    ctx: ToolBranchContext,
    variables: dict[str, str] | None = None,
) -> int:
    """Handle tool execution for tools that output to file."""
    files_to_process = _get_files_for_tool_execution(ctx)
    if not files_to_process:
        logger.warning(
            'no_files_found',
            tool=ctx.tool.name,
            profile=ctx.profile,
            advisory='No files found to process.',
        )
        return 0

    return run_tool_with_file_output(ctx.tool, files_to_process, variables)


def _run_tool_per_file_mode(
    ctx: ToolBranchContext,
    variables: dict[str, str] | None = None,
) -> int:
    """Handle tool execution for per-file mode tools."""
    files_to_process = _get_files_for_tool_execution(ctx)
    if not files_to_process:
        logger.warning(
            'no_files_found',
            tool=ctx.tool.name,
            profile=ctx.profile,
            advisory='No files found to process.',
        )
        return 0

    return run_tool_per_file_mode(
        ctx.tool,
        files=files_to_process,
        variables=variables,
    )


def _run_tool_batch_mode(
    ctx: ToolBranchContext,
    variables: dict[str, str] | None = None,
) -> int:
    """Handle tool execution for batch mode tools."""
    if ctx.use_file_mode and ctx.target_files:
        targets = [str(f) for f in ctx.target_files]
    else:
        # Use default_target if specified, otherwise let tool auto-discover
        targets = [ctx.tool.default_target] if ctx.tool.default_target else []

    return run_tool_in_discovery_mode(
        ctx.tool,
        targets=targets,
        variables=variables,
    )


def _get_files_for_tool_execution(ctx: ToolBranchContext) -> list[Path]:
    """Get the appropriate files for tool execution based on context."""
    if ctx.use_file_mode and ctx.target_files:
        return get_target_files(
            ctx.profile,
            ctx.target_files,
            ctx.global_exclude_patterns,
            verbose=ctx.verbose,
        )
    return get_target_files(
        ctx.profile,
        None,
        ctx.global_exclude_patterns,
        verbose=ctx.verbose,
    )


def _run_tools_for_profile(
    config: ToolbeltConfig,
    profile_name: str,
    *,
    files: list[Path] | None,
    verbose: bool,
    tool_type: str,
) -> int:
    """Generic runner for check/format tools with complex file handling logic.

    This function implements the core orchestration logic with these steps:

    1. **Profile Setup**: Load profile and its tools
    2. **File Mode Detection**: Determine if specific files provided vs discovery mode
    3. **Target Resolution**: Handle different scenarios based on tool types:
       - Batch tools: Pass provided files/paths directly (let tool handle discovery)
       - Per-file tools: Filter provided files to existing, valid files
       - Discovery mode: Let each tool discover files independently
    4. **Tool Execution**: Run each tool with appropriate context

    Key Logic:
    - `use_file_mode = True` when specific files are provided
    - For batch tools: Pass files as-is (even non-existent paths)
    - For per_file tools: Filter to existing files matching profile patterns
    - Mixed tool types: Handle each appropriately

    Args:
        config: Toolbelt configuration with profiles and global settings
        profile_name: Name of profile to run
        files: Optional specific files/paths to process
        verbose: Enable detailed logging
        tool_type: 'check' or 'format' - determines which tools to run

    Returns:
        Exit code: 0 for success, non-zero for any tool failure
    """
    profile = config.get_profile(profile_name)
    if not profile:
        logger.error('invalid_profile', profile=profile)
        return 1

    tools = getattr(profile, f'{tool_type}_tools', None)
    if not tools:
        warn_msg = f'no_{tool_type}ers'
        logger.warning(warn_msg, profile=profile)
        return 0

    use_file_mode = files is not None and len(files) > 0
    target_files = _determine_target_files(
        TargetDeterminationContext(
            files=files,
            profile=profile,
            config=config,
            verbose=verbose,
            tool_type=tool_type,
            tools=tools,
        ),
    )

    if use_file_mode and target_files is None:
        # This means we had per-file tools but no valid files found
        return 0

    return _execute_tools(
        ToolExecutionContext(
            tools=tools,
            profile=profile,
            config=config,
            use_file_mode=use_file_mode,
            target_files=target_files,
            verbose=verbose,
        ),
    )


def _determine_target_files(
    ctx: TargetDeterminationContext,
) -> list[Path] | None:
    """Determine the target files based on tool types and provided files."""
    if ctx.files is None or len(ctx.files) == 0:
        # Discovery mode: No specific files provided
        logger.debug('discovering', profile_name=ctx.profile.name)
        return None

    # COMPLEX LOGIC: Handle mixed tool types when specific files are provided
    # Batch tools: Can handle non-existent paths, pass paths directly
    # Per-file tools: Need actual files, filter to existing files
    has_batch_tools = any(tool.file_handling_mode == 'batch' for tool in ctx.tools)

    if has_batch_tools:
        # Pass provided files/paths directly - let the tool handle them
        logger.debug(
            'checking' if ctx.tool_type == 'check' else 'formatting',
            profile_name=ctx.profile.name,
            provided_paths=[str(f) for f in ctx.files],
        )
        return ctx.files
    # Per-file mode - filter to existing files
    tf_ctx = TargetFilesContext(
        profile=ctx.profile,
        files=ctx.files,
        global_exclude_patterns=ctx.config.global_exclude_patterns,
        verbose=ctx.verbose,
        provided_files=[str(f) for f in ctx.files],
        log_type='no_files',
    )
    target_files = _get_target_files_or_log(tf_ctx)
    if not target_files:
        return None
    logger.debug(
        'checking' if ctx.tool_type == 'check' else 'formatting',
        profile=ctx.profile.name,
        file_count=len(target_files),
    )
    return target_files


def _execute_tools(ctx: ToolExecutionContext) -> int:
    """Execute all tools and return the final exit code."""
    exit_code = 0
    for tool in ctx.tools:
        branch_ctx = ToolBranchContext(
            tool=tool,
            profile=ctx.profile,
            use_file_mode=ctx.use_file_mode,
            target_files=ctx.target_files,
            global_exclude_patterns=ctx.config.global_exclude_patterns,
            verbose=ctx.verbose,
        )
        result = _run_tool_branch(branch_ctx, ctx.config.variables)
        if result != 0:
            exit_code = result
    return exit_code


def run_check(
    config: ToolbeltConfig,
    profile: str,
    *,
    files: list[Path] | None = None,
    verbose: bool = False,
) -> int:
    """Run check tools for the specified profile.

    Args:
        config: The ToolbeltConfig instance containing profiles and tools.
        profile: The profile name to run.
        files: Optional list of files to check. If None, uses profile extensions.
        verbose: Whether to log detailed output.

    Returns:
        Exit code indicating success (0) or failure (non-zero).
    """
    return _run_tools_for_profile(
        config,
        profile,
        files=files,
        verbose=verbose,
        tool_type='check',
    )


def run_format(
    config: ToolbeltConfig,
    profile: str,
    *,
    files: list[Path] | None = None,
    verbose: bool = False,
) -> int:
    """Run format tools for the specified profile.

    Args:
        config: The ToolbeltConfig instance containing profiles and tools.
        profile: The profile name to run.
        files: Optional list of files to format. If None, uses profile extensions.
        verbose: Whether to log detailed output.

    Returns:
        Exit code indicating success (0) or failure (non-zero).
    """
    return _run_tools_for_profile(
        config,
        profile,
        files=files,
        verbose=verbose,
        tool_type='format',
    )
