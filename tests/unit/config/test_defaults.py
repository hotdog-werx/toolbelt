from toolbelt.config.defaults import get_default_config


def test_default_config() -> None:
    """Test that the default configuration is loaded correctly."""
    config = get_default_config()

    assert config.list_profiles() == ['python']
    python_profile = config.get_profile('python')
    assert python_profile is not None
    assert python_profile.name == 'python'
    assert python_profile.extensions == ['.py']
    assert len(python_profile.check_tools) == 1
    assert python_profile.check_tools[0].name == 'ruff-check'
