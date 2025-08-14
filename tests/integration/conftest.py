"""Fixtures for integration tests."""

import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def fixture_files_dir():
    """Return path to fixture files directory."""
    return Path(__file__).parent / 'fixtures' / 'files'


@pytest.fixture
def fixture_configs_dir():
    """Return path to fixture configs directory."""
    return Path(__file__).parent / 'fixtures' / 'configs'


@pytest.fixture
def copy_fixture_file(fixture_files_dir):
    """Copy a fixture file to a temporary directory."""

    def _copy_file(filename: str, dest_dir: Path) -> Path:
        src_file = fixture_files_dir / filename
        if not src_file.exists():
            raise FileNotFoundError(
                f'Fixture file {filename} not found at {src_file}',
            )

        dest_file = dest_dir / filename
        shutil.copy2(src_file, dest_file)
        return dest_file

    return _copy_file


@pytest.fixture
def copy_fixture_config(fixture_configs_dir):
    """Copy a fixture config to a temporary directory."""

    def _copy_config(config_name: str, dest_dir: Path) -> Path:
        src_config = fixture_configs_dir / config_name
        if not src_config.exists():
            raise FileNotFoundError(
                f'Fixture config {config_name} not found at {src_config}',
            )

        dest_config = dest_dir / 'toolbelt.yaml'  # Always name it toolbelt.yaml in test
        shutil.copy2(src_config, dest_config)
        return dest_config

    return _copy_config


@pytest.fixture
def run_toolbelt_cli():
    """Run toolbelt CLI command and return result."""

    def _run_cli(
        args: list[str],
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess:
        cmd = ['python', '-m', 'toolbelt.cli.main'] + args
        return subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,  # Prevent hanging tests
            check=False,  # Don't raise on non-zero exit
        )

    return _run_cli


@pytest.fixture
def setup_test_environment(tmp_path, copy_fixture_file, copy_fixture_config):
    """Set up a complete test environment with config and files."""

    def _setup(
        config_name: str,
        file_names: list[str],
    ) -> tuple[Path, list[Path]]:
        # Copy config
        config_path = copy_fixture_config(config_name, tmp_path)

        # Copy files
        file_paths = []
        for filename in file_names:
            file_path = copy_fixture_file(filename, tmp_path)
            file_paths.append(file_path)

        return config_path, file_paths

    return _setup
