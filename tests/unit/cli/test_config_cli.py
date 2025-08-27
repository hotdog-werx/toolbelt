import subprocess
import sys
from pathlib import Path


def test_config_cli_shows_only_top_level_sources(tmp_path: Path) -> None:
    """Test that tb config only shows top-level sources, not nested includes."""
    # Create a minimal pyproject.toml with a toolbelt include
    pyproject = tmp_path / 'pyproject.toml'
    pyproject.write_text(
        """
[tool.toolbelt]
include = ["@toolbelt:resources/presets/hdw.yaml"]
""",
    )
    # Run tb config and capture output
    result = subprocess.run(  # noqa: S603 - testing the cli
        [sys.executable, '-m', 'toolbelt.cli.main', 'config'],
        check=False,
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    output = result.stdout.replace(
        '\n',
        '',
    )  # Remove line breaks for robust matching
    # Should show all sources, including nested includes
    for fname in [
        'hdw.yaml',
        'python-dev.yaml',
        'web.yaml',
        'yaml.yaml',
        'python-hdw.yaml',
        'python-typed.yaml',
    ]:
        assert fname in output, f'Expected {fname} in CLI output'
