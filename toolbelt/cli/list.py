import argparse

from toolbelt.config.models import ToolbeltConfig
from toolbelt.runner.display import list_tools


def add_list_subparser(
    subparsers: argparse._SubParsersAction,
) -> argparse.ArgumentParser:
    """Add the 'list' subparser to show available profiles and tools.

    Args:
        subparsers: The subparsers action from the main parser.

    Returns:
        The created ArgumentParser for the 'list' command.
    """
    list_parser = subparsers.add_parser(
        'list',
        help='List available profiles and their configured tools',
    )
    list_parser.add_argument(
        'profile',
        nargs='?',
        help='Show tools for a specific profile',
    )
    return list_parser


def handle_list_command(
    config: ToolbeltConfig,
    args: argparse.Namespace,
) -> int:
    """Handle the 'list' command.

    Args:
        config: The loaded configuration object.
        args: Parsed CLI arguments.

    Returns:
        Exit code from the list command.
    """
    return list_tools(config, args.profile)
