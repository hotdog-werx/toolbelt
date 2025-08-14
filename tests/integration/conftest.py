"""Fixtures for integration tests."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

import pytest

if TYPE_CHECKING:  # type-only imports
    from collections.abc import Callable


@pytest.fixture
def fixture_files_dir() -> Path:
    """Return path to fixture files directory."""
    return Path(__file__).parent / 'fixtures' / 'files'


@pytest.fixture
def fixture_configs_dir() -> Path:
    """Return path to fixture configs directory."""
    return Path(__file__).parent / 'fixtures' / 'configs'


@pytest.fixture
def copy_fixture_file(fixture_files_dir: Path) -> Callable[[str, Path], Path]:
    """Return a helper that copies a fixture file to a destination directory."""

    def _copy_file(filename: str, dest_dir: Path) -> Path:
        src_file = fixture_files_dir / filename
        if not src_file.exists():
            msg = f'Fixture file {filename} not found at {src_file}'
            raise FileNotFoundError(msg)

        dest_file = dest_dir / filename
        shutil.copy2(src_file, dest_file)
        return dest_file

    return _copy_file


@pytest.fixture
def copy_fixture_config(
    fixture_configs_dir: Path,
) -> Callable[[str, Path], Path]:
    """Return a helper that copies a fixture config to a destination directory."""

    def _copy_config(config_name: str, dest_dir: Path) -> Path:
        src_config = fixture_configs_dir / config_name
        if not src_config.exists():
            msg = f'Fixture config {config_name} not found at {src_config}'
            raise FileNotFoundError(msg)

        dest_config = dest_dir / 'toolbelt.yaml'  # Always name it toolbelt.yaml in test
        shutil.copy2(src_config, dest_config)
        return dest_config

    return _copy_config


class RunToolbeltCLI(Protocol):
    """Callable protocol for running the toolbelt CLI in tests."""

    def __call__(
        self,
        args: list[str],
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:  # pragma: no cover - protocol signature
        ...


@pytest.fixture
def run_toolbelt_cli() -> RunToolbeltCLI:
    """Provide a callable to run the toolbelt CLI and capture its result."""

    def _run_cli(
        args: list[str],
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        # The arguments are controlled in tests; safe for subprocess execution.
        cmd = ['python', '-m', 'toolbelt.cli.main', *args]
        return subprocess.run(  # noqa: S603 - Controlled test harness command
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,  # Prevent hanging tests
            check=False,  # Don't raise on non-zero exit
        )

    return _run_cli


@pytest.fixture
def setup_test_environment(
    tmp_path: Path,
    copy_fixture_file: Callable[[str, Path], Path],
    copy_fixture_config: Callable[[str, Path], Path],
) -> Callable[[str, list[str]], tuple[Path, list[Path]]]:
    """Set up a complete test environment with config and files.

    Returns a callable that, given a config name and a list of fixture file
    names, copies them into the temporary path and returns the config path
    plus the list of copied file paths.
    """

    def _setup(
        config_name: str,
        file_names: list[str],
    ) -> tuple[Path, list[Path]]:
        # Copy config
        config_path = copy_fixture_config(config_name, tmp_path)

        # Copy files
        file_paths: list[Path] = []
        for filename in file_names:
            file_path = copy_fixture_file(filename, tmp_path)
            file_paths.append(file_path)

        return config_path, file_paths

    return _setup
