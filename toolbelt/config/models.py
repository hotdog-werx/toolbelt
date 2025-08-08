from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .utils import expand_template_strings, normalize_extensions


class ToolConfig(BaseModel):
    """Configuration for a single tool."""

    model_config = ConfigDict(extra='forbid')

    name: str = Field(..., description='Name of the tool')
    command: str = Field(..., description='Command to execute')
    args: list[str] = Field(
        ...,
        description='Base arguments for the tool',
    )
    file_handling_mode: Literal['batch', 'per_file', 'no_target'] = Field(
        default='per_file',
        description=(
            'How to handle provided files: batch (process all files at once), '
            'per_file (process each file individually), no_target (ignore files)'
        ),
    )
    default_target: str | None = Field(
        default=None,
        description='Default target when no files provided (for append_targets mode)',
    )
    output_to_file: bool = Field(
        default=False,
        description='If True, tool outputs to stdout and toolbelt will redirect to overwrite the input file',
    )
    ignore_files: list[str] = Field(
        default_factory=lambda: ['.gitignore'],
        description='List of ignore files to respect when finding files (e.g., .gitignore, .prettierignore)',
    )
    extensions: list[str] = Field(
        default_factory=list,
        description='File extensions this tool applies to',
    )
    working_dir: str | None = Field(
        default=None,
        description='Working directory to run the tool in',
    )
    description: str | None = Field(
        None,
        description='Description of what the tool does',
    )

    def can_discover_files(self) -> bool:
        """Check if tool can discover files on its own."""
        return self.file_handling_mode in ['batch', 'no_target'] or (
            self.file_handling_mode == 'per_file' and self.default_target is not None
        )


class ProfileConfig(BaseModel):
    """Configuration for a specific profile."""

    name: str = Field(..., description='Name of the profile')
    extensions: list[str] = Field(
        ...,
        description='File extensions for this profile',
    )
    check_tools: list[ToolConfig] = Field(
        ...,
        description='Tools for checking code',
    )
    format_tools: list[ToolConfig] = Field(
        ...,
        description='Tools for formatting code',
    )
    exclude_patterns: list[str] = Field(
        default_factory=list,
        description='Patterns to exclude from processing',
    )
    ignore_files: list[str] = Field(
        default_factory=lambda: ['.gitignore'],
        description='List of ignore files to respect when finding files',
    )

    @field_validator('extensions')
    @classmethod
    def validate_extensions(cls, v: list[str]) -> list[str]:
        """Ensure extensions start with a dot."""
        return normalize_extensions(v)


class ToolbeltConfig(BaseModel):
    """Main configuration for toolbelt."""

    sources: list[str] = Field(default_factory=list, exclude=True)

    profiles: dict[str, ProfileConfig] = Field(
        default_factory=dict,
        description='Profile configurations',
    )
    global_exclude_patterns: list[str] = Field(
        default_factory=list,
        description='Global patterns to exclude',
    )
    variables: dict[str, str] = Field(
        default_factory=dict,
        description='Template variables for use in tool configurations',
    )

    def get_profile(self, name: str) -> ProfileConfig | None:
        """Get configuration for a specific profile."""
        return self.profiles.get(name)

    def list_profiles(self) -> list[str]:
        """List all configured profiles."""
        return list(self.profiles.keys())

    def get_variables(self) -> dict[str, str]:
        """Get template variables for this configuration."""
        return self.variables


@dataclass
class ToolCommand:
    """Represents a command to be executed for a tool."""

    full_command: list[str]
    base_command: list[str]
    unexpanded_base_command: list[str] | None = None
    files_or_targets: list[str] | None = None
    unexpanded_files_or_targets: list[str] | None = None


def get_tool_command(
    tool: 'ToolConfig',
    *,
    files: list[str] | None = None,
    targets: list[str] | None = None,
    variables: dict[str, str] | None = None,
) -> ToolCommand:
    """Build the command for a ToolConfig instance and capture all relevant info.

    Args:
        tool: The ToolConfig instance to build the command for.
        files: List of files to process (if applicable).
        targets: List of target directories/files to append to the command.
        variables: Template variables for expansion.

    Returns:
        ToolCommand dataclass instance with full/expanded/unexpanded command info.
    """
    # Unexpanded base command (raw config)
    unexpanded_base_command = [tool.command, *tool.args]
    base_command = expand_template_strings(
        unexpanded_base_command,
        variables or {},
    )

    files_or_targets = None
    unexpanded_files_or_targets = None

    full_command = base_command.copy()

    # Handle file mode
    if files is not None:
        files_or_targets = files
        unexpanded_files_or_targets = files  # files are user input, not templated
        full_command.extend(files)
    elif tool.file_handling_mode == 'batch':
        # Handle discovery/target modes
        if targets:
            files_or_targets = expand_template_strings(targets, variables or {})
            unexpanded_files_or_targets = targets
            full_command.extend(files_or_targets)
        elif tool.default_target:
            files_or_targets = expand_template_strings(
                [tool.default_target],
                variables or {},
            )
            unexpanded_files_or_targets = [tool.default_target]
            full_command.extend(files_or_targets)

    return ToolCommand(
        full_command=full_command,
        base_command=base_command,
        unexpanded_base_command=unexpanded_base_command,
        files_or_targets=files_or_targets,
        unexpanded_files_or_targets=unexpanded_files_or_targets,
    )
