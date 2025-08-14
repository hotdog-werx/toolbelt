import logging

import structlog
import yaml
from rich.console import Console
from rich.syntax import Syntax
from structlog.types import FilteringBoundLogger
from structlog.typing import EventDict

console = Console()

# Type alias for our logger
Logger = FilteringBoundLogger


def format_context_yaml(event_dict: EventDict, indent: int = 2) -> str:
    """Format the context dictionary as YAML.

    Args:
        event_dict: The context dictionary to format.
        indent: The number of spaces to use for indentation.

    Returns:
        The formatted YAML string.
    """
    if not event_dict:
        return ''
    context_yaml = yaml.safe_dump(
        event_dict,
        sort_keys=True,
        default_flow_style=False,
    )
    pad = ' ' * indent
    return '\n'.join(f'{pad}{line}' for line in context_yaml.splitlines())


def pre_process_log(event_msg: str, event_dict: EventDict) -> tuple[str, str]:
    """Custom log formatting for command execution events.

    Args:
        event_msg: The main event message.
        event_dict: The event dictionary containing additional context.

    Returns:
        The the command to execute and the tool name if available.
    """
    for key in ('timestamp', 'level', 'log_level', 'event'):
        event_dict.pop(key, None)
    if event_msg == 'executing' and 'command' in event_dict:
        return event_dict.pop('command'), event_dict.pop('tool', '')
    return event_msg, ''


def cli_renderer(
    _logger: Logger,
    method_name: str,
    event_dict: EventDict,
) -> str:
    """Render log messages for CLI output using rich formatting.

    Args:
        logger: The logger instance.
        method_name: The logging method name (e.g., 'info', 'error').
        event_dict: The event dictionary containing log data.

    Returns:
        str: An empty string, as structlog expects a string return but output is printed.
    """
    level = method_name.upper()
    event_msg = event_dict.pop('event', '')
    event_msg, tool_name = pre_process_log(event_msg, event_dict)
    context_yaml = format_context_yaml(event_dict)

    # Map log levels to colors/styles
    level_styles = {
        'INFO': 'blue',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'DEBUG': 'magenta',
        'CRITICAL': 'white on red',
        'SUCCESS': 'green',  # for custom use
    }
    # Pick style, fallback to bold cyan for unknown
    style = level_styles.get(level, 'bold cyan')

    if level == 'INFO' and tool_name:
        log_msg = f'[bold #888888]tb\\[{tool_name}] =>[/bold #888888] [blue]{event_msg}[/blue]'
    else:
        log_msg = f'[bold {style}][{level}][/bold {style}] [{style}]{event_msg}[/{style}]'

    console.print(log_msg)
    if context_yaml:
        syntax = Syntax(
            context_yaml,
            'yaml',
            theme='github-dark',
            background_color='default',
            line_numbers=False,
        )
        console.print(syntax)
    return ''  # structlog expects a string return, but we already printed


def configure_logging(*, verbose: bool = False) -> None:
    """Configure structlog for toolbelt.

    Args:
        verbose: Enable verbose/debug output
    """
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.processors.TimeStamper(fmt='ISO', utc=False),
            structlog.stdlib.add_log_level,
            cli_renderer,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )

    if verbose:
        logging.basicConfig(level=logging.DEBUG, handlers=[])
    else:
        logging.basicConfig(level=logging.INFO, handlers=[])


def get_logger(name: str) -> Logger:
    """Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)
