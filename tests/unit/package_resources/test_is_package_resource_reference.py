from dataclasses import dataclass

import pytest

from toolbelt.package_resources import is_package_resource_reference


@dataclass
class IsRefCase:
    ref: str
    expected: bool


@pytest.mark.parametrize(
    'tcase',
    [
        IsRefCase(ref='@pkg:res.txt', expected=True),
        IsRefCase(ref='@a:b/c', expected=True),
        IsRefCase(ref='pkg:res.txt', expected=False),
        IsRefCase(ref='@pkgres.txt', expected=False),
        IsRefCase(ref='', expected=False),
    ],
)
def test_is_package_resource_reference(tcase: IsRefCase) -> None:
    result = is_package_resource_reference(tcase.ref)
    assert result == tcase.expected, (
        f'is_package_resource_reference({tcase.ref!r}) returned {result}, expected {tcase.expected}'
    )
