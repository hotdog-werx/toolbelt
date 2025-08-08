from pathlib import Path
from textwrap import dedent

from toolbelt.config.loader import load_config


def test_merge_three_configs(tmp_path: Path):
    """Test merging three configs with overlapping and unique profiles."""
    # Base config: python, global exclude
    base_file = tmp_path / 'base.yaml'
    base_file.write_text(
        dedent("""
        profiles:
          python:
            extensions: [".py"]
            format_tools: []
            check_tools:
              - name: "ruff"
                command: "uvx"
                args: ["ruff@latest", "check"]
        global_exclude_patterns: ["*.pyc"]
        variables:
          MARKDOWNLINT_VERSION: 1.2.3
          TOOLBELT_RUFF_VERSION: "latest"
    """),
    )
    # Middle config: python (override), javascript
    middle_file = tmp_path / 'middle.yaml'
    middle_file.write_text(
        dedent("""
        profiles:
          python:
            extensions: [".py", ".pyi"]
            format_tools: []
            check_tools:
              - name: "flake8"
                command: "flake8"
                args: ["--max-line-length=88"]
          javascript:
            extensions: [".js"]
            format_tools: []
            check_tools:
              - name: "eslint"
                command: "npx"
                args: ["eslint"]
        global_exclude_patterns: ["node_modules/**"]
        variables:
          ESLINT_VERSION: "latest"
    """),
    )
    # Top config: javascript (override), add markdown
    top_file = tmp_path / 'top.yaml'
    top_file.write_text(
        dedent("""
        profiles:
          javascript:
            extensions: [".js", ".jsx"]
            format_tools: []
            check_tools:
              - name: "eslint"
                command: "npx"
                args: ["eslint", "--fix"]
          markdown:
            extensions: [".md"]
            format_tools: []
            check_tools:
              - name: "markdownlint"
                command: "markdownlint"
                args: ["--config", ".markdownlint.json"]
        global_exclude_patterns: ["docs/**"]
        variables:
          MARKDOWNLINT_VERSION: "latest"
    """),
    )
    config = load_config([base_file, middle_file, top_file])
    # Dump config as dict and compare to expected
    config_dict = config.model_dump()
    config_dict['sources'] = config.sources  # not included in model_dump
    expected = {
        'sources': [str(base_file), str(middle_file), str(top_file)],
        'profiles': {
            'python': {
                'name': 'python',
                'extensions': ['.py', '.pyi'],
                'check_tools': [
                    {
                        'name': 'flake8',
                        'command': 'flake8',
                        'args': ['--max-line-length=88'],
                        'file_handling_mode': 'per_file',
                        'default_target': None,
                        'output_to_file': False,
                        'ignore_files': ['.gitignore'],
                        'extensions': [],
                        'working_dir': None,
                        'description': None,
                    },
                ],
                'format_tools': [],
                'exclude_patterns': [],
                'ignore_files': ['.gitignore'],
            },
            'javascript': {
                'name': 'javascript',
                'extensions': ['.js', '.jsx'],
                'check_tools': [
                    {
                        'name': 'eslint',
                        'command': 'npx',
                        'args': ['eslint', '--fix'],
                        'file_handling_mode': 'per_file',
                        'default_target': None,
                        'output_to_file': False,
                        'ignore_files': ['.gitignore'],
                        'extensions': [],
                        'working_dir': None,
                        'description': None,
                    },
                ],
                'format_tools': [],
                'exclude_patterns': [],
                'ignore_files': ['.gitignore'],
            },
            'markdown': {
                'name': 'markdown',
                'extensions': ['.md'],
                'check_tools': [
                    {
                        'name': 'markdownlint',
                        'command': 'markdownlint',
                        'args': ['--config', '.markdownlint.json'],
                        'file_handling_mode': 'per_file',
                        'default_target': None,
                        'output_to_file': False,
                        'ignore_files': ['.gitignore'],
                        'extensions': [],
                        'working_dir': None,
                        'description': None,
                    },
                ],
                'format_tools': [],
                'exclude_patterns': [],
                'ignore_files': ['.gitignore'],
            },
        },
        'global_exclude_patterns': ['*.pyc', 'node_modules/**', 'docs/**'],
        'variables': {
            'MARKDOWNLINT_VERSION': 'latest',
            'TOOLBELT_RUFF_VERSION': 'latest',
            'ESLINT_VERSION': 'latest',
        },
    }
    assert config_dict == expected
