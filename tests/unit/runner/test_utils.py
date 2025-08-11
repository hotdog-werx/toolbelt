import os
from dataclasses import dataclass
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from toolbelt.runner.utils import expand_globs_in_args


def normalize_paths(paths: list[Path]) -> list[str]:
    return [os.path.normpath(str(p)) for p in paths]


@dataclass
class GlobExpansionTestCase:
    """Test case for glob expansion."""

    desc: str
    args: list[str]
    expected: list[str]
    glob_matches: dict[str, list[str]]  # arg -> list of matches


@pytest.mark.parametrize(
    'tcase',
    [
        GlobExpansionTestCase(
            desc='no_globs',
            args=['command', '--flag', 'value', 'file.py'],
            expected=['command', '--flag', 'value', 'file.py'],
            glob_matches={},
        ),
        GlobExpansionTestCase(
            desc='with_matches',
            args=['command', '*.py', '--include', 'test_*.py', 'src/**/*.js'],
            expected=[
                'command',
                'file1.py',
                'file2.py',
                '--include',
                'test_file.py',
                'src/app.js',
                'src/utils.js',
            ],
            glob_matches={
                '*.py': ['file1.py', 'file2.py'],
                'test_*.py': ['test_file.py'],
                'src/**/*.js': ['src/app.js', 'src/utils.js'],
            },
        ),
        GlobExpansionTestCase(
            desc='no_matches',
            args=['command', '*.nonexistent', '--pattern', 'missing_*.py'],
            expected=['command', '*.nonexistent', '--pattern', 'missing_*.py'],
            glob_matches={
                '*.nonexistent': [],
                'missing_*.py': [],
            },
        ),
        GlobExpansionTestCase(
            desc='mixed_patterns',
            args=[
                'cmd',
                '*.py',
                '--flag',
                '*.missing',
                'regular_file.txt',
                'test_[abc].py',
            ],
            expected=[
                'cmd',
                'main.py',
                '--flag',
                '*.missing',
                'regular_file.txt',
                'test_a.py',
                'test_b.py',
            ],
            glob_matches={
                '*.py': ['main.py'],
                '*.missing': [],
                'test_[abc].py': ['test_a.py', 'test_b.py'],
            },
        ),
        GlobExpansionTestCase(
            desc='preserves_order',
            args=['cmd', '*.py', '--sep', '*.js', 'end'],
            expected=['cmd', 'z.py', 'a.py', '--sep', 'b.js', 'y.js', 'end'],
            glob_matches={
                '*.py': ['z.py', 'a.py'],
                '*.js': ['b.js', 'y.js'],
            },
        ),
        GlobExpansionTestCase(
            desc='literal_glob_chars',
            args=['echo', 'hello*world', 'test?', 'bracket[x]'],
            expected=['echo', 'hello*world', 'test?', 'bracket[x]'],
            glob_matches={
                'hello*world': [],
                'test?': [],
                'bracket[x]': [],
            },
        ),
        GlobExpansionTestCase(
            desc='single_asterisk',
            args=['*.txt'],
            expected=['file1.txt', 'file2.txt'],
            glob_matches={'*.txt': ['file1.txt', 'file2.txt']},
        ),
        GlobExpansionTestCase(
            desc='question_mark_pattern',
            args=['file?.py'],
            expected=['file1.py', 'file2.py'],
            glob_matches={'file?.py': ['file1.py', 'file2.py']},
        ),
        GlobExpansionTestCase(
            desc='bracket_pattern',
            args=['test_[ab].py'],
            expected=['test_a.py', 'test_b.py'],
            glob_matches={'test_[ab].py': ['test_a.py', 'test_b.py']},
        ),
        GlobExpansionTestCase(
            desc='recursive_pattern',
            args=['**/*.js'],
            expected=['src/app.js', 'lib/utils.js'],
            glob_matches={'**/*.js': ['src/app.js', 'lib/utils.js']},
        ),
        GlobExpansionTestCase(
            desc='no_glob_characters',
            args=['regular_file.py', '--flag', 'value'],
            expected=['regular_file.py', '--flag', 'value'],
            glob_matches={},
        ),
        GlobExpansionTestCase(
            desc='empty_args',
            args=[],
            expected=[],
            glob_matches={},
        ),
    ],
    ids=lambda c: c.desc,
)
def test_expand_globs_in_args_cases(
    tcase: GlobExpansionTestCase,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        Path,
        'glob',
        lambda _self, pattern: [Path(m) for m in tcase.glob_matches.get(pattern, [])],
    )
    result = expand_globs_in_args(tcase.args)
    # Compare normalized paths for platform independence
    assert normalize_paths(result) == normalize_paths(tcase.expected)
