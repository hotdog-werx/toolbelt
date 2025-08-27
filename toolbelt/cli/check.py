import argparse
from pathlib import Path

from toolbelt.cli._utils import get_profile_names_completer
from toolbelt.config.models import ToolbeltConfig
from toolbelt.runner.orchestrator import run_check


def add_check_subparser(
    subparsers: argparse._SubParsersAction,
) -> argparse.ArgumentParser:
    """Add the 'check' subparser for running checks on files.

    Args:
        subparsers: The subparsers action from the main parser.

    Returns:
        The created ArgumentParser for the 'check' command.
    """
    check_parser = subparsers.add_parser('check', help='Run checks on files')
    check_profile_arg = check_parser.add_argument(
        'profile',
        help='Profile to check (e.g., python, javascript, coverage, test)',
    )
    check_profile_arg.completer = get_profile_names_completer
    check_parser.add_argument(
        'files',
        nargs='*',
        type=Path,
        help='Specific files to check (if not provided, checks all files for the profile)',
    )
    return check_parser


def handle_check_command(
    config: ToolbeltConfig,
    args: argparse.Namespace,
) -> int:
    """Handle the 'check' command.

    Args:
        config: The loaded configuration object.
        args: Parsed CLI arguments.

    Returns:
        Exit code from the check command.
    """
    return run_check(
        config,
        args.profile,
        files=args.files,
        verbose=args.verbose,
    )
