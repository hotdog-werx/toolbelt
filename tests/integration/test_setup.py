"""Simple test to verify integration test setup."""


def test_fixture_files_exist(fixture_files_dir):
    """Verify all fixture files are present."""
    expected_files = [
        'bad_python_for_ruff.py',
        'needs_trailing_comma.py',
        'needs_sed_replacement.txt',
    ]

    for filename in expected_files:
        file_path = fixture_files_dir / filename
        assert file_path.exists(), f'Fixture file {filename} not found at {file_path}'
        assert file_path.stat().st_size > 0, f'Fixture file {filename} is empty'


def test_fixture_configs_exist(fixture_configs_dir):
    """Verify all fixture configs are present."""
    expected_configs = [
        'ruff_batch.yaml',
        'add_trailing_comma_per_file.yaml',
        'sed_write_to_file.yaml',
    ]

    for config_name in expected_configs:
        config_path = fixture_configs_dir / config_name
        assert config_path.exists(), f'Fixture config {config_name} not found at {config_path}'
        assert config_path.stat().st_size > 0, f'Fixture config {config_name} is empty'


def test_copy_fixtures(tmp_path, copy_fixture_file, copy_fixture_config):
    """Test that fixture copying works."""
    # Copy a config
    config_path = copy_fixture_config('ruff_batch.yaml', tmp_path)
    assert config_path.exists()
    assert config_path.name == 'toolbelt.yaml'

    # Copy a file
    file_path = copy_fixture_file('bad_python_for_ruff.py', tmp_path)
    assert file_path.exists()
    assert file_path.name == 'bad_python_for_ruff.py'


def test_setup_test_environment(tmp_path, setup_test_environment):
    """Test that complete environment setup works."""
    config_path, file_paths = setup_test_environment(
        'ruff_batch.yaml',
        ['bad_python_for_ruff.py'],
    )

    assert config_path.exists()
    assert len(file_paths) == 1
    assert file_paths[0].exists()


def test_run_toolbelt_help(run_toolbelt_cli):
    """Test that we can run toolbelt CLI."""
    result = run_toolbelt_cli(['--help'])

    assert result.returncode == 0
    assert 'toolbelt' in result.stdout
