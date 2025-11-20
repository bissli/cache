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


@pytest.mark.parametrize(('cache_type', 'set_func', 'fixture'), [
    ('file', cache.set_filecache_key, 'temp_cache_dir'),
    ('redis', cache.set_rediscache_key, 'redis_docker'),
])
def test_set_cache_key_basic(cache_type, set_func, fixture, request):
    """Verify setting a specific cache key updates the cached value.
    """
    if cache_type == 'redis':
        pytest.importorskip('redis')
    request.getfixturevalue(fixture)

    call_count = 0
    cache_func = cache.filecache if cache_type == 'file' else cache.rediscache

    @cache_func(seconds=300).cache_on_arguments(namespace='items')
    def get_item(item_id: int) -> dict:
        nonlocal call_count
        call_count += 1
        return {'id': item_id, 'data': 'original_data'}

    get_item(100)
    assert call_count == 1

    set_func(300, 'items', get_item, {'id': 100, 'data': 'updated_data'}, item_id=100)

    result = get_item(100)
    assert result['data'] == 'updated_data'
    assert call_count == 1


@pytest.mark.parametrize(('cache_type', 'set_func', 'fixture'), [
    ('file', cache.set_filecache_key, 'temp_cache_dir'),
    ('redis', cache.set_rediscache_key, 'redis_docker'),
])
def test_set_cache_key_multiple_params(cache_type, set_func, fixture, request):
    """Verify setting cache key with multiple parameters.
    """
    if cache_type == 'redis':
        pytest.importorskip('redis')
    request.getfixturevalue(fixture)

    call_count = 0
    cache_func = cache.filecache if cache_type == 'file' else cache.rediscache

    @cache_func(seconds=300).cache_on_arguments(namespace='data')
    def get_data(user_id: int, metric: str, period: str) -> dict:
        nonlocal call_count
        call_count += 1
        return {'user_id': user_id, 'metric': metric, 'period': period, 'value': 'original'}

    get_data(123, 'views', 'daily')
    get_data(123, 'views', 'weekly')
    assert call_count == 2

    set_func(300, 'data', get_data, {'user_id': 123, 'metric': 'views', 'period': 'daily', 'value': 'updated'}, user_id=123, metric='views', period='daily')

    result = get_data(123, 'views', 'daily')
    assert result['value'] == 'updated'
    assert call_count == 2

    result = get_data(123, 'views', 'weekly')
    assert result['value'] == 'original'
    assert call_count == 2


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
