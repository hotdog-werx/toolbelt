from dataclasses import dataclass
from pathlib import Path

import pytest

from toolbelt.config.models import ToolConfig
from toolbelt.runner.tool_execution import _build_log_context


@dataclass
class LogContextCase:
    tool: ToolConfig
    command_parts: list
    cwd: str | None
    expected: dict
    description: str


@pytest.mark.parametrize(
    'tcase',
    [
        LogContextCase(
            tool=ToolConfig(
                name='test-tool',
                command='echo',
                args=[],
                description='Test tool',
            ),
            command_parts=['echo', 'hello', 'world'],
            cwd=None,
            expected={'tool': 'test-tool', 'command': 'echo hello world'},
            description='basic',
        ),
        LogContextCase(
            tool=ToolConfig(
                name='test-tool',
                command='echo',
                args=[],
                description='Test tool',
                working_dir='/some/other/path',
            ),
            command_parts=['echo', 'test'],
            cwd='/current/path',
            expected={
                'tool': 'test-tool',
                'command': 'echo test',
                'working_dir': '/some/other/path',
            },
            description='with_working_dir',
        ),
        LogContextCase(
            tool=ToolConfig(
                name='test-tool',
                command='echo',
                args=[],
                description='Test tool',
                working_dir='/current/path',
            ),
            command_parts=['echo', 'test'],
            cwd='/current/path',
            expected={'tool': 'test-tool', 'command': 'echo test'},
            description='working_dir_same_as_cwd',
        ),
        LogContextCase(
            tool=ToolConfig(
                name='test-tool',
                command='echo',
                args=[],
                description='Test tool',
            ),
            command_parts=['echo', 'test'],
            cwd=None,
            expected={'tool': 'test-tool', 'command': 'echo test'},
            description='no_working_dir',
        ),
        LogContextCase(
            tool=ToolConfig(
                name='test-tool',
                command='echo',
                args=[],
                description='Test tool',
            ),
            command_parts=[],
            cwd=None,
            expected={'tool': 'test-tool', 'command': ''},
            description='empty_command',
        ),
    ],
    ids=lambda c: c.description,
)
def test_build_log_context_parametrized(mocker, tcase: LogContextCase):
    """Parametrized test for _build_log_context helper function.
    Covers: {tcase.description}
    """
    if tcase.cwd is not None:
        mocker.patch(
            'toolbelt.runner.tool_execution.Path.cwd',
            return_value=Path(tcase.cwd),
        )
    result = _build_log_context(tcase.tool, tcase.command_parts)
    assert result == tcase.expected, f'Failed: {tcase.description}\nExpected: {tcase.expected}\nGot: {result}'
