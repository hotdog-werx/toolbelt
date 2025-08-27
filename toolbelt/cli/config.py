import argparse

from rich.console import Console
from rich.table import Table

from toolbelt.config.models import ToolbeltConfig, ToolConfig, get_tool_command

from ._utils import get_profile_names_completer, print_config_sources_list

console = Console()


def add_config_subparser(
    subparsers: argparse._SubParsersAction,
) -> argparse.ArgumentParser:
    """Add the 'config' subparser to show configuration details.

    Args:
        subparsers: The subparsers action from the main parser.

    Returns:
        The created ArgumentParser for the 'config' command.
    """
    config_parser = subparsers.add_parser(
        'config',
        help='Show configuration details including sources and raw commands',
    )

    config_parser.add_argument(
        'profile',
        nargs='?',
        help='Show detailed configuration for a specific profile',
    ).completer = get_profile_names_completer
    config_parser.add_argument(
        '--show-variables',
        action='store_true',
        help='Show all available template variables',
    )
    return config_parser


def _show_variables(config: ToolbeltConfig) -> None:
    """Display all template variables."""
    variables = config.get_variables()
    if variables:
        console.print(
            '[bold bright_blue]Template Variables:[/bold bright_blue]',
        )

        table = Table(show_header=True, header_style='bold magenta', box=None)
        table.add_column('Variable', style='bold green', width=30)
        table.add_column('Value', style='white')

        for key, value in sorted(variables.items()):
            table.add_row(key, value)

        console.print(table)
    else:
        console.print(
            '[bold yellow]No template variables defined.[/bold yellow]',
        )
    console.print()


def _show_tool_commands(profile_name: str, config: ToolbeltConfig) -> None:
    """Show raw and expanded commands for all tools in a profile."""
    profile = config.get_profile(profile_name)
    if not profile:
        console.print(
            f'[bold red]Profile "{profile_name}" not found.[/bold red]',
        )
        return

    variables = config.get_variables()

    console.print(
        f'[bold bright_blue]Profile: {profile_name}[/bold bright_blue]',
    )
    console.print(f'[cyan]Extensions: {", ".join(profile.extensions)}[/cyan]')
    console.print()

    # Show check tools
    if profile.check_tools:
        console.print('[bold magenta]Check Tools:[/bold magenta]')
        for tool in profile.check_tools:
            _show_single_tool_commands(tool, variables)
        console.print()

    # Show format tools
    if profile.format_tools:
        console.print('[bold magenta]Format Tools:[/bold magenta]')
        for tool in profile.format_tools:
            _show_single_tool_commands(tool, variables)
        console.print()


def _show_single_tool_commands(
    tool: ToolConfig,
    variables: dict[str, str],
) -> None:
    """Show commands for a single tool."""
    # Get the command info
    cmd_info = get_tool_command(tool, variables=variables)

    # Create a table for this tool
    table = Table(show_header=True, header_style='bold cyan', box=None)
    table.add_column('Property', style='dim', width=20)
    table.add_column('Value', style='white')

    table.add_row('Tool Name', f'[bold green]{tool.name}[/bold green]')
    if tool.description:
        table.add_row('Description', tool.description)

    # Show raw (unexpanded) command
    raw_cmd = ' '.join(cmd_info.unexpanded_base_command or [])
    table.add_row('Raw Command', f'[yellow]{raw_cmd}[/yellow]')

    # Show expanded command
    expanded_cmd = ' '.join(cmd_info.base_command)
    table.add_row(
        'Expanded Command',
        f'[bright_green]{expanded_cmd}[/bright_green]',
    )

    table.add_row('File Mode', tool.file_handling_mode)

    if tool.default_target:
        table.add_row('Default Target', f'[blue]{tool.default_target}[/blue]')

    if tool.working_dir:
        table.add_row('Working Dir', f'[blue]{tool.working_dir}[/blue]')

    if tool.output_to_file:
        table.add_row('Output to File', '[green]Yes[/green]')

    console.print(table)
    console.print()


def _show_all_profiles_summary(config: ToolbeltConfig) -> None:
    """Show a summary of all profiles."""
    profiles = config.list_profiles()
    if not profiles:
        console.print('[bold red]No profiles configured.[/bold red]')
        return

    console.print('[bold bright_blue]Profile Summary:[/bold bright_blue]')

    table = Table(show_header=True, header_style='bold magenta', box=None)
    table.add_column('Profile', style='bold green', width=15)
    table.add_column('Extensions', style='cyan', width=20)
    table.add_column('Check Tools', style='white', width=15)
    table.add_column('Format Tools', style='white', width=15)
    table.add_column('Total Tools', style='bright_green', width=12)

    for profile_name in sorted(profiles):
        profile = config.get_profile(profile_name)
        if profile:
            extensions = ', '.join(profile.extensions)
            check_count = len(profile.check_tools)
            format_count = len(profile.format_tools)
            total_tools = check_count + format_count

            table.add_row(
                profile_name,
                extensions,
                str(check_count),
                str(format_count),
                str(total_tools),
            )

    console.print(table)
    console.print()


def handle_config_command(
    config: ToolbeltConfig,
    args: argparse.Namespace,
) -> int:
    """Handle the 'config' command.

    Args:
        config: The loaded configuration object.
        args: Parsed CLI arguments.

    Returns:
        Exit code from the config command.
    """
    # Show configuration sources
    print_config_sources_list(
        config.sources,
        'Configuration Sources (in load order)',
    )

    # Show variables if requested
    if args.show_variables:
        _show_variables(config)

    # Show specific profile details or summary
    if args.profile:
        _show_tool_commands(args.profile, config)
    else:
        _show_all_profiles_summary(config)

        # Show variables at the end if not already shown
        if not args.show_variables:
            console.print(
                '[dim]Use --show-variables to see all template variables[/dim]',
            )
            console.print(
                '[dim]Use "toolbelt config <profile>" to see detailed tool commands for a specific profile[/dim]',
            )

    return 0
