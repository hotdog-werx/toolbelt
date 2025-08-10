import os
from dataclasses import dataclass

import pytest

from toolbelt.config.loader import get_env_variables_context
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
        ['${X}', '${Y:yy}', '${Z:zz}'],
        {'X': 'x', 'Z': 'z'},
    )
    assert result == ['x', 'yy', 'z']


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
