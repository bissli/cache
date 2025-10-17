"""Flexible caching library built on dogpile.cache.
"""
from .cache import clear_filecache, clear_memorycache, clear_rediscache
from .cache import delete_filecache_key, delete_memorycache_key
from .cache import delete_rediscache_key, filecache, memorycache, rediscache
from .cache import set_filecache_key, set_memorycache_key, set_rediscache_key
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
    'set_memorycache_key',
    'set_filecache_key',
    'set_rediscache_key',
    'delete_memorycache_key',
    'delete_filecache_key',
    'delete_rediscache_key',
]
