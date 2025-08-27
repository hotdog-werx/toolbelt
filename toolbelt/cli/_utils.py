"""Shared utilities for CLI modules."""

from pathlib import Path
from typing import Any

from rich.console import Console

from toolbelt.config.discovery import find_config_sources
from toolbelt.config.loader import load_config

console = Console()


def print_config_sources_list(
    sources: list[str],
    title: str = 'Configuration Sources',
) -> None:
    """Print a list of config sources with a title."""
    if sources:
        console.print(f'[bold bright_blue]{title}:[/bold bright_blue]')
        for i, source in enumerate(sources, 1):
            console.print(f'  [cyan]{i}.[/cyan] [white]{source}[/white]')
    else:
        console.print(
            '[bold yellow]No configuration sources found, using defaults.[/bold yellow]',
        )
    console.print()  # Empty line for spacing


def show_config_sources(
    config_path: Path | None,
    title: str = 'Configuration Sources',
) -> list[Path]:
    """Display configuration sources being loaded.

    Args:
        config_path: Path to config file or None for auto-discovery
        title: Title to display for the sources section

    Returns:
        List of source paths found
    """
    sources = find_config_sources(config_path)
    print_config_sources_list([str(s) for s in sources], title)
    return sources


def get_profile_names_completer(**kwargs: Any) -> list[str]:  # noqa: ARG001
    # kwargs is required by argcomplete interface, even if unused
    """Return available profile names for argcomplete completion."""
    try:
        config = load_config(None)
        return list(config.profiles.keys())
    except Exception:  # noqa: BLE001 - catch all to avoid breaking completion
        return []
