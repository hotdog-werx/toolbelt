import argparse
from pathlib import Path
from toolbelt.runner.orchestrator import run_format
from toolbelt.config.models import ToolbeltConfig

def add_format_subparser(
    subparsers: argparse._SubParsersAction,
) -> argparse.ArgumentParser:
    """Add the 'format' subparser for formatting files.

    Args:
        subparsers: The subparsers action from the main parser.

    Returns:
        The created ArgumentParser for the 'format' command.
    """
    format_parser = subparsers.add_parser('format', help='Format files')
    format_parser.add_argument(
        'profile',
        help='Profile to format (e.g., python, javascript, typescript)',
    )
    format_parser.add_argument(
        'files',
        nargs='*',
        type=Path,
        help='Specific files to format (if not provided, formats all files for the profile)',
    )
    return format_parser

def handle_format_command(
    config: ToolbeltConfig,
    args: argparse.Namespace,
) -> int:
    """Handle the 'format' command.

    Args:
        config: The loaded configuration object.
        args: Parsed CLI arguments.

    Returns:
        Exit code from the format command.
    """
    return run_format(
        config,
        args.profile,
        files=args.files,
        verbose=args.verbose,
    )