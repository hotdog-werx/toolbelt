from dataclasses import dataclass
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from toolbelt import ignore as ignore_mod
from toolbelt.ignore import (
    IgnoreManager,
    create_ignore_manager,
    filter_files,
    filter_ignored_files,
    load_ignore_patterns,
    should_ignore,
    should_ignore_file,
)


@dataclass
class IgnoreTestCase:
    desc: str
    ignore_content: str
    file_to_check: str
    expected_ignored: bool


@pytest.mark.parametrize(
    'tcase',
    [
        IgnoreTestCase(
            desc='pyc_file',
            ignore_content='*.pyc\n',
            file_to_check='test.pyc',
            expected_ignored=True,
        ),
        IgnoreTestCase(
            desc='pycache_dir',
            ignore_content='__pycache__/\n',
            file_to_check='__pycache__/test.py',
            expected_ignored=True,
        ),
        IgnoreTestCase(
            desc='nested_pycache',
            ignore_content='__pycache__/\n',
            file_to_check='src/__pycache__/test.py',
            expected_ignored=True,
        ),
        IgnoreTestCase(
            desc='allowed_file',
            ignore_content='*.pyc\n',
            file_to_check='test.py',
            expected_ignored=False,
        ),
        IgnoreTestCase(
            desc='empty_patterns',
            ignore_content='',
            file_to_check='test.py',
            expected_ignored=False,
        ),
    ],
    ids=lambda c: c.desc,
)
def test_should_ignore_file_patterns(tcase: IgnoreTestCase, temp_dir: Path) -> None:
    """Parametrized: Test should_ignore_file with various patterns."""
    root_dir = Path(temp_dir)
    ignore_file = root_dir / '.gitignore'
    ignore_file.write_text(tcase.ignore_content)

    spec = load_ignore_patterns(['.gitignore'], root_dir)
    file_path = Path(tcase.file_to_check)

    result = should_ignore_file(file_path, spec, root_dir)
    assert result == tcase.expected_ignored, (
        f"Test '{tcase.desc}': expected {tcase.expected_ignored}, got {result} "
        f"for file '{tcase.file_to_check}' with pattern '{tcase.ignore_content.strip()}'"
    )


@dataclass
class IgnorePatternCase:
    desc: str
    ignore_files: list
    file_contents: dict
    patch_open: str | None
    expected_count: int

@pytest.mark.parametrize(
    "case",
    [
        IgnorePatternCase(
            desc="empty_list",
            ignore_files=[],
            file_contents={},
            patch_open=None,
            expected_count=0,
        ),
        IgnorePatternCase(
            desc="nonexistent_file",
            ignore_files=[".nonexistent"],
            file_contents={},
            patch_open=None,
            expected_count=0,
        ),
        IgnorePatternCase(
            desc="single_file",
            ignore_files=[".gitignore"],
            file_contents={".gitignore": "*.pyc\n__pycache__/\n# This is a comment\n\n"},
            patch_open=None,
            expected_count=2,
        ),
        IgnorePatternCase(
            desc="multiple_files",
            ignore_files=[".gitignore", ".prettierignore"],
            file_contents={
                ".gitignore": "*.pyc\n__pycache__/\n",
                ".prettierignore": "dist/\nnode_modules/\n",
            },
            patch_open=None,
            expected_count=4,
        ),
        IgnorePatternCase(
            desc="io_error",
            ignore_files=[".gitignore"],
            file_contents={".gitignore": "*.pyc\n"},
            patch_open="OSError",
            expected_count=0,
        ),
        IgnorePatternCase(
            desc="unicode_error",
            ignore_files=[".gitignore"],
            file_contents={".gitignore": "*.pyc\n"},
            patch_open="UnicodeDecodeError",
            expected_count=0,
        ),
    ],
    ids=lambda c: c.desc,
)
def test_load_ignore_patterns_parametrized(case: IgnorePatternCase, temp_dir: Path, mocker):
    """Parametrized test for loading ignore patterns from various files and error conditions."""
    root_dir = Path(temp_dir)
    for fname, content in case.file_contents.items():
        (root_dir / fname).write_text(content)

    if case.patch_open == "OSError":
        mocker.patch.object(Path, "open", side_effect=OSError("Permission denied"))
    elif case.patch_open == "UnicodeDecodeError":
        mocker.patch.object(
            Path,
            "open",
            side_effect=UnicodeDecodeError("utf-8", b"\x80", 0, 1, "invalid start byte"),
        )

    spec = load_ignore_patterns(case.ignore_files, root_dir)
    assert len(spec.patterns) == case.expected_count



@dataclass
class ShouldIgnoreFileCase:
    desc: str
    ignore_content: str
    file_to_check: str
    expected: bool
    root_dir_offset: str = ""
    spec_is_none: bool = False

@pytest.mark.parametrize(
    "case",
    [
        ShouldIgnoreFileCase(
            desc="none_spec",
            ignore_content="",
            file_to_check="test.py",
            expected=False,
            spec_is_none=True,
        ),
        ShouldIgnoreFileCase(
            desc="absolute_path",
            ignore_content="*.pyc\n",
            file_to_check="test.pyc",
            expected=True,
            root_dir_offset="",
        ),
        ShouldIgnoreFileCase(
            desc="outside_root",
            ignore_content="*.pyc\n",
            file_to_check="/outside/test.pyc",
            expected=False,
            root_dir_offset="",
        ),
    ],
    ids=lambda c: c.desc,
)
def test_should_ignore_file_cases(case: ShouldIgnoreFileCase, temp_dir: Path):
    root_dir = Path(temp_dir) / case.root_dir_offset
    ignore_file = root_dir / '.gitignore'
    if not case.spec_is_none:
        ignore_file.write_text(case.ignore_content)
        spec = load_ignore_patterns(['.gitignore'], root_dir)
    else:
        spec = None
    if case.desc == "outside_root":
        file_path = Path(Path(temp_dir).anchor, *case.file_to_check.lstrip('/').split('/'))
    else:
        file_path = Path(case.file_to_check)
    result = should_ignore_file(file_path, spec, root_dir)
    assert result == case.expected



def test_filter_ignored_files(temp_dir: Path) -> None:
    """Test filtering a list of files."""
    root_dir = Path(temp_dir)
    ignore_file = root_dir / '.gitignore'
    ignore_file.write_text('*.pyc\n__pycache__/\n')

    spec = load_ignore_patterns(['.gitignore'], root_dir)

    files = [
        Path('test.py'),
        Path('test.pyc'),
        Path('__pycache__/cached.py'),
        Path('src/main.py'),
        Path('src/main.pyc'),
    ]

    filtered = filter_ignored_files(files, spec, root_dir)
    expected = [Path('test.py'), Path('src/main.py')]

    assert filtered == expected, f'Expected {expected}, got {filtered}'

def test_should_ignore_convenience_function(temp_dir: Path) -> None:
    """Test should_ignore convenience function."""
    root_dir = Path(temp_dir)
    ignore_file = root_dir / '.gitignore'
    ignore_file.write_text('*.pyc\n')

    manager = create_ignore_manager(['.gitignore'], root_dir)

    result = should_ignore(manager, Path('test.pyc'))
    assert result is True, 'Should ignore .pyc files based on .gitignore patterns'


def test_ignore_manager_filter_files_method(temp_dir: Path) -> None:
    """Test IgnoreManager.filter_files method."""
    root_dir = Path(temp_dir)
    ignore_file = root_dir / '.gitignore'
    ignore_file.write_text('*.pyc\n')

    manager = create_ignore_manager(['.gitignore'], root_dir)

    files = [Path('test.py'), Path('test.pyc')]
    filtered = manager.filter_files(files)

    assert filtered == [Path('test.py')]



def test_create_ignore_manager_default_cwd(mocker: MockerFixture) -> None:
    """Test create_ignore_manager with default current working directory."""
    mock_cwd = Path('/mock/cwd')
    mocker.patch('pathlib.Path.cwd', return_value=mock_cwd)
    mocker.patch.object(
        ignore_mod,
        'load_ignore_patterns',
        return_value=mocker.Mock(),
    )

    manager = create_ignore_manager(['.gitignore'])

    assert manager.ignore_files == ['.gitignore']
    assert manager.root_dir == mock_cwd


def test_create_ignore_manager_explicit_root(temp_dir: Path) -> None:
    """Test create_ignore_manager with explicit root directory."""
    root_dir = Path(temp_dir)
    ignore_file = root_dir / '.gitignore'
    ignore_file.write_text('*.pyc\n')

    manager = create_ignore_manager(['.gitignore'], root_dir)

    assert manager.ignore_files == ['.gitignore']
    assert manager.root_dir == root_dir
    assert manager._spec is not None


def test_ignore_manager_dataclass(temp_dir: Path) -> None:
    """Test IgnoreManager dataclass basic functionality."""
    root_dir = Path(temp_dir)
    manager = IgnoreManager(
        ignore_files=['.gitignore'],
        root_dir=root_dir,
        _spec=None,
    )

    assert manager.ignore_files == ['.gitignore']
    assert manager.root_dir == root_dir
    assert manager._spec is None


def test_ignore_manager_should_ignore_method(temp_dir: Path) -> None:
    """Test IgnoreManager.should_ignore method."""
    root_dir = Path(temp_dir)
    ignore_file = root_dir / '.gitignore'
    ignore_file.write_text('*.pyc\n')

    manager = create_ignore_manager(['.gitignore'], root_dir)

    assert manager.should_ignore(Path('test.pyc')) is True, 'Should ignore .pyc files'
    assert manager.should_ignore(Path('test.py')) is False, 'Should not ignore .py files'


def test_filter_files_convenience_function(temp_dir: Path) -> None:
    """Test filter_files convenience function."""
    root_dir = Path(temp_dir)
    ignore_file = root_dir / '.gitignore'
    ignore_file.write_text('*.pyc\n')

    manager = create_ignore_manager(['.gitignore'], root_dir)

    files = [Path('test.py'), Path('test.pyc')]
    filtered = filter_files(manager, files)

    assert filtered == [Path('test.py')]


def test_ignore_patterns_comments_and_empty_lines(temp_dir: Path) -> None:
    """Test that comments and empty lines are properly filtered."""
    root_dir = Path(temp_dir)
    ignore_file = root_dir / '.gitignore'
    ignore_file.write_text("""
# This is a comment
*.pyc

# Another comment
__pycache__/

    """)

    spec = load_ignore_patterns(['.gitignore'], root_dir)

    # Should only have 2 patterns (comments and empty lines filtered out)
    assert len(spec.patterns) == 2

    # Test the patterns work
    assert should_ignore_file(Path('test.pyc'), spec, root_dir) is True
    assert should_ignore_file(Path('__pycache__/test.py'), spec, root_dir) is True
    assert should_ignore_file(Path('test.py'), spec, root_dir) is False


def test_ignore_patterns_with_whitespace(temp_dir: Path) -> None:
    """Test that patterns with leading/trailing whitespace are handled correctly."""
    root_dir = Path(temp_dir)
    ignore_file = root_dir / '.gitignore'
    ignore_file.write_text('  *.pyc  \n\t__pycache__/\t\n')

    spec = load_ignore_patterns(['.gitignore'], root_dir)

    # Should have 2 patterns with whitespace stripped
    assert len(spec.patterns) == 2

    # Test the patterns work
    assert should_ignore_file(Path('test.pyc'), spec, root_dir) is True
    assert should_ignore_file(Path('__pycache__/test.py'), spec, root_dir) is True


