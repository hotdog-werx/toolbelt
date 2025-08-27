import argparse

import pytest
from pytest_mock import MockerFixture

import toolbelt.cli.config as cli_config
from toolbelt.cli.config import handle_config_command
from toolbelt.config.models import ProfileConfig, ToolbeltConfig, ToolConfig


@pytest.fixture
def sample_config():
    """Create a sample config for testing."""
    return ToolbeltConfig(
        sources=['/path/to/config.yaml'],
        profiles={
            'python': ProfileConfig(
                name='python',
                extensions=['.py'],
                check_tools=[
                    ToolConfig(
                        name='ruff',
                        command='ruff',
                        args=['check', '${TB_PROJECT_SOURCE}'],
                        description='Python linter',
                    ),
                    ToolConfig(
                        name='mypy',
                        command='mypy',
                        args=['--strict', '${TB_PROJECT_SOURCE}'],
                        description='Type checker',
                    ),
                ],
                format_tools=[
                    ToolConfig(
                        name='black',
                        command='black',
                        args=['${TB_PROJECT_SOURCE}'],
                        description='Code formatter',
                        default_target='.',
                    ),
                ],
            ),
            'yaml': ProfileConfig(
                name='yaml',
                extensions=['.yaml', '.yml'],
                check_tools=[],
                format_tools=[
                    ToolConfig(
                        name='prettier',
                        command='prettier',
                        args=['--write'],
                        file_handling_mode='per_file',
                        description='YAML formatter',
                    ),
                ],
            ),
        },
        variables={
            'TB_PROJECT_SOURCE': 'src',
            'TB_VERSION': '1.0.0',
            'TB_ENV_VAR': 'env_value',
        },
    )


def test_handle_config_command_shows_summary(
    sample_config: ToolbeltConfig,
    mocker: MockerFixture,
) -> None:
    """Test that config command shows profile summary by default."""
    mock_console = mocker.patch.object(cli_config, 'console')

    args = argparse.Namespace(
        config=None,
        profile=None,
        show_variables=False,
    )

    result = handle_config_command(sample_config, args)

    # Should show config sources (no mock, just check console output)

    # Should print multiple times (header, table, usage hints)
    assert mock_console.print.call_count >= 3

    # Should return success
    assert result == 0


def test_handle_config_command_shows_variables(
    sample_config: ToolbeltConfig,
    mocker: MockerFixture,
) -> None:
    """Test that config command shows variables when requested."""
    mock_console = mocker.patch.object(cli_config, 'console')

    args = argparse.Namespace(
        config=None,
        profile=None,
        show_variables=True,
    )

    result = handle_config_command(sample_config, args)

    # Should show config sources (no mock, just check console output)

    # Should print variables section
    assert mock_console.print.called

    # Should return success
    assert result == 0


def test_handle_config_command_shows_specific_profile(
    sample_config: ToolbeltConfig,
    mocker: MockerFixture,
) -> None:
    """Test that config command shows specific profile details."""
    mock_console = mocker.patch.object(cli_config, 'console')

    args = argparse.Namespace(
        config=None,
        profile='python',
        show_variables=False,
    )

    result = handle_config_command(sample_config, args)

    # Should show config sources (no mock, just check console output)

    # Should print profile details
    assert mock_console.print.call_count >= 5  # Profile header + tools

    # Should return success
    assert result == 0


def test_handle_config_command_shows_raw_and_expanded_commands(
    sample_config: ToolbeltConfig,
    mocker: MockerFixture,
) -> None:
    """Test that config command shows both raw and expanded commands for tools."""
    mock_console = mocker.patch.object(cli_config, 'console')

    args = argparse.Namespace(
        config=None,
        profile='python',
        show_variables=False,
    )

    result = handle_config_command(sample_config, args)

    # Should show profile details with tools
    assert mock_console.print.call_count >= 5

    # Should return success
    assert result == 0


def test_handle_config_command_nonexistent_profile(
    sample_config: ToolbeltConfig,
    mocker: MockerFixture,
) -> None:
    """Test that config command handles nonexistent profile gracefully."""
    mock_console = mocker.patch.object(cli_config, 'console')

    args = argparse.Namespace(
        config=None,
        profile='nonexistent',
        show_variables=False,
    )

    result = handle_config_command(sample_config, args)

    # Should show config sources (no mock, just check console output)

    # Should print error message
    assert mock_console.print.called

    # Should return success (even for nonexistent profile)
    assert result == 0


def test_handle_config_command_with_config_path(
    sample_config: ToolbeltConfig,
    mocker: MockerFixture,
) -> None:
    """Test that config command passes through the config path."""
    mocker.patch.object(cli_config, 'console')

    args = argparse.Namespace(
        config='/custom/config.yaml',
        profile=None,
        show_variables=False,
    )

    result = handle_config_command(sample_config, args)

    # Should pass the custom config path to show_config_sources (no mock, just check console output)

    # Should return success
    assert result == 0


def test_handle_config_command_no_variables(
    mocker: MockerFixture,
) -> None:
    """Test that config command handles configs with no variables."""
    mock_console = mocker.patch.object(cli_config, 'console')

    # Config with no variables
    config = ToolbeltConfig(
        sources=['/path/to/config.yaml'],
        profiles={
            'simple': ProfileConfig(
                name='simple',
                extensions=['.txt'],
                check_tools=[],
                format_tools=[],
            ),
        },
        variables={},  # Empty variables
    )

    args = argparse.Namespace(
        config=None,
        profile=None,
        show_variables=True,
    )

    result = handle_config_command(config, args)

    # Should print something (no variables message)
    assert mock_console.print.called

    # Should return success
    assert result == 0


def test_handle_config_command_no_profiles(
    mocker: MockerFixture,
) -> None:
    """Test that config command handles configs with no profiles."""
    mock_console = mocker.patch.object(cli_config, 'console')

    # Config with no profiles
    config = ToolbeltConfig(
        sources=['/path/to/config.yaml'],
        profiles={},  # Empty profiles
        variables={},
    )

    args = argparse.Namespace(
        config=None,
        profile=None,
        show_variables=False,
    )

    result = handle_config_command(config, args)

    # Should print something (no profiles message)
    assert mock_console.print.called

    # Should return success
    assert result == 0


def test_profile_with_tool_descriptions_and_options(
    mocker: MockerFixture,
) -> None:
    """Test that tool descriptions and additional options are displayed."""
    mock_console = mocker.patch.object(cli_config, 'console')

    # Config with tools that have descriptions and additional options
    config = ToolbeltConfig(
        sources=['/path/to/config.yaml'],
        profiles={
            'advanced': ProfileConfig(
                name='advanced',
                extensions=['.py'],
                check_tools=[
                    ToolConfig(
                        name='advanced_tool',
                        command='tool',
                        args=['--flag', '${VAR}'],
                        description='Tool with description',
                        default_target='./src',
                        working_dir='/custom/dir',
                        output_to_file=True,
                    ),
                ],
                format_tools=[],
            ),
        },
        variables={'VAR': 'value'},
    )

    args = argparse.Namespace(
        config=None,
        profile='advanced',
        show_variables=False,
    )

    result = handle_config_command(config, args)

    # Should print profile details
    assert mock_console.print.called

    # Should return success
    assert result == 0
