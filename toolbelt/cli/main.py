import argparse
import sys
import traceback
from pathlib import Path

import argcomplete

from toolbelt import __version__
from toolbelt.config.loader import load_config
from toolbelt.logging import configure_logging, get_logger

from ._utils import show_config_sources as show_config_sources_util
from .check import add_check_subparser, handle_check_command
from .config import add_config_subparser, handle_config_command
from .format import add_format_subparser, handle_format_command
from .list import add_list_subparser, handle_list_command


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser for toolbelt CLI."""
    parser = argparse.ArgumentParser(
        prog='toolbelt',
        description='A configurable tool runner for code checks and formatting',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    arg = parser.add_argument
    arg('--version', action='version', version=__version__)
    arg(
        '--config',
        '-c',
        type=Path,
        help='Path to configuration file (toolbelt.yaml or toolbelt.py)',
    )
    arg('--verbose', '-v', action='store_true', help='Enable verbose output')
    arg(
        '--sources',
        action='store_true',
        help='Show configuration sources being loaded',
    )
    subparsers = parser.add_subparsers(
        dest='command',
        help='Available commands',
        required=True,
    )

    add_check_subparser(subparsers)
    add_config_subparser(subparsers)
    add_format_subparser(subparsers)
    add_list_subparser(subparsers)

    return parser


def show_config_sources(config_path: Path | None) -> list[Path]:
    """Display configuration sources being loaded."""
    return show_config_sources_util(
        config_path,
        'Configuration sources (in load order)',
    )


def _load_sources(args: argparse.Namespace) -> list[Path] | None:
    sources: list[Path] | None = []
    if args.sources:
        sources = show_config_sources(args.config)
    if not sources:
        sources = [args.config] if args.config else None
    return sources


def main() -> int:
    """Main entry point for the toolbelt CLI."""
    logger = get_logger(__name__)

    parser = create_parser()

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    # Configure logging first
    configure_logging(verbose=args.verbose)

    try:
        sources = _load_sources(args)
        config = load_config(sources)
        logger.debug('config_loaded', profiles=list(config.profiles.keys()))

        command_handlers = {
            'check': handle_check_command,
            'config': handle_config_command,
            'format': handle_format_command,
            'list': handle_list_command,
        }
        # argparse will ensure args.command is one of the keys
        return command_handlers[args.command](config, args)
    except Exception as e:
        logger.exception(
            'exception',
            error=str(e),
            error_type=type(e).__name__,
            traceback=traceback.format_exc(),
        )
        return 1


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
