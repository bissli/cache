"""Flexible caching library built on dogpile.cache.
"""
from .cache import clear_filecache, clear_memorycache, clear_rediscache
from .cache import filecache, memorycache, rediscache
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
]
