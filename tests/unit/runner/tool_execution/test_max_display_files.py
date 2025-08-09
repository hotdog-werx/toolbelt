import os
from dataclasses import dataclass
from unittest.mock import patch

import pytest

from toolbelt.runner.tool_execution import get_max_display_files


@dataclass
class MaxDisplayFilesCase:
    env_value: str | None
    expected: int


@pytest.mark.parametrize(
    'case',
    [
        MaxDisplayFilesCase(env_value='invalid', expected=5),
        MaxDisplayFilesCase(env_value='10', expected=10),
        MaxDisplayFilesCase(env_value=None, expected=5),
        MaxDisplayFilesCase(env_value='0', expected=0),
    ],
)
def test_get_max_display_files_parametrized(case: MaxDisplayFilesCase):
    """Parametrized test for _get_max_display_files with various env values."""
    env_val = case.env_value
    env = {} if env_val is None else {'TOOLBELT_MAX_DISPLAY_FILES': env_val}
    with patch.dict(os.environ, env, clear=env_val is None):
        result = get_max_display_files()
        assert result == case.expected
