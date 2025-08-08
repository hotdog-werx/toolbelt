from dataclasses import dataclass

import pytest
from pytest_mock import MockerFixture

from toolbelt import package_resources
from toolbelt.package_resources import _resolve_package_resource_internal


@dataclass
class ResourceInternalCase:
    package_name: str
    resource_path: str
    should_error: bool
    error_type: type = FileNotFoundError
    error_msg: str = ''


@pytest.mark.parametrize(
    'tcase',
    [
        ResourceInternalCase(
            package_name='pytest',
            resource_path='not_a_real_resource.txt',
            should_error=True,
            error_type=FileNotFoundError,
            error_msg='not found in package',
        ),
    ],
)
def test_resolve_package_resource_internal_error(
    tcase: ResourceInternalCase,
) -> None:
    with pytest.raises(tcase.error_type, match=tcase.error_msg):
        _resolve_package_resource_internal(
            tcase.package_name,
            tcase.resource_path,
        )


def test_resolve_package_resource_internal_fallback_to_tempfile(
    mocker: MockerFixture,
) -> None:
    """Test fallback to temp file when as_file fails, using mocks."""
    mock_resource = mocker.Mock()
    mock_resource.is_file.return_value = True
    mock_resource.read_bytes.return_value = b'dummy content'

    mock_files = mocker.Mock()
    mock_files.joinpath.return_value = mock_resource

    mocker.patch('importlib.resources.files', return_value=mock_files)
    mocker.patch(
        'importlib.resources.as_file',
        side_effect=AttributeError('simulate as_file failure'),
    )

    result = package_resources._resolve_package_resource_internal(
        'toolbelt',
        'resources/toolbelt.yaml',
    )
    assert result.exists(), f'Fallback temp file {result} does not exist.'
    assert result.read_bytes() == b'dummy content', 'Fallback temp file content mismatch.'
