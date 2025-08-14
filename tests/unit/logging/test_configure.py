import logging
from dataclasses import dataclass

import pytest
import structlog
from pytest_mock import MockerFixture

from toolbelt.logging import configure_logging, get_logger


@pytest.fixture(autouse=True)
def reset_structlog():
    structlog.reset_defaults()
    yield
    structlog.reset_defaults()


@dataclass
class LoggingTestCase:
    verbose: bool
    expected_level: int


@pytest.mark.parametrize(
    'tcase',
    [
        LoggingTestCase(verbose=True, expected_level=logging.DEBUG),
        LoggingTestCase(verbose=False, expected_level=logging.INFO),
    ],
)
def test_configure_logging_levels(
    mocker: MockerFixture,
    tcase: LoggingTestCase,
):
    """Test configure_logging sets correct log levels based on verbose flag."""
    mock_configure = mocker.patch('structlog.configure')
    mock_basic_config = mocker.patch('logging.basicConfig')

    configure_logging(verbose=tcase.verbose)

    mock_configure.assert_called_once()
    mock_basic_config.assert_called_once_with(
        level=tcase.expected_level,
        handlers=[],
    )


def test_configure_logging_idempotent():
    # Should not raise or misbehave if called multiple times
    configure_logging()
    configure_logging()
    logger = get_logger('repeat.module')
    assert logger is not None
    assert hasattr(logger, 'info')


def test_get_logger_returns_structlog_logger():
    logger = get_logger('my.module')
    # Should be a structlog logger (BoundLogger or FilteringBoundLogger)
    assert hasattr(logger, 'info')
    assert hasattr(logger, 'bind')
    assert callable(logger.info)
    assert callable(logger.bind)
