"""Shared fixtures for cache tests.
"""
import logging
import pathlib
import shutil
import site
import tempfile

import cache
import pytest

logger = logging.getLogger(__name__)

HERE = pathlib.Path(pathlib.Path(__file__).resolve()).parent
site.addsitedir(HERE)


@pytest.fixture(autouse=True)
def reset_cache_config():
    """Reset cache configuration and clear cache regions before each test.
    """
    cache.cache._memory_cache_regions.clear()
    cache.cache._file_cache_regions.clear()
    cache.cache._redis_cache_regions.clear()
    cache.configure(
        debug_key='test:',
        tmpdir=tempfile.gettempdir(),
        redis_host='localhost',
        redis_port=6379,
        redis_db=0,
        redis_ssl=False,
        redis_distributed=False
    )
    yield
    cache.cache._memory_cache_regions.clear()
    cache.cache._file_cache_regions.clear()
    cache.cache._redis_cache_regions.clear()
    cache.configure(
        debug_key='',
        tmpdir='/tmp',
        redis_host='localhost',
        redis_port=6379,
        redis_db=0,
        redis_ssl=False,
        redis_distributed=False
    )


@pytest.fixture
def temp_cache_dir():
    """Provide a temporary directory for file cache tests.
    """
    temp_dir = tempfile.mkdtemp(prefix='cache_test_')
    cache.configure(tmpdir=temp_dir)
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_function():
    """Provide a simple function for cache testing.
    """
    def compute(x: int, y: int) -> int:
        return x + y
    return compute


pytest_plugins = [
    'fixtures.redis',
]
