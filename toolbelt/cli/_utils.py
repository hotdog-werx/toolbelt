"""Shared utilities for CLI modules."""

from pathlib import Path

from rich.console import Console

from toolbelt.config.discovery import find_config_sources

console = Console()


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
    if sources:
        console.print(f'[bold bright_blue]{title}:[/bold bright_blue]')
        for i, source in enumerate(sources, 1):
            console.print(f'  [cyan]{i}.[/cyan] [white]{source}[/white]')
    else:
        console.print(
            '[bold yellow]No configuration sources found, using defaults.[/bold yellow]',
        )
    console.print()  # Empty line for spacing
    return sources
