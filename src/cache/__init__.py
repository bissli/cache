"""Flexible caching library built on dogpile.cache.
"""
from .cache import clear_filecache, clear_memorycache, clear_rediscache
from .cache import delete_filecache_key, delete_memorycache_key
from .cache import delete_rediscache_key, filecache, memorycache, rediscache
from .config import configure, get_config

__all__ = [
    'configure',
    'get_config',
    'memorycache',
    'filecache',
    'rediscache',
    'clear_memorycache',
    'clear_filecache',
    'clear_rediscache',
    'delete_memorycache_key',
    'delete_filecache_key',
    'delete_rediscache_key',
]
