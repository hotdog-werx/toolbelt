from .models import ProfileConfig, ToolbeltConfig, ToolConfig


def create_python_config() -> ProfileConfig:
    """Create default a profile configuration for Python."""
    return ProfileConfig(
        name='python',
        extensions=['.py'],
        check_tools=[
            ToolConfig(
                name='ruff-check',
                command='uvx',
                args=['ruff@${TOOLBELT_RUFF_VERSION}', 'check'],
                description='lint python code with ruff',
                file_handling_mode='batch',
            ),
        ],
        format_tools=[
            ToolConfig(
                name='ruff-format',
                command='uvx',
                args=['ruff@${TOOLBELT_RUFF_VERSION}', 'format'],
                description='format python code with ruff',
                file_handling_mode='batch',
            ),
        ],
    )


def get_default_global_exclude_patterns() -> list[str]:
    """Get default global exclude patterns."""
    return [
        'node_modules/**',
        '.git/**',
        '**/__pycache__/**',
        '*.pyc',
        '.venv/**',
        'venv/**',
    ]


def get_default_config() -> ToolbeltConfig:
    """Return a default configuration for python."""
    return ToolbeltConfig(
        sources=['__default__'],
        profiles={
            'python': create_python_config(),
        },
        global_exclude_patterns=get_default_global_exclude_patterns(),
        variables={
            'TOOLBELT_RUFF_VERSION': 'latest',
        },
    )
