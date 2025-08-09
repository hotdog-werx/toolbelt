import logging
from dataclasses import dataclass
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

import toolbelt.runner.file_discovery as fd
from toolbelt.config import ProfileConfig
from toolbelt.runner.file_discovery import (
    find_files_by_extensions,
    get_target_files,
)


@dataclass
class GetTargetFilesCase:
    desc: str
    files: list[str] | None  # relative filenames or None
    create: list[str]  # which files to actually create
    expected: list[str]  # expected result (relative)
    extensions: list[str] | None = None
    log_missing: bool = False
    as_dir: bool = False  # If True, create a directory and put files inside
    use_any_ext: bool = False  # If True, use '.*' extension
    verbose: bool = False


@pytest.fixture
def sample_profile_config(tmp_path: Path):
    # Default profile config for .py files
    return ProfileConfig(
        name='python',
        extensions=['.py'],
        check_tools=[],
        format_tools=[],
        exclude_patterns=[],
        ignore_files=[],
    )


def make_files(
    tmp_path: Path,
    files: list[str],
    *,
    as_dir: bool = False,
) -> tuple[Path | None, list[Path]]:
    """Creates dummy files in a directory."""
    paths = []
    if as_dir:
        d = tmp_path / 'subdir'
        d.mkdir()
        for fname in files:
            p = d / fname
            p.write_text('dummy')
            paths.append(p)
        return d, paths
    for fname in files:
        p = tmp_path / fname
        p.write_text('dummy')
        paths.append(p)
    return None, paths


@pytest.mark.parametrize(
    'case',
    [
        GetTargetFilesCase(
            desc='all_files_exist_and_match_extension',
            files=['test.py'],
            create=['test.py'],
            expected=['test.py'],
        ),
        GetTargetFilesCase(
            desc='some_files_do_not_exist',
            files=['test.py', 'missing.py'],
            create=['test.py'],
            expected=['test.py'],
            log_missing=True,
        ),
        GetTargetFilesCase(
            desc='files_exist_no_ext_match',
            files=['test.js', 'readme.txt'],
            create=['test.js', 'readme.txt'],
            expected=[],
        ),
        GetTargetFilesCase(
            desc='discovery_mode_files_none',
            files=None,
            create=['found.py'],
            expected=['found.py'],
        ),
        GetTargetFilesCase(
            desc='discovery_mode_files_empty',
            files=[],
            create=['found.py'],
            expected=['found.py'],
        ),
        GetTargetFilesCase(
            desc='directory_provided_expands_to_matching_files',
            files=None,
            create=['a.py', 'b.py', 'c.txt'],
            expected=['a.py', 'b.py'],
            as_dir=True,
        ),
        GetTargetFilesCase(
            desc='extensions_include_star',
            files=['foo.txt', 'bar.py'],
            create=['foo.txt', 'bar.py'],
            expected=['foo.txt', 'bar.py'],
            use_any_ext=True,
        ),
    ],
    ids=lambda c: c.desc,
)
def test_get_target_files(
    tmp_path: Path,
    case: GetTargetFilesCase,
    capsys: pytest.CaptureFixture,
    caplog: pytest.LogCaptureFixture,
):
    # Use pytest monkeypatch to safely change working directory
    # This will be automatically restored after the test
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.chdir(tmp_path)
    # Setup profile config
    extensions = case.extensions if case.extensions is not None else ['.py']
    if case.use_any_ext:
        extensions = ['.*']
    profile = ProfileConfig(
        name='test',
        extensions=extensions,
        check_tools=[],
        format_tools=[],
        exclude_patterns=[],
        ignore_files=[],
    )
    # Create files and set up files/expected
    dir_path, _ = make_files(tmp_path, case.create, as_dir=case.as_dir)
    if case.as_dir and dir_path is not None:
        files = [dir_path] if case.files is None else [tmp_path / f for f in case.files]
        expected = [dir_path / f for f in case.expected]
    else:
        files = None if case.files is None else [tmp_path / f for f in case.files]
        expected = [tmp_path / f for f in case.expected]
    with caplog.at_level(logging.INFO):
        result = get_target_files(
            profile=profile,
            files=files,
            global_exclude_patterns=[],
            verbose=case.verbose,
        )

    # Convert all paths to absolute for comparison
    result = [Path(f).resolve() for f in result]
    expected = [Path(f).resolve() for f in expected]
    assert sorted(result) == sorted(expected)

    if case.log_missing:
        out = capsys.readouterr().out
        assert 'File not found' in out
        assert str(tmp_path) in out


@dataclass
class FindFilesByExtCase:
    desc: str
    create: list[str]
    extensions: list[str]
    exclude_patterns: list[str]
    ignore_files: list[str]
    global_exclude_patterns: list[str]
    verbose: bool = False
    expected: list[str] | None = None
    expected_sorted: list[str] | None = None


@pytest.mark.parametrize(
    'case',
    [
        FindFilesByExtCase(
            desc='exclude pattern',
            create=['keep.py', 'exclude_me.py'],
            extensions=['.py'],
            exclude_patterns=['exclude_me.py'],
            ignore_files=[],
            global_exclude_patterns=[],
            expected=['keep.py'],
        ),
        FindFilesByExtCase(
            desc='sorted result',
            create=['z_file.py', 'a_file.py', 'm_file.py'],
            extensions=['.py'],
            exclude_patterns=[],
            ignore_files=[],
            global_exclude_patterns=[],
            expected_sorted=['a_file.py', 'm_file.py', 'z_file.py'],
        ),
        FindFilesByExtCase(
            desc='single file verbose',
            create=['single.py'],
            extensions=['.py'],
            exclude_patterns=[],
            ignore_files=[],
            global_exclude_patterns=[],
            verbose=True,
            expected=['single.py'],
        ),
    ],
    ids=lambda c: c.desc,
)
def test_find_files_by_extensions_parametrized(
    tmp_path: Path,
    case: FindFilesByExtCase,
    capsys: pytest.CaptureFixture,
):
    # Create files
    for fname in case.create:
        (tmp_path / fname).write_text('dummy')
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.chdir(tmp_path)
    result = find_files_by_extensions(
        extensions=case.extensions,
        exclude_patterns=case.exclude_patterns,
        ignore_files=case.ignore_files,
        global_exclude_patterns=case.global_exclude_patterns,
        verbose=case.verbose,
    )
    result = [Path(f).resolve() for f in result]
    if case.expected is not None:
        expected = [Path(tmp_path / f).resolve() for f in case.expected]
        assert result == expected
    if case.expected_sorted is not None:
        expected_sorted = [Path(tmp_path / f).resolve() for f in case.expected_sorted]
        assert result == expected_sorted
    if case.verbose:
        out = capsys.readouterr().out
        assert 'Found files after applying ignore rules' in out


def test_find_files_by_extensions_ignore(tmp_path: Path, mocker: MockerFixture):
    (tmp_path / 'ignored.py').write_text('dummy')
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.chdir(tmp_path)

    # Patch the ignore manager's should_ignore method to return True for 'ignored.py'
    mock_ignore_manager = fd.create_ignore_manager([])
    mocker.patch.object(
        fd,
        'create_ignore_manager',
        return_value=mock_ignore_manager,
    )
    mocker.patch.object(
        mock_ignore_manager,
        'should_ignore',
        lambda path: str(path).endswith('ignored.py'),
    )

    result = find_files_by_extensions(
        extensions=['.py'],
        exclude_patterns=[],
        ignore_files=[],
        global_exclude_patterns=[],
        verbose=False,
    )
    result = [Path(f).resolve() for f in result]
    assert result == []
