"""Main test configuration and fixtures."""

import logging
import tempfile
from collections.abc import Generator
from pathlib import Path
from textwrap import dedent
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from structlog.types import FilteringBoundLogger

from toolbelt.config import ProfileConfig, ToolbeltConfig, ToolConfig


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_yaml_config(temp_dir: Path) -> Path:
    """Create a sample YAML config file for testing."""
    config_file = temp_dir / 'toolbelt.yaml'
    config_content = """
        profiles:
          python:
            extensions: ['.py']
            check_tools:
              - name: ruff-check
                command: uvx
                args: ['ruff@${TOOLBELT_RUFF_VERSION}', 'check']
                description: lint python code with ruff
                file_handling_mode: batch
            format_tools:
              - name: ruff-format
                command: uvx
                args: ['ruff@${TOOLBELT_RUFF_VERSION}', 'format']
                description: format python code with ruff
                file_handling_mode: batch
        global_exclude_patterns:
          - "**/__pycache__/**"
          - "*.pyc"
        variables:
          TOOLBELT_RUFF_VERSION: latest
    """
    config_file.write_text(dedent(config_content))
    return config_file


@pytest.fixture
def sample_python_config(temp_dir: Path) -> Path:
    """Create a sample Python config file for testing."""
    config_file = temp_dir / 'toolbelt.py'
    config_content = """
        from toolbelt.config import ToolbeltConfig, ProfileConfig, ToolConfig

        config = ToolbeltConfig(
            profiles={
                "python": ProfileConfig(
                    name="python",
                    extensions=[".py"],
                    check_tools=[
                        ToolConfig(
                            name="ruff-check",
                            command="uvx",
                            args=["ruff@${TOOLBELT_RUFF_VERSION}", "check"],
                            description="lint python code with ruff",
                            file_handling_mode="batch",
                        )
                    ],
                    format_tools=[
                        ToolConfig(
                            name="ruff-format",
                            command="uvx",
                            args=["ruff@${TOOLBELT_RUFF_VERSION}", "format"],
                            description="format python code with ruff",
                            file_handling_mode="batch",
                        )
                    ],
                )
            },
            global_exclude_patterns=[
                "**/__pycache__/**",
                "*.pyc",
            ],
            variables={
                "TOOLBELT_RUFF_VERSION": "latest",
            },
        )
    """
    config_file.write_text(dedent(config_content))
    return config_file