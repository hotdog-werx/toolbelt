from dataclasses import dataclass
from pathlib import Path

import pytest

from toolbelt.cli.main import create_parser


@dataclass
class ParseTestCase:
    desc: str
    args: list[str]
    expected_command: str
    expected_profile: str | None = None
    expected_files: list[Path] | None = None
    expected_verbose: bool = False
    expected_config: Path | None = None

    def __post_init__(self) -> None:
        """Post-initialization processing."""
        if self.expected_files is None:
            self.expected_files = []


@pytest.mark.parametrize(
    'tcase',
    [
        ParseTestCase(
            desc='check_command_with_files',
            args=['check', 'python', 'file1.py', 'file2.py'],
            expected_command='check',
            expected_profile='python',
            expected_files=[Path('file1.py'), Path('file2.py')],
        ),
        ParseTestCase(
            desc='format_command_single_file',
            args=['format', 'javascript', 'src/app.js'],
            expected_command='format',
            expected_profile='javascript',
            expected_files=[Path('src/app.js')],
        ),
        ParseTestCase(
            desc='check_discovery_mode',
            args=['check', 'python'],
            expected_command='check',
            expected_profile='python',
            expected_files=[],
        ),
        ParseTestCase(
            desc='with_config_file',
            args=['--config', 'custom.yaml', 'check', 'python', 'file.py'],
            expected_command='check',
            expected_profile='python',
            expected_files=[Path('file.py')],
            expected_config=Path('custom.yaml'),
        ),
        ParseTestCase(
            desc='verbose_mode',
            args=['--verbose', 'check', 'python', 'file.py'],
            expected_command='check',
            expected_profile='python',
            expected_files=[Path('file.py')],
            expected_verbose=True,
        ),
        ParseTestCase(
            desc='list_command_no_language',
            args=['list'],
            expected_command='list',
            expected_profile=None,
        ),
        ParseTestCase(
            desc='list_command_with_language',
            args=['list', 'python'],
            expected_command='list',
            expected_profile='python',
        ),
    ],
    ids=lambda c: c.desc,
)
def test_argument_parsing(tcase: ParseTestCase) -> None:
    """Test CLI argument parsing with various combinations."""
    parser = create_parser()
    args = parser.parse_args(tcase.args)

    assert args.command == tcase.expected_command
    assert args.profile == tcase.expected_profile

    # Only check/format commands have 'files' attribute, list command doesn't
    if hasattr(args, 'files'):
        assert args.files == tcase.expected_files
    else:
        # For list command, expected_files should be empty or None
        assert tcase.expected_files == [] or tcase.expected_files is None

    assert args.verbose == tcase.expected_verbose
    assert args.config == tcase.expected_config
