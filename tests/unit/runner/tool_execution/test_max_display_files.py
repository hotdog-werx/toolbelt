import os
from unittest.mock import patch

import pytest

from toolbelt.runner.tool_execution import get_max_display_files


@pytest.mark.parametrize(
    'env_val, expected',
    [
        ('invalid', 5),
        ('10', 10),
        (None, 5),
        ('0', 0),
    ],
)
def test_get_max_display_files_parametrized(env_val: str, expected: int):
    """Parametrized test for _get_max_display_files with various env values."""
    env = {} if env_val is None else {'TOOLBELT_MAX_DISPLAY_FILES': env_val}
    with patch.dict(os.environ, env, clear=env_val is None):
        result = get_max_display_files()
        assert result == expected
