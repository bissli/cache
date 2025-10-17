"""Test file cache backend operations.
"""
import os

import cache
import pathlib


def test_file_cache_basic_decoration(temp_cache_dir):
    """Verify file cache decorator caches function results.
    """
    call_count = 0

    @cache.filecache(seconds=300).cache_on_arguments()
    def expensive_func(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    result1 = expensive_func(5)
    result2 = expensive_func(5)

    assert result1 == 10
    assert result2 == 10
    assert call_count == 1


def test_file_cache_creates_dbm_file(temp_cache_dir):
    """Verify file cache creates DBM file in configured directory.
    """
    @cache.filecache(seconds=300).cache_on_arguments()
    def func(x: int) -> int:
        return x * 2

    func(5)

    cache_files = [f for f in os.listdir(temp_cache_dir) if f.startswith('cache')]
    assert len(cache_files) > 0


def test_file_cache_naming_convention():
    """Verify file cache uses correct naming convention for different expiration times.
    """
    @cache.filecache(seconds=30).cache_on_arguments()
    def func1(x: int) -> int:
        return x

    @cache.filecache(seconds=120).cache_on_arguments()
    def func2(x: int) -> int:
        return x

    @cache.filecache(seconds=7200).cache_on_arguments()
    def func3(x: int) -> int:
        return x

    func1(1)
    func2(2)
    func3(3)

    region30 = cache.cache._file_cache_regions[30]
    region120 = cache.cache._file_cache_regions[120]
    region7200 = cache.cache._file_cache_regions[7200]

    assert 'cache30sec' in region30.actual_backend.filename
    assert 'cache2min' in region120.actual_backend.filename
    assert 'cache2hour' in region7200.actual_backend.filename


def test_file_cache_persists_across_region_recreation(temp_cache_dir):
    """Verify file cache DBM file persists when region is deleted.
    """
    @cache.filecache(seconds=300).cache_on_arguments()
    def func(x: int) -> int:
        return x * 2

    func(5)

    region = cache.cache._file_cache_regions[300]
    cache_file = region.actual_backend.filename

    assert pathlib.Path(cache_file).exists() or any(
        pathlib.Path(f'{cache_file}{ext}').exists()
        for ext in ['.db', '.dat', '.bak', '.dir']
    )

    del cache.cache._file_cache_regions[300]

    assert pathlib.Path(cache_file).exists() or any(
        pathlib.Path(f'{cache_file}{ext}').exists()
        for ext in ['.db', '.dat', '.bak', '.dir']
    )


def test_file_cache_with_namespace(temp_cache_dir):
    """Verify file cache namespace parameter is accepted.
    """
    @cache.filecache(seconds=300).cache_on_arguments(namespace='users')
    def get_user(user_id: int) -> dict:
        return {'id': user_id, 'name': 'test'}

    result = get_user(123)
    assert result['id'] == 123
