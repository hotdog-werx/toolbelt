from dataclasses import dataclass

import pytest

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
