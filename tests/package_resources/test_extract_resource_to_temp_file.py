from dataclasses import dataclass
from pathlib import Path

import pytest

from toolbelt.package_resources import _extract_resource_to_temp_file


@dataclass
class ExtractCase:
    content: bytes
    package_name: str
    resource_path: str


@pytest.mark.parametrize(
    'tcase',
    [
        ExtractCase(
            content=b'hello world',
            package_name='mypkg',
            resource_path='data.txt',
        ),
        ExtractCase(
            content=b'',
            package_name='empty',
            resource_path='empty.txt',
        ),
    ],
)
def test_extract_resource_to_temp_file(
    tmp_path: Path,
    tcase: ExtractCase,
) -> None:
    temp_file = _extract_resource_to_temp_file(
        tcase.content,
        tcase.package_name,
        tcase.resource_path,
    )
    assert temp_file.exists(), f'Temp file {temp_file} was not created.'
    assert temp_file.read_bytes() == tcase.content, f'Content mismatch for {temp_file}'
    assert temp_file.name.endswith(f'_{Path(tcase.resource_path).name}'), f'File suffix incorrect: {temp_file.name}'
    assert temp_file.name.startswith(f'{tcase.package_name}_'), f'File prefix incorrect: {temp_file.name}'
