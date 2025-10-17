"""Test Redis cache backend operations.
"""
import cache
import pytest

pytestmark = pytest.mark.redis


def test_redis_cache_basic_decoration(redis_docker):
    """Verify Redis cache decorator caches function results.
    """
    call_count = 0

    @cache.rediscache(seconds=300).cache_on_arguments()
    def expensive_func(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    result1 = expensive_func(5)
    result2 = expensive_func(5)

    assert result1 == 10
    assert result2 == 10
    assert call_count == 1


def test_redis_cache_naming_convention(redis_docker):
    """Verify Redis cache uses correct naming convention for regions.
    """
    @cache.rediscache(seconds=30).cache_on_arguments()
    def func1(x: int) -> int:
        return x

    @cache.rediscache(seconds=120).cache_on_arguments()
    def func2(x: int) -> int:
        return x

    @cache.rediscache(seconds=7200).cache_on_arguments()
    def func3(x: int) -> int:
        return x

    @cache.rediscache(seconds=172800).cache_on_arguments()
    def func4(x: int) -> int:
        return x

    func1(1)
    func2(2)
    func3(3)
    func4(4)

    region30 = cache.cache._redis_cache_regions[30]
    region120 = cache.cache._redis_cache_regions[120]
    region7200 = cache.cache._redis_cache_regions[7200]
    region172800 = cache.cache._redis_cache_regions[172800]

    assert region30.name == '30s'
    assert region120.name == '2m'
    assert region7200.name == '2h'
    assert region172800.name == '2d'


def test_redis_cache_with_namespace(redis_docker):
    """Verify Redis cache namespace parameter is accepted.
    """
    @cache.rediscache(seconds=300).cache_on_arguments(namespace='users')
    def get_user(user_id: int) -> dict:
        return {'id': user_id, 'name': 'test'}

    result = get_user(123)
    assert result['id'] == 123


def test_redis_cache_distributed_lock_configuration(redis_docker):
    """Verify Redis cache respects distributed lock configuration.
    """
    cache.configure(redis_distributed=True)

    @cache.rediscache(seconds=300).cache_on_arguments()
    def func(x: int) -> int:
        return x * 2

    func(5)

    region = cache.cache._redis_cache_regions[300]
    assert hasattr(region.backend, 'distributed_lock')
    assert region.backend.distributed_lock is True
