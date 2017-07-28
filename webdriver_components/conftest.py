import pytest
from webdriver_components.testutils import LocalDriver


@pytest.yield_fixture
def local_driver():
    ld = LocalDriver()
    yield ld
    ld.cleanup()


