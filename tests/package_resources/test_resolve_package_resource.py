from tempfile import gettempdir

from toolbelt.package_resources import resolve_package_resource

RESOURCE_REF = '@toolbelt:resources/toolbelt.yaml'


def test_resolve_package_resource_dev_mode():
    path = resolve_package_resource(RESOURCE_REF)
    assert path.exists(), f'Resource path {path} does not exist.'
    assert path.is_file(), f'Resource path {path} is not a file.'
    # Should be a real file, not a temp file, in dev mode

    assert not str(path).startswith(gettempdir()), f'Path {path} should not be in tempdir in dev mode.'
    # Check content
    content = path.read_text()
    assert 'python:' in content
    assert 'prettier:' in content
