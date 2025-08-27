from pytest_mock import MockerFixture

from toolbelt.cli import _utils as cli_utils
from toolbelt.cli._utils import get_profile_names_completer


def test_get_profile_names_completer_returns_non_empty_list():
    result = get_profile_names_completer()
    assert isinstance(result, list)
    assert result, 'Expected a non-empty list of profile names'


def test_get_profile_names_completer_returns_empty_on_error(
    mocker: MockerFixture,
):
    mocker.patch.object(
        cli_utils,
        'load_config',
        side_effect=RuntimeError('Simulated-error'),
    )
    result = get_profile_names_completer()
    assert isinstance(result, list)
    assert result == [], 'Expected an empty list when load_config fails'
