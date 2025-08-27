from toolbelt.config.defaults import get_default_config


def test_default_config() -> None:
    """Test that the default configuration is loaded correctly."""
    config = get_default_config()

    # The default config now loads all profiles from hdw.yaml and its includes
    assert 'python' in config.list_profiles()
    python_profile = config.get_profile('python')
    assert python_profile is not None
    assert python_profile.name == 'python'
    assert '.py' in python_profile.extensions
