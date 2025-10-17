"""Test cache configuration.
"""
import cache
import pytest


def test_default_configuration():
    """Verify default configuration values are set correctly.
    """
    config = cache.get_config()
    assert config.memory == 'dogpile.cache.memory'
    assert config.redis == 'dogpile.cache.redis'
    assert config.tmpdir == '/tmp'


def test_configure_updates_settings():
    """Verify configure() updates global configuration.
    """
    cache.configure(debug_key='v2:', tmpdir='/var/cache')
    config = cache.get_config()
    assert config.debug_key == 'v2:'
    assert config.tmpdir == '/var/cache'


def test_configure_rejects_invalid_keys():
    """Verify configure() raises error for unknown configuration keys.
    """
    with pytest.raises(ValueError, match='Unknown configuration key'):
        cache.configure(invalid_key='value')


def test_configure_redis_settings():
    """Verify Redis-specific configuration can be updated.
    """
    cache.configure(
        redis_host='redis.example.com',
        redis_port=6380,
        redis_db=1,
        redis_ssl=True,
        redis_distributed=True
    )
    config = cache.get_config()
    assert config.redis_host == 'redis.example.com'
    assert config.redis_port == 6380
    assert config.redis_db == 1
    assert config.redis_ssl is True
    assert config.redis_distributed is True
