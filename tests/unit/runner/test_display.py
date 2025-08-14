from dataclasses import dataclass

import pytest

from toolbelt.config import ProfileConfig, ToolbeltConfig, ToolConfig
from toolbelt.runner.display import list_tools, print_profile_tools


@dataclass
class DisplayCase:
    desc: str
    lang_name: str
    lang_config: ProfileConfig
    expected_strings: list[str]


@pytest.mark.parametrize(
    'tcase',
    [
        DisplayCase(
            desc='with_check_and_format',
            lang_name='python',
            lang_config=ProfileConfig(
                name='python',
                extensions=['.py'],
                check_tools=[
                    ToolConfig(
                        name='flake8',
                        command='flake8',
                        args=[],
                        description='Python linter',
                    ),
                ],
                format_tools=[
                    ToolConfig(
                        name='black',
                        command='black',
                        args=[],
                        description='Python formatter',
                    ),
                ],
                exclude_patterns=['__pycache__/**'],
                ignore_files=['.gitignore'],
            ),
            expected_strings=[
                'Profile:',
                'python',
                'Extensions:',
                '.py',
                'Check',
                'flake8',
                'Python linter',
                'Format',
                'black',
                'Python formatter',
                'Exclude patterns:',
                '__pycache__/**',
            ],
        ),
        DisplayCase(
            desc='no_tools',
            lang_name='empty',
            lang_config=ProfileConfig(
                name='empty',
                extensions=['.foo'],
                check_tools=[],
                format_tools=[],
                exclude_patterns=[],
                ignore_files=[],
            ),
            expected_strings=[
                'Profile:',
                'empty',
                'Extensions:',
                '.foo',
                'No tools configured',
            ],
        ),
        DisplayCase(
            desc='exclude_patterns_only',
            lang_name='exclude',
            lang_config=ProfileConfig(
                name='exclude',
                extensions=['.bar'],
                check_tools=[],
                format_tools=[],
                exclude_patterns=['build/**', 'dist/**'],
                ignore_files=[],
            ),
            expected_strings=[
                'Profile:',
                'exclude',
                'Extensions:',
                '.bar',
                'Exclude patterns:',
                'build/**',
                'dist/**',
            ],
        ),
    ],
    ids=lambda c: c.desc,
)
def test_print_language_tools_param(
    capsys: pytest.CaptureFixture[str],
    tcase: DisplayCase,
) -> None:
    """Parametrized: Test printing language tools with various configurations."""
    print_profile_tools(tcase.lang_name, tcase.lang_config)
    captured = capsys.readouterr()
    for expected in tcase.expected_strings:
        assert expected in captured.out


@dataclass
class ListToolsCase:
    desc: str
    toolbelt_config: ToolbeltConfig
    profile: str | None
    expected_strings: list[str]
    expected_code: int


@pytest.mark.parametrize(
    'tcase',
    [
        ListToolsCase(
            desc='list_all_profiles',
            toolbelt_config=ToolbeltConfig(
                profiles={
                    'python': ProfileConfig(
                        name='python',
                        extensions=['.py'],
                        check_tools=[],
                        format_tools=[],
                        exclude_patterns=[],
                        ignore_files=[],
                    ),
                    'js': ProfileConfig(
                        name='js',
                        extensions=['.js'],
                        check_tools=[],
                        format_tools=[],
                        exclude_patterns=[],
                        ignore_files=[],
                    ),
                },
            ),
            profile=None,
            expected_strings=['Configured profiles:', 'python', 'js'],
            expected_code=0,
        ),
        ListToolsCase(
            desc='list_specific_profile',
            toolbelt_config=ToolbeltConfig(
                profiles={
                    'python': ProfileConfig(
                        name='python',
                        extensions=['.py'],
                        check_tools=[],
                        format_tools=[],
                        exclude_patterns=[],
                        ignore_files=[],
                    ),
                },
            ),
            profile='python',
            expected_strings=['Profile:', 'python', 'Extensions:', '.py'],
            expected_code=0,
        ),
        ListToolsCase(
            desc='language not configured',
            toolbelt_config=ToolbeltConfig(profiles={}),
            profile='ruby',
            expected_strings=['Error:', 'ruby', 'not configured'],
            expected_code=1,
        ),
        ListToolsCase(
            desc='no languages configured',
            toolbelt_config=ToolbeltConfig(profiles={}),
            profile=None,
            expected_strings=['No profiles configured'],
            expected_code=0,
        ),
    ],
    ids=lambda c: c.desc,
)
def test_list_tools_param(
    capsys: pytest.CaptureFixture[str],
    tcase: ListToolsCase,
) -> None:
    """Parametrized: Test listing tools with various configurations."""
    code = list_tools(tcase.toolbelt_config, tcase.profile)
    captured = capsys.readouterr()

    for expected in tcase.expected_strings:
        assert expected in captured.out

    assert code == tcase.expected_code
