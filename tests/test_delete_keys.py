"""Test deleting specific cache keys by parameters.
"""
import cache
import pytest


def test_delete_memorycache_key_basic():
    """Verify deleting a specific memory cache key removes only that entry.
    """
    call_count = 0

    @cache.memorycache(seconds=300).cache_on_arguments(namespace='users')
    def get_user(user_id: int) -> dict:
        nonlocal call_count
        call_count += 1
        return {'id': user_id, 'name': f'user_{user_id}'}

    result1 = get_user(123)
    result2 = get_user(456)
    assert call_count == 2

    result3 = get_user(123)
    result4 = get_user(456)
    assert call_count == 2

    cache.delete_memorycache_key(300, 'users', get_user, user_id=123)

    result5 = get_user(123)
    assert call_count == 3

    result6 = get_user(456)
    assert call_count == 3


def test_delete_memorycache_key_with_multiple_params():
    """Verify deleting cache key with multiple parameters.
    """
    call_count = 0

    @cache.memorycache(seconds=300).cache_on_arguments(namespace='data')
    def get_data(user_id: int, key: str) -> dict:
        nonlocal call_count
        call_count += 1
        return {'user_id': user_id, 'key': key, 'value': 'data'}

    get_data(123, 'profile')
    get_data(123, 'settings')
    get_data(456, 'profile')
    assert call_count == 3

    get_data(123, 'profile')
    get_data(123, 'settings')
    get_data(456, 'profile')
    assert call_count == 3

    cache.delete_memorycache_key(300, 'data', get_data, user_id=123, key='profile')

    get_data(123, 'profile')
    assert call_count == 4

    get_data(123, 'settings')
    get_data(456, 'profile')
    assert call_count == 4


def test_delete_memorycache_key_with_defaults():
    """Verify deleting cache key works with default parameter values.
    """
    call_count = 0

    @cache.memorycache(seconds=300).cache_on_arguments(namespace='api')
    def fetch_data(resource: str, latest: bool = False) -> dict:
        nonlocal call_count
        call_count += 1
        return {'resource': resource, 'latest': latest, 'data': 'value'}

    fetch_data('users', latest=True)
    fetch_data('users', latest=False)
    fetch_data('users')
    assert call_count == 2

    cache.delete_memorycache_key(300, 'api', fetch_data, resource='users', latest=True)

    fetch_data('users', latest=True)
    assert call_count == 3

    fetch_data('users', latest=False)
    fetch_data('users')
    assert call_count == 3


def test_delete_filecache_key_basic(temp_cache_dir):
    """Verify deleting a specific file cache key removes only that entry.
    """
    call_count = 0

    @cache.filecache(seconds=300).cache_on_arguments(namespace='reports')
    def generate_report(report_id: int) -> dict:
        nonlocal call_count
        call_count += 1
        return {'id': report_id, 'data': 'report_data'}

    generate_report(100)
    generate_report(200)
    assert call_count == 2

    generate_report(100)
    generate_report(200)
    assert call_count == 2

    cache.delete_filecache_key(300, 'reports', generate_report, report_id=100)

    generate_report(100)
    assert call_count == 3

    generate_report(200)
    assert call_count == 3


def test_delete_filecache_key_multiple_params(temp_cache_dir):
    """Verify deleting file cache key with multiple parameters.
    """
    call_count = 0

    @cache.filecache(seconds=300).cache_on_arguments(namespace='analytics')
    def get_analytics(user_id: int, metric: str, period: str) -> dict:
        nonlocal call_count
        call_count += 1
        return {'user_id': user_id, 'metric': metric, 'period': period}

    get_analytics(123, 'views', 'daily')
    get_analytics(123, 'views', 'weekly')
    get_analytics(456, 'views', 'daily')
    assert call_count == 3

    cache.delete_filecache_key(300, 'analytics', get_analytics,
                               user_id=123, metric='views', period='daily')

    get_analytics(123, 'views', 'daily')
    assert call_count == 4

    get_analytics(123, 'views', 'weekly')
    get_analytics(456, 'views', 'daily')
    assert call_count == 4


@pytest.mark.redis
def test_delete_rediscache_key_basic(redis_docker):
    """Verify deleting a specific redis cache key removes only that entry.
    """
    call_count = 0

    @cache.rediscache(seconds=300).cache_on_arguments(namespace='products')
    def get_product(product_id: int) -> dict:
        nonlocal call_count
        call_count += 1
        return {'id': product_id, 'name': f'product_{product_id}'}

    get_product(100)
    get_product(200)
    assert call_count == 2

    get_product(100)
    get_product(200)
    assert call_count == 2

    cache.delete_rediscache_key(300, 'products', get_product, product_id=100)

    get_product(100)
    assert call_count == 3

    get_product(200)
    assert call_count == 3


@pytest.mark.redis
def test_delete_rediscache_key_use_case(redis_docker):
    """Verify the original use case from the requirements works correctly.
    """
    call_count = 0

    @cache.rediscache(seconds=86400).cache_on_arguments(namespace='target')
    def get_target(latest: bool = False, inst_id: int = None,
                   target_id: int = None, key: str = None) -> dict:
        nonlocal call_count
        call_count += 1
        return {
            'latest': latest,
            'inst_id': inst_id,
            'target_id': target_id,
            'key': key,
            'data': 'target_data'
        }

    get_target(latest=True, inst_id=123)
    get_target(target_id=456, key='main')
    assert call_count == 2

    get_target(latest=True, inst_id=123)
    get_target(target_id=456, key='main')
    assert call_count == 2

    def _reset_cache_keys(inst_id, target_id, key):
        cache.delete_rediscache_key(86400, 'target', get_target,
                                    latest=True, inst_id=inst_id)
        cache.delete_rediscache_key(86400, 'target', get_target,
                                    target_id=target_id, key=key)

    _reset_cache_keys(123, 456, 'main')

    get_target(latest=True, inst_id=123)
    assert call_count == 3

    get_target(target_id=456, key='main')
    assert call_count == 4


@pytest.mark.redis
def test_delete_rediscache_key_multiple_params(redis_docker):
    """Verify deleting redis cache key with multiple parameters.
    """
    call_count = 0

    @cache.rediscache(seconds=300).cache_on_arguments(namespace='orders')
    def get_order(user_id: int, order_id: int, status: str) -> dict:
        nonlocal call_count
        call_count += 1
        return {'user_id': user_id, 'order_id': order_id, 'status': status}

    get_order(123, 789, 'pending')
    get_order(123, 789, 'completed')
    get_order(456, 789, 'pending')
    assert call_count == 3

    cache.delete_rediscache_key(300, 'orders', get_order,
                                user_id=123, order_id=789, status='pending')

    get_order(123, 789, 'pending')
    assert call_count == 4

    get_order(123, 789, 'completed')
    get_order(456, 789, 'pending')
    assert call_count == 4
