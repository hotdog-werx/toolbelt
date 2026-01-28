import os
from dataclasses import dataclass

import pytest

from toolbelt.config.loader import (
    expand_variables_with_env_templates,
    get_env_variables_context,
)
from toolbelt.config.utils import (
    expand_template_string,
    expand_template_strings,
    normalize_extensions,
)


@dataclass
class ExpandStringCase:
    desc: str
    arg: str
    variables: dict[str, str]
    expected: str


@pytest.mark.parametrize(
    'tcase',
    [
        ExpandStringCase(
            desc='basic_variable_expansion',
            arg='foo ${BAR}',
            variables={'BAR': 'baz'},
            expected='foo baz',
        ),
        ExpandStringCase(
            desc='default_value_used_if_variable_missing',
            arg='foo ${BAR:default}',
            variables={},
            expected='foo default',
        ),
        ExpandStringCase(
            desc='default_value_present_but_variable_provided',
            arg='foo ${BAR:default}',
            variables={'BAR': 'baz'},
            expected='foo baz',
        ),
        ExpandStringCase(
            desc='plain_text_no_variables',
            arg='plain text',
            variables={},
            expected='plain text',
        ),
        ExpandStringCase(
            desc='variable_with_empty_default',
            arg='foo ${BAR:}',
            variables={},
            expected='foo ',
        ),
        ExpandStringCase(
            desc='variable_with_colon_in_default',
            arg='foo ${BAR:de:fault}',
            variables={},
            expected='foo de:fault',
        ),
        ExpandStringCase(
            desc='variable_not_present_no_default',
            arg='foo ${BAR}',
            variables={},
            expected='foo ',
        ),
        ExpandStringCase(
            desc='multiple_variables_in_one_string',
            arg='${A}${B}${C:default}',
            variables={'A': 'a', 'B': 'b'},
            expected='abdefault',
        ),
        ExpandStringCase(
            desc='variable_at_start_end',
            arg='${A}foo${B}',
            variables={'A': 'a', 'B': 'b'},
            expected='afoob',
        ),
        ExpandStringCase(
            desc='variable_with_digits_and_underscores',
            arg='${VAR_1:default}',
            variables={'VAR_1': 'v1'},
            expected='v1',
        ),
    ],
    ids=lambda c: c.desc,
)
def test_expand_template_string_should_expand_correctly(
    tcase: ExpandStringCase,
):
    result = expand_template_string(tcase.arg, tcase.variables)
    assert result == tcase.expected, (
        f'{tcase.desc}: {tcase.arg} with {tcase.variables} -> {result}, expected {tcase.expected}'
    )


def test_expand_template_strings_should_expand_correctly() -> None:
    result = expand_template_strings(
        ['arg1', '${VAR1}', 'arg3'],
        {'VAR1': 'value1'},
    )
    assert result == ['arg1', 'value1', 'arg3']


@pytest.mark.parametrize(
    ('args', 'variables', 'expected', 'description'),
    [
        # Basic argument splitting
        (
            ['${TB_COVERAGE_PATHS:--cov=src}'],
            {'TB_COVERAGE_PATHS': '--cov=toolbelt --cov=tests'},
            ['--cov=toolbelt', '--cov=tests'],
            'basic argument splitting',
        ),
        # Mixed arguments (some split, some don't)
        (
            ['-v', '${TB_COVERAGE_PATHS}', '--other'],
            {'TB_COVERAGE_PATHS': '--cov=src --cov=lib'},
            ['-v', '--cov=src', '--cov=lib', '--other'],
            'mixed arguments with splitting',
        ),
        # Plain strings with spaces don't get split
        (
            ['arg with spaces', '${VAR}'],
            {'VAR': 'single_value'},
            ['arg with spaces', 'single_value'],
            'plain strings with spaces preserved',
        ),
        # Variables without spaces don't get split
        (
            ['${VAR}'],
            {'VAR': 'single_value'},
            ['single_value'],
            'single value variables not split',
        ),
        # Quoted arguments are handled correctly
        (
            ['${QUOTED_ARGS}'],
            {'QUOTED_ARGS': '--message "hello world" --flag'},
            ['--message', 'hello world', '--flag'],
            'quoted arguments parsed correctly',
        ),
        # Malformed shell syntax falls back to single argument
        (
            ['${BAD_SHELL}'],
            {'BAD_SHELL': '--arg "unclosed quote'},
            ['--arg "unclosed quote'],
            'malformed shell syntax fallback',
        ),
        # Empty strings are filtered out
        (
            ['-v', '${EMPTY_VAR:}', '--other'],
            {'EMPTY_VAR': ''},
            ['-v', '--other'],
            'empty strings filtered out',
        ),
        # Empty strings in split arguments are filtered out
        (
            ['${MIXED_ARGS}'],
            {
                'MIXED_ARGS': '--flag1  --flag2',
            },  # Extra spaces create empty strings when split
            ['--flag1', '--flag2'],
            'empty strings from extra spaces filtered',
        ),
    ],
)
def test_expand_template_strings_with_argument_splitting(
    args: list[str],
    variables: dict[str, str],
    expected: list[str],
    description: str,
) -> None:
    """Test that template variables containing spaces get split into multiple arguments."""
    result = expand_template_strings(args, variables)
    assert result == expected


def test_environment_variables_in_template_expansion() -> None:
    """Test that environment variables can be used in template expansion.

    This test verifies the complete flow: environment variables are filtered
    by the loader and can be used in template substitution.
    """
    # Set up test environment variables
    test_env_vars = {
        'TOOLBELT_TEST_VAR': 'test_value',
        'TB_BRANCH': 'main',
        'CI_BUILD_NUMBER': '123',
        'SECRET_VAR': 'should_not_be_accessible',  # Should be filtered out
    }

    # Temporarily modify environment
    original_env = {}
    for key, value in test_env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    try:
        # Get filtered environment variables
        env_context = get_env_variables_context()

        # Verify filtering works correctly
        assert 'TOOLBELT_TEST_VAR' in env_context
        assert 'TB_BRANCH' in env_context
        assert 'CI_BUILD_NUMBER' in env_context
        assert 'SECRET_VAR' not in env_context  # Should be filtered out

        # Test template expansion with environment variables
        test_cases = [
            ('${TOOLBELT_TEST_VAR}', 'test_value'),
            ('branch: ${TB_BRANCH}', 'branch: main'),
            ('build-${CI_BUILD_NUMBER}', 'build-123'),
            ('${TB_BRANCH}-${CI_BUILD_NUMBER}', 'main-123'),
            (
                '${MISSING_VAR:default}',
                'default',
            ),  # Test default with missing env var
        ]

        for template, expected in test_cases:
            result = expand_template_string(template, env_context)
            assert result == expected, f"Template '{template}' should expand to '{expected}', got '{result}'"

        # Test with additional regular variables (should override env vars)
        combined_vars = {**env_context, 'TB_BRANCH': 'override_branch'}
        result = expand_template_string('${TB_BRANCH}', combined_vars)
        assert result == 'override_branch'

    finally:
        # Restore original environment
        for key, original_value in original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value


def test_config_variables_can_reference_any_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that config variables can reference any environment variable via templates.

    This allows config files to use external environment variables without requiring
    them to be redefined in the config, while still maintaining security through
    filtered runtime overrides.
    """
    # Set up test environment variables (including one that would be filtered)
    test_env_vars = {
        'TOOLBELT_ALLOWED_VAR': 'allowed_value',
        'EXTERNAL_TOOL_VAR': 'external_value',
        'SECRET_API_KEY': 'secret123',  # Would be filtered from runtime overrides
        'HOME': '/home/user',  # Common env var
    }

    # Use monkeypatch to temporarily set environment variables
    for key, value in test_env_vars.items():
        monkeypatch.setenv(key, value)

    # Test that any env var can be referenced in config variables
    config_variables = {
        'tb_var': '${TOOLBELT_ALLOWED_VAR}',
        'external_var': '${EXTERNAL_TOOL_VAR}',
        'secret_var': '${SECRET_API_KEY}',
        'home_var': '${HOME}',
        'combined': '${EXTERNAL_TOOL_VAR}-${HOME}',
        'missing_with_default': '${MISSING_VAR:default_value}',
    }

    expanded = expand_variables_with_env_templates(config_variables)

    # Verify all variables were expanded using all env vars
    assert expanded['tb_var'] == 'allowed_value'
    assert expanded['external_var'] == 'external_value'
    assert expanded['secret_var'] == 'secret123'  # noqa: S105  # Even sensitive vars are accessible
    assert expanded['home_var'] == '/home/user'
    assert expanded['combined'] == 'external_value-/home/user'
    assert expanded['missing_with_default'] == 'default_value'

    # Verify that filtered env context still excludes sensitive vars
    filtered_env = get_env_variables_context()
    assert 'TOOLBELT_ALLOWED_VAR' in filtered_env
    assert 'EXTERNAL_TOOL_VAR' not in filtered_env  # Not in allowed prefixes
    assert 'SECRET_API_KEY' not in filtered_env
    assert 'HOME' not in filtered_env


@dataclass
class ExtensionTestCase:
    """Test case for extension normalization."""

    desc: str
    input_extensions: list[str]
    expected_extensions: list[str]


@pytest.mark.parametrize(
    'tcase',
    [
        ExtensionTestCase(
            desc='already-normalized',
            input_extensions=['.py', '.pyx'],
            expected_extensions=['.py', '.pyx'],
        ),
        ExtensionTestCase(
            desc='needs-dots',
            input_extensions=['py', 'pyx'],
            expected_extensions=['.py', '.pyx'],
        ),
        ExtensionTestCase(
            desc='mixed',
            input_extensions=['.py', 'pyx', '.so'],
            expected_extensions=['.py', '.pyx', '.so'],
        ),
        ExtensionTestCase(
            desc='empty',
            input_extensions=[],
            expected_extensions=[],
        ),
    ],
    ids=lambda c: c.desc,
)
def test_extension_normalization(tcase: ExtensionTestCase) -> None:
    """Test that extensions get normalized with dots."""
    normalized = normalize_extensions(tcase.input_extensions)
    assert normalized == tcase.expected_extensions
