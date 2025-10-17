"""Configuration module for cache backends.
"""
from dataclasses import dataclass


@dataclass
class CacheConfig:
    """Configuration for cache backends.
    """
    debug_key: str = ""
    memory: str = "dogpile.cache.memory"
    redis: str = "dogpile.cache.redis"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_distributed: bool = False
    redis_ssl: bool = False
    tmpdir: str = "/tmp"


_config = CacheConfig()


def get_config() -> CacheConfig:
    """Get the current global configuration.
    """
    return _config


def configure(**kwargs) -> None:
    """Configure cache settings globally.

    Args:
        debug_key: Prefix for cache keys (default: "")
        memory: Backend for memory cache (default: "dogpile.cache.memory")
        redis: Backend for redis cache (default: "dogpile.cache.redis")
        redis_host: Redis server hostname (default: "localhost")
        redis_port: Redis server port (default: 6379)
        redis_db: Redis database number (default: 0)
        redis_distributed: Use distributed locks for Redis (default: False)
        redis_ssl: Use SSL for Redis connection (default: False)
        tmpdir: Directory for file-based caches (default: "/tmp")
    """
    for key, value in kwargs.items():
        if hasattr(_config, key):
            setattr(_config, key, value)
        else:
            raise ValueError(f'Unknown configuration key: {key}')
