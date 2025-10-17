import dbm
import inspect
import logging
import os
import pathlib
from collections.abc import Callable
from functools import partial, wraps
from typing import Any

from dogpile.cache import CacheRegion, make_region
from dogpile.cache.backends.file import AbstractFileLock
from dogpile.cache.region import DefaultInvalidationStrategy
from dogpile.util.readwrite_lock import ReadWriteMutex
from func_timeout import func_timeout

from .config import get_config

logger = logging.getLogger(__name__)


def _is_connection_like(obj) -> bool:
    """Check if object appears to be a database connection.

    Uses heuristics to detect common database connection objects without
    requiring database library imports.
    """
    if hasattr(obj, 'driver_connection'):
        return True

    if hasattr(obj, 'dialect'):
        return True

    if hasattr(obj, 'engine'):
        return True

    obj_type = str(type(obj))
    connection_indicators = ('Connection', 'Engine', 'psycopg', 'pyodbc', 'sqlite3')

    return any(indicator in obj_type for indicator in connection_indicators)


def _normalize_namespace(namespace: str) -> str:
    """Normalize namespace to always be wrapped in pipes.

    Parameters
        namespace: The namespace string to normalize.

    Returns
        The namespace wrapped in pipes on both sides (e.g., |foo|).
    """
    if not namespace:
        return ''
    namespace = namespace.strip('|')
    namespace = namespace.replace('|', '.')
    return f'|{namespace}|'


def _create_namespace_filter(namespace: str) -> Callable[[str], bool]:
    """Create a filter function for namespace-based key matching.

    Parameters
        namespace: The namespace to filter by.

    Returns
        A function that returns True if a key matches the namespace.
    """
    _config = get_config()
    debug_prefix = _config.debug_key
    normalized_ns = _normalize_namespace(namespace)
    namespace_pattern = f'|{normalized_ns}|'

    def matches_namespace(key: str) -> bool:
        if not key.startswith(debug_prefix):
            return False
        key_after_prefix = key[len(debug_prefix):]
        return namespace_pattern in key_after_prefix

    return matches_namespace


def key_generator(namespace: str, fn: Callable[..., Any]) -> Callable[..., str]:
    """Generate a cache key for the given namespace and function.

    This function uses the provided function's argument specification to generate
    a unique cache key based on the arguments passed to the function.

    Parameters
        namespace: A string to be prefixed to the key. Can be empty.
        fn: The function for which the key is being generated.

    Returns
        A callable that generates a cache key string from the function's arguments.
    """
    namespace = f'{fn.__name__}|{_normalize_namespace(namespace)}' if namespace else f'{fn.__name__}'

    argspec = inspect.getfullargspec(fn)
    _args_reversed = list(reversed(argspec.args or []))
    _defaults_reversed = list(reversed(argspec.defaults or []))
    args_with_defaults = { _args_reversed[i]: default for i, default in enumerate(_defaults_reversed)}

    def generate_key(*args, **kwargs):
        args, vargs = args[:len(argspec.args)], args[len(argspec.args):]
        as_kwargs = dict(**args_with_defaults)
        as_kwargs.update(dict(zip(argspec.args, args)))
        as_kwargs.update({f'vararg{i+1}': varg for i, varg in enumerate(vargs)})
        as_kwargs.update(**kwargs)
        as_kwargs = {k: v for k, v in as_kwargs.items() if not _is_connection_like(v) and k not in {'self', 'cls'}}
        as_kwargs = {k: v for k, v in as_kwargs.items() if not k.startswith('_')}
        as_str = ' '.join(f'{str(k)}={str(v)}' for k, v in sorted(as_kwargs.items()))
        return f'{namespace}|{as_str}'

    return generate_key


def key_mangler_default(key: str) -> str:
    """Modify the key for debugging purposes by prefixing it with a debug marker.

    Parameters
        key: The original cache key.

    Returns
        A modified cache key with the debug marker prepended.
    """
    _config = get_config()
    return f'{_config.debug_key}{key}'


def key_mangler_region(key: str, region: str) -> str:
    """Modify the key for a specific region for debugging purposes.

    Parameters
        key: The original cache key.
        region: The cache region name.

    Returns
        A modified cache key that includes the region prefix and debug marker.
    """
    _config = get_config()
    return f'{region}:{_config.debug_key}{key}'


def should_cache_fn(value: Any) -> bool:
    """Determine if the given value should be cached.

    Parameters
        value: The value to evaluate for caching.

    Returns
        True if the value should be cached, False otherwise.
    """
    return bool(value)


def _wrap_cache_on_arguments(region: CacheRegion) -> CacheRegion:
    """Wrap the `cache_on_arguments` method of a CacheRegion instance to inject a default should_cache_fn.

    Parameters
        region: A dogpile.cache.CacheRegion instance to wrap.

    Returns
        The wrapped CacheRegion instance with an updated cache_on_arguments method.
    """
    original_cache_on_arguments = region.cache_on_arguments

    def cache_on_arguments_with_default(namespace: str = '', should_cache_fn: Callable[[Any], bool] = should_cache_fn, **kwargs):
        return original_cache_on_arguments(namespace=namespace, should_cache_fn=should_cache_fn, **kwargs)

    region.cache_on_arguments = cache_on_arguments_with_default
    return region


class CustomFileLock(AbstractFileLock):
    """Implementation of a file lock using a read-write mutex.

    Note:
        This implementation may be replaced with portalocker in the future.
    """
    def __init__(self, filename: str) -> None:
        self.mutex = ReadWriteMutex()

    def acquire_read_lock(self, wait: bool) -> bool:
        """Acquire the read lock.

        Parameters
            wait: Flag indicating whether to wait for the lock.

        Returns
            True if the lock is acquired, False otherwise.
        """
        ret = self.mutex.acquire_read_lock(wait)
        return wait or ret

    def acquire_write_lock(self, wait: bool) -> bool:
        """Acquire the write lock.

        Parameters
            wait: Flag indicating whether to wait for the lock.

        Returns
            True if the lock is acquired, False otherwise.
        """
        ret = self.mutex.acquire_write_lock(wait)
        return wait or ret

    def release_read_lock(self) -> bool:
        """Release the read lock.

        Returns
            True if the lock is released successfully.
        """
        return self.mutex.release_read_lock()

    def release_write_lock(self) -> bool:
        """Release the write lock.

        Returns
            True if the lock is released successfully.
        """
        return self.mutex.release_write_lock()


class RedisInvalidator(DefaultInvalidationStrategy):

    def __init__(self, region: CacheRegion, delete_keys: bool = False) -> None:
        """Initialize the RedisInvalidator for a given CacheRegion.

        Parameters
            region: A dogpile.cache.CacheRegion instance that will be invalidated.
            delete_keys: If True, physically delete keys from Redis on invalidation.
                        If False, rely on timestamp-based invalidation only.
        """
        self.region = region
        self.delete_keys = delete_keys
        super().__init__()

    def invalidate(self, hard: bool = True) -> None:
        """Invalidate the cache region using timestamp-based invalidation.

        Parameters
            hard: If True, perform a hard invalidation.
        """
        super().invalidate(hard)
        if self.delete_keys:
            self._delete_backend_keys()

    def _delete_backend_keys(self) -> None:
        """Delete keys from Redis backend for this region.
        """
        client = self.region.backend.writer_client
        region_prefix = f'{self.region.name}:'
        deleted_count = 0
        for key in client.scan_iter(match=f'{region_prefix}*'):
            client.delete(key)
            deleted_count += 1
        logger.debug(f'Deleted {deleted_count} Redis keys for region "{self.region.name}"')


def _handle_all_regions(regions_dict: dict, log_level: str = 'warning'):
    """Decorator to handle clearing all cache regions when seconds=None.

    When seconds=None, iterates through all regions in the dictionary and calls
    the decorated function for each one. Otherwise passes through to the
    original function.

    Parameters
        regions_dict: Dictionary of cache regions keyed by seconds
        log_level: Logging level to use when no regions exist (default 'warning')

    Returns
        Decorator function that wraps cache clearing functions
    """
    def decorator(func):
        @wraps(func)
        def wrapper(seconds: int = None, namespace: str = None) -> None:
            if seconds is None:
                regions_to_clear = list(regions_dict.keys())
                if not regions_to_clear:
                    log_func = getattr(logger, log_level)
                    cache_type = func.__name__.replace('clear_', '').replace('cache', ' cache')
                    log_func(f'No{cache_type} regions exist')
                    return
                for region_seconds in regions_to_clear:
                    wrapper(region_seconds, namespace)
                return
            return func(seconds, namespace)
        return wrapper
    return decorator


_memory_cache_regions = {}


def memorycache(seconds: int) -> CacheRegion:
    """Create or retrieve a memory cache region with a specified expiration time.

    Parameters
        seconds: The expiration time in seconds for caching.

    Returns
        A configured memory cache region (dogpile.cache.CacheRegion).
    """
    if seconds not in _memory_cache_regions:
        _config = get_config()
        region = make_region(
            function_key_generator=key_generator,
            key_mangler=key_mangler_default,
        ).configure(
            _config.memory,
            expiration_time=seconds,
        )
        _memory_cache_regions[seconds] = _wrap_cache_on_arguments(region)
    return _memory_cache_regions[seconds]


_file_cache_regions = {}


def filecache(seconds: int) -> CacheRegion:
    """Create or retrieve a file cache region with a specified expiration time.

    Parameters
        seconds: The expiration time in seconds for caching.

    Returns
        A configured file cache region (dogpile.cache.CacheRegion).
    """

    if seconds < 60:
        filename = f'cache{seconds}sec'
    elif seconds < 3600:
        filename = f'cache{seconds // 60}min'
    else:
        filename = f'cache{seconds // 3600}hour'

    if seconds not in _file_cache_regions:
        _config = get_config()
        region = make_region(
            function_key_generator=key_generator,
            key_mangler=key_mangler_default,
        ).configure(
            'dogpile.cache.dbm',
            expiration_time=seconds,
            arguments={
                'filename': os.path.join(_config.tmpdir, filename),
                'lock_factory': CustomFileLock
            }
        )
        _file_cache_regions[seconds] = _wrap_cache_on_arguments(region)
    return _file_cache_regions[seconds]


_redis_cache_regions = {}


def rediscache(seconds: int) -> CacheRegion:
    """Create or retrieve a Redis cache region with a specified expiration time.

    Parameters
        seconds: The expiration time in seconds for caching.

    Returns
        A configured Redis cache region (dogpile.cache.CacheRegion).
    """
    if seconds not in _redis_cache_regions:
        _config = get_config()
        if seconds < 60:
            name = f'{seconds}s'
        elif seconds < 3600:
            name = f'{seconds // 60}m'
        elif seconds < 86400:
            name = f'{seconds // 3600}h'
        else:
            name = f'{seconds // 86400}d'

        region = make_region(name=name, function_key_generator=key_generator,
                             key_mangler=partial(key_mangler_region, region=name))

        connection_kwargs = {}
        if _config.redis_ssl:
            connection_kwargs['ssl'] = True

        region.configure(
            _config.redis,
            arguments={
                'host': _config.redis_host,
                'port': _config.redis_port,
                'db': _config.redis_db,
                'redis_expiration_time': seconds,
                'distributed_lock': _config.redis_distributed,
                'thread_local_lock': not _config.redis_distributed,
                'connection_kwargs': connection_kwargs,
            },
            region_invalidator=RedisInvalidator(region)
        )
        _redis_cache_regions[seconds] = _wrap_cache_on_arguments(region)
    return _redis_cache_regions[seconds]


@_handle_all_regions(_memory_cache_regions)
def clear_memorycache(seconds: int | None = None, namespace: str | None = None) -> None:
    """Clear a memory cache region.

    When decorated, supports seconds=None to clear all regions.

    Parameters
        seconds: Expiration time in seconds that identifies the region to clear
        namespace: Optional namespace to filter which keys to clear
    """
    if seconds not in _memory_cache_regions:
        logger.warning(f'No memory cache region exists for {seconds} seconds')
        return

    cache_dict = _memory_cache_regions[seconds].actual_backend._cache

    if namespace is None:
        cache_dict.clear()
        logger.debug(f'Cleared all memory cache keys for {seconds} second region')
    else:
        matches_namespace = _create_namespace_filter(namespace)
        keys_to_delete = [key for key in list(cache_dict.keys()) if matches_namespace(key)]
        for key in keys_to_delete:
            del cache_dict[key]
        logger.debug(f'Cleared {len(keys_to_delete)} memory cache keys for namespace "{namespace}"')


@_handle_all_regions(_file_cache_regions)
def clear_filecache(seconds: int | None = None, namespace: str | None = None) -> None:
    """Clear a file cache region.

    When decorated, supports seconds=None to clear all regions.

    Parameters
        seconds: Expiration time in seconds that identifies the region to clear
        namespace: Optional namespace to filter which keys to clear
    """
    if seconds not in _file_cache_regions:
        logger.warning(f'No file cache region exists for {seconds} seconds')
        return

    _config = get_config()
    filename = _file_cache_regions[seconds].actual_backend.filename
    basename = pathlib.Path(filename).name
    filepath = os.path.join(_config.tmpdir, basename)

    if namespace is None:
        db = dbm.open(filepath, 'n')
        db.close()
        logger.debug(f'Cleared all file cache keys for {seconds} second region')
    else:
        matches_namespace = _create_namespace_filter(namespace)
        with dbm.open(filepath, 'w') as db:
            keys_to_delete = [
                key for key in list(db.keys())
                if matches_namespace(key.decode())
            ]
            for key in keys_to_delete:
                del db[key]
        logger.debug(f'Cleared {len(keys_to_delete)} file cache keys for namespace "{namespace}"')


@_handle_all_regions(_redis_cache_regions, log_level='info')
def clear_rediscache(seconds: int | None = None, namespace: str | None = None) -> None:
    """Clear a redis cache region.

    When decorated, supports seconds=None to clear all regions.

    Parameters
        seconds: Expiration time in seconds that identifies the region to clear
        namespace: Optional namespace to filter which keys to clear
    """
    if seconds not in _redis_cache_regions:
        logger.info(f'No redis cache region exists for {seconds} seconds')
        return

    region = _redis_cache_regions[seconds]

    if namespace is None:
        func_timeout(60, region.region_invalidator.invalidate)
        logger.debug(f'Invalidated Redis cache region "{region.name}"')
    else:
        _config = get_config()
        client = region.backend.writer_client
        region_name = region.name
        debug_prefix = _config.debug_key
        region_prefix = f'{region_name}:{debug_prefix}'
        matches_namespace = _create_namespace_filter(namespace)
        deleted_count = 0
        for key in client.scan_iter(match=f'{region_prefix}*'):
            key_str = key.decode()
            key_without_region = key_str[len(region_name) + 1:]
            if matches_namespace(key_without_region):
                client.delete(key)
                deleted_count += 1
        logger.debug(f'Cleared {deleted_count} Redis cache keys for namespace "{namespace}"')


def delete_memorycache_key(seconds: int, namespace: str, fn: Callable[..., Any], **kwargs) -> None:
    """Delete a specific cached entry from memory cache.
    """
    region = memorycache(seconds)
    cache_key = key_generator(namespace, fn)(**kwargs)
    region.delete(cache_key)
    logger.debug(f'Deleted memory cache key for {fn.__name__} in namespace "{namespace}"')


def delete_filecache_key(seconds: int, namespace: str, fn: Callable[..., Any], **kwargs) -> None:
    """Delete a specific cached entry from file cache.
    """
    region = filecache(seconds)
    cache_key = key_generator(namespace, fn)(**kwargs)
    region.delete(cache_key)
    logger.debug(f'Deleted file cache key for {fn.__name__} in namespace "{namespace}"')


def delete_rediscache_key(seconds: int, namespace: str, fn: Callable[..., Any], **kwargs) -> None:
    """Delete a specific cached entry from redis cache.
    """
    region = rediscache(seconds)
    cache_key = key_generator(namespace, fn)(**kwargs)
    region.delete(cache_key)
    logger.debug(f'Deleted redis cache key for {fn.__name__} in namespace "{namespace}"')


if __name__ == '__main__':
    __import__('doctest').testmod(optionflags=4 | 8 | 32)
