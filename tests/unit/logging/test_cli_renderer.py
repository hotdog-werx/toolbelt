"""Tests for cli_renderer function in toolbelt.logging."""

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from rich.syntax import Syntax

from toolbelt import logging as logging_mod
from toolbelt.logging import Logger, cli_renderer


@pytest.fixture(autouse=True)
def patch_console(mocker: MockerFixture) -> dict[str, Any]:
    """Patch the global Console.print used in cli_renderer to capture output using mocker."""
    printed: list[Any] = []
    mocker.patch.object(
        logging_mod.console,
        'print',
        side_effect=lambda *args, **kwargs: printed.append((args, kwargs)),
    )
    return {'printed': printed}


@dataclass
class RendererCase:
    method_name: str
    event_dict: dict
    expected_fragments: list[str]
    expected_style: str
    desc: str


@pytest.mark.parametrize(
    'tcase',
    [
        RendererCase(
            method_name='info',
            event_dict={
                'event': 'executing',
                'tool': 'mytool',
                'command': 'mytool --args',
            },
            expected_fragments=['tb\\[mytool] =>', 'mytool --args'],
            expected_style='blue',
            desc='info_command',
        ),
        RendererCase(
            method_name='info',
            event_dict={'event': 'hello', 'p1': 'v1', 'p2': 'v2'},
            expected_fragments=['[INFO]', 'hello'],
            expected_style='blue',
            desc='info',
        ),
        RendererCase(
            method_name='warning',
            event_dict={'event': 'warn!'},
            expected_fragments=['[WARNING]', 'warn!'],
            expected_style='yellow',
            desc='warning_log',
        ),
        RendererCase(
            method_name='error',
            event_dict={'event': 'fail!'},
            expected_fragments=['[ERROR]', 'fail!'],
            expected_style='red',
            desc='error_log',
        ),
        RendererCase(
            method_name='debug',
            event_dict={'event': 'debugging'},
            expected_fragments=['[DEBUG]', 'debugging'],
            expected_style='magenta',
            desc='debug_log',
        ),
        RendererCase(
            method_name='critical',
            event_dict={'event': 'oh no'},
            expected_fragments=['[CRITICAL]', 'oh no'],
            expected_style='white on red',
            desc='critical',
        ),
        RendererCase(
            method_name='success',
            event_dict={'event': 'yay'},
            expected_fragments=['[SUCCESS]', 'yay'],
            expected_style='green',
            desc='success',
        ),
    ],
    ids=lambda c: c.desc,
)
def test_cli_renderer_basic_styles(
    patch_console: dict[str, Any],
    tcase: RendererCase,
) -> None:
    """Test that cli_renderer prints correct style and fragments for each log level."""
    logger = MagicMock(spec=Logger)
    result = cli_renderer(logger, tcase.method_name, tcase.event_dict)
    assert result == ''
    assert patch_console['printed'], 'No output was printed.'
    found = False
    for args, _ in patch_console['printed']:
        text = ' '.join(str(a) for a in args)
        if all(frag in text for frag in tcase.expected_fragments) and tcase.expected_style in text:
            found = True
            break
    frag = ' '.join(tcase.expected_fragments)
    style = tcase.expected_style
    patched = patch_console['printed']
    assert found, f"Expected fragments '{frag}' with style '{style}' in output: {patched}"


def test_cli_renderer_context_yaml(patch_console: dict[str, Any]) -> None:
    """Test that cli_renderer prints YAML context when present."""
    logger = MagicMock(spec=Logger)
    event_dict = {'event': 'info', 'foo': 'bar', 'baz': 123}
    cli_renderer(logger, 'info', dict(event_dict))
    # Should print the main log line and a Syntax (YAML) block
    assert len(patch_console['printed']) >= 2
    # The second print should be a Syntax object

    found_yaml = any(isinstance(args[0], Syntax) for args, _ in patch_console['printed'] if args)
    assert found_yaml, f'Expected a Syntax (YAML) block in output: {patch_console["printed"]}'


def test_cli_renderer_executing_special_case(
    patch_console: dict[str, Any],
) -> None:
    """Test that cli_renderer handles the 'executing' event specially."""
    logger = MagicMock(spec=Logger)
    event_dict = {'event': 'executing', 'command': 'ls -l', 'tool': 'ls'}
    cli_renderer(logger, 'info', dict(event_dict))
    # Should print tb[ls] => and not include 'executing' in the output
    found = any('tb\\[ls] =>' in ' '.join(str(a) for a in args) for args, _ in patch_console['printed'])
    assert found, f"Expected 'tb\\[ls] =>' in output: {patch_console['printed']}"
    # Should not print 'executing' as the event message
    not_found = all('executing' not in ' '.join(str(a) for a in args) for args, _ in patch_console['printed'])
    assert not_found, f"'executing' should not appear in output: {patch_console['printed']}"
