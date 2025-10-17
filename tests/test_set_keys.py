"""Test setting specific cache keys by parameters.
"""
import cache
import pytest


def test_set_memorycache_key_basic():
    """Verify setting a specific memory cache key updates the cached value.
    """
    call_count = 0

    @cache.memorycache(seconds=300).cache_on_arguments(namespace='users')
    def get_user(user_id: int) -> dict:
        nonlocal call_count
        call_count += 1
        return {'id': user_id, 'name': f'user_{user_id}'}

    result1 = get_user(123)
    assert result1 == {'id': 123, 'name': 'user_123'}
    assert call_count == 1

    result2 = get_user(123)
    assert result2 == {'id': 123, 'name': 'user_123'}
    assert call_count == 1

    cache.set_memorycache_key(300, 'users', get_user, {'id': 123, 'name': 'updated_user'}, user_id=123)

    result3 = get_user(123)
    assert result3 == {'id': 123, 'name': 'updated_user'}
    assert call_count == 1


def test_set_memorycache_key_with_multiple_params():
    """Verify setting cache key with multiple parameters.
    """
    call_count = 0

    @cache.memorycache(seconds=300).cache_on_arguments(namespace='data')
    def get_data(user_id: int, key: str) -> dict:
        nonlocal call_count
        call_count += 1
        return {'user_id': user_id, 'key': key, 'value': 'original'}

    get_data(123, 'profile')
    get_data(123, 'settings')
    assert call_count == 2

    cache.set_memorycache_key(300, 'data', get_data, {'user_id': 123, 'key': 'profile', 'value': 'updated'}, user_id=123, key='profile')

    result = get_data(123, 'profile')
    assert result['value'] == 'updated'
    assert call_count == 2

    result = get_data(123, 'settings')
    assert result['value'] == 'original'
    assert call_count == 2


def test_set_memorycache_key_with_defaults():
    """Verify setting cache key works with default parameter values.
    """
    call_count = 0

    @cache.memorycache(seconds=300).cache_on_arguments(namespace='api')
    def fetch_data(resource: str, latest: bool = False) -> dict:
        nonlocal call_count
        call_count += 1
        return {'resource': resource, 'latest': latest, 'data': 'original'}

    fetch_data('users', latest=True)
    assert call_count == 1

    cache.set_memorycache_key(300, 'api', fetch_data, {'resource': 'users', 'latest': True, 'data': 'updated'}, resource='users', latest=True)

    result = fetch_data('users', latest=True)
    assert result['data'] == 'updated'
    assert call_count == 1


def test_set_filecache_key_basic(temp_cache_dir):
    """Verify setting a specific file cache key updates the cached value.
    """
    call_count = 0

    @cache.filecache(seconds=300).cache_on_arguments(namespace='reports')
    def generate_report(report_id: int) -> dict:
        nonlocal call_count
        call_count += 1
        return {'id': report_id, 'data': 'original_report'}

    generate_report(100)
    assert call_count == 1

    cache.set_filecache_key(300, 'reports', generate_report, {'id': 100, 'data': 'updated_report'}, report_id=100)

    result = generate_report(100)
    assert result['data'] == 'updated_report'
    assert call_count == 1


def test_set_filecache_key_multiple_params(temp_cache_dir):
    """Verify setting file cache key with multiple parameters.
    """
    call_count = 0

    @cache.filecache(seconds=300).cache_on_arguments(namespace='analytics')
    def get_analytics(user_id: int, metric: str, period: str) -> dict:
        nonlocal call_count
        call_count += 1
        return {'user_id': user_id, 'metric': metric, 'period': period, 'value': 'original'}

    get_analytics(123, 'views', 'daily')
    get_analytics(123, 'views', 'weekly')
    assert call_count == 2

    cache.set_filecache_key(300, 'analytics', get_analytics, {'user_id': 123, 'metric': 'views', 'period': 'daily', 'value': 'updated'}, user_id=123, metric='views', period='daily')

    result = get_analytics(123, 'views', 'daily')
    assert result['value'] == 'updated'
    assert call_count == 2

    result = get_analytics(123, 'views', 'weekly')
    assert result['value'] == 'original'
    assert call_count == 2


@pytest.mark.redis
def test_set_rediscache_key_basic(redis_docker):
    """Verify setting a specific redis cache key updates the cached value.
    """
    call_count = 0

    @cache.rediscache(seconds=300).cache_on_arguments(namespace='products')
    def get_product(product_id: int) -> dict:
        nonlocal call_count
        call_count += 1
        return {'id': product_id, 'name': f'product_{product_id}'}

    get_product(100)
    assert call_count == 1

    cache.set_rediscache_key(300, 'products', get_product, {'id': 100, 'name': 'updated_product'}, product_id=100)

    result = get_product(100)
    assert result['name'] == 'updated_product'
    assert call_count == 1


@pytest.mark.redis
def test_set_rediscache_key_use_case(redis_docker):
    """Verify the use case of updating cache values directly.
    """
    call_count = 0

    @cache.rediscache(seconds=86400).cache_on_arguments(namespace='target')
    def get_target(latest: bool = False, inst_id: int = None, target_id: int = None, key: str = None) -> dict:
        nonlocal call_count
        call_count += 1
        return {'latest': latest, 'inst_id': inst_id, 'target_id': target_id, 'key': key, 'data': 'original_data'}

    get_target(latest=True, inst_id=123)
    get_target(target_id=456, key='main')
    assert call_count == 2

    def _update_cache_values(inst_id, target_id, key, new_value):
        cache.set_rediscache_key(86400, 'target', get_target, {'latest': True, 'inst_id': inst_id, 'target_id': None, 'key': None, 'data': new_value}, latest=True, inst_id=inst_id)
        cache.set_rediscache_key(86400, 'target', get_target, {'latest': False, 'inst_id': None, 'target_id': target_id, 'key': key, 'data': new_value}, target_id=target_id, key=key)

    _update_cache_values(123, 456, 'main', 'updated_data')

    result1 = get_target(latest=True, inst_id=123)
    assert result1['data'] == 'updated_data'
    assert call_count == 2

    result2 = get_target(target_id=456, key='main')
    assert result2['data'] == 'updated_data'
    assert call_count == 2


@pytest.mark.redis
def test_set_rediscache_key_multiple_params(redis_docker):
    """Verify setting redis cache key with multiple parameters.
    """
    call_count = 0

    @cache.rediscache(seconds=300).cache_on_arguments(namespace='orders')
    def get_order(user_id: int, order_id: int, status: str) -> dict:
        nonlocal call_count
        call_count += 1
        return {'user_id': user_id, 'order_id': order_id, 'status': status, 'data': 'original'}

    get_order(123, 789, 'pending')
    get_order(123, 789, 'completed')
    assert call_count == 2

    cache.set_rediscache_key(300, 'orders', get_order, {'user_id': 123, 'order_id': 789, 'status': 'pending', 'data': 'updated'}, user_id=123, order_id=789, status='pending')

    result = get_order(123, 789, 'pending')
    assert result['data'] == 'updated'
    assert call_count == 2

    result = get_order(123, 789, 'completed')
    assert result['data'] == 'original'
    assert call_count == 2
