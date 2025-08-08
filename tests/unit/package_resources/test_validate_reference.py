from dataclasses import dataclass

import pytest

from toolbelt.package_resources import _validate_package_reference


@dataclass
class ValidateRefCase:
    ref: str
    expected: list[str]


@pytest.mark.parametrize(
    'tcase',
    [
        ValidateRefCase(ref='@pkg:res.txt', expected=['pkg', 'res.txt']),
        ValidateRefCase(ref='@a:b/c', expected=['a', 'b/c']),
    ],
)
def test_validate_package_reference_valid(tcase: ValidateRefCase) -> None:
    result = _validate_package_reference(tcase.ref)
    assert result == tcase.expected, f'Expected {tcase.expected} for {tcase.ref}, got {result}'


@dataclass
class ValidateRefErrorCase:
    ref: str
    err_msg: str


@pytest.mark.parametrize(
    'tcase',
    [
        ValidateRefErrorCase(ref='pkg:res.txt', err_msg='must start with @'),
        ValidateRefErrorCase(ref='@pkgres.txt', err_msg='Expected format'),
        ValidateRefErrorCase(ref='', err_msg='must start with @'),
    ],
)
def test_validate_package_reference_invalid(
    tcase: ValidateRefErrorCase,
) -> None:
    with pytest.raises(ValueError, match=tcase.err_msg):
        _validate_package_reference(tcase.ref)
