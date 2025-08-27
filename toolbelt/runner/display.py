from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from toolbelt.config import ProfileConfig, ToolbeltConfig

console = Console()


# --- Helper functions for display ---
def _make_profile_header(name: str) -> Text:
    return Text.assemble(('Profile: ', 'bold yellow'), (name, 'bold white'))


def _make_extensions_text(lang_config: ProfileConfig) -> Text:
    return Text(
        f'Extensions: {", ".join(lang_config.extensions)}',
        style='cyan',
    )


def _make_tools_table(lang_config: ProfileConfig) -> Table:
    table = Table(show_header=True, header_style='bold magenta', box=None)
    table.add_column('Type', style='dim', width=10)
    table.add_column('Tool', style='bold green')
    table.add_column('Description', style='white')

    added = False
    if lang_config.check_tools:
        for tool in lang_config.check_tools:
            table.add_row('Check', tool.name, tool.description)
            added = True
    if lang_config.format_tools:
        for tool in lang_config.format_tools:
            table.add_row('Format', tool.name, tool.description)
            added = True
    if not added:
        table.add_row('-', 'No tools configured', '')
    return table


def _make_exclude_text(lang_config: ProfileConfig) -> Text | None:
    if lang_config.exclude_patterns:
        return Text(
            f'Exclude patterns: {", ".join(lang_config.exclude_patterns)}',
            style='red',
        )
    return None


def print_profile_tools(name: str, lang_config: ProfileConfig) -> None:
    """Print information about a profile and its tools."""
    header = _make_profile_header(name)
    extensions = _make_extensions_text(lang_config)
    table = _make_tools_table(lang_config)
    exclude = _make_exclude_text(lang_config)

    panel_items = [extensions, table]
    if exclude:
        panel_items.append(exclude)
    group = Group(*panel_items)
    panel = Panel.fit(
        group,
        title=header,
        border_style='bright_blue',
    )
    console.print(panel)


def _error(msg: str) -> int:
    console.print(msg, style='red')
    return 1


def list_tools(config: ToolbeltConfig, profile: str | None = None) -> int:
    """List available profiles and their tools.

    Args:
        config: Loaded ToolbeltConfig
        profile: Optional profile name to display; if None, list all profiles

    Returns:
        Exit code (0 for success, 1 for error)
    """
    if profile:
        lang_config = config.get_profile(profile)
        if not lang_config:
            return _error(
                f"[bold red]Error:[/bold red] Profile '[yellow]{profile}[/yellow]' not configured",
            )
        print_profile_tools(profile, lang_config)
        return 0

    profiles = config.list_profiles()
    if not profiles:
        console.print(
            '[bold red]No profiles configured[/bold red]',
            style='red',
        )
        return 0

    console.print('[bold bright_blue]Configured profiles:[/bold bright_blue]\n')
    for lang_name in sorted(profiles):
        lang_config = config.get_profile(lang_name)
        if lang_config:
            print_profile_tools(lang_name, lang_config)
            console.print()  # Empty line between profiles
    return 0
