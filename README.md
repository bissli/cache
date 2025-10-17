# cache

Flexible caching library built on dogpile.cache with support for memory, file, and Redis backends.

## Installation

```bash
poetry add git+https://github.com/bissli/cache.git
```

For Redis support:

```bash
poetry add git+https://github.com/bissli/cache.git -E redis
```

## Configuration

Configure the cache settings at application startup:

```python
import cache

cache.configure(
    debug_key="v1:",
    memory="dogpile.cache.memory",
    redis="dogpile.cache.redis",
    redis_host="localhost",
    redis_port=6379,
    redis_db=0,
    redis_ssl=False,
    redis_distributed=False,
    tmpdir="/var/cache/myapp"
)
```

Available configuration options:
- `debug_key`: Prefix for cache keys (default: "")
- `memory`: Backend for memory cache (default: "dogpile.cache.memory")
- `redis`: Backend for redis cache (default: "dogpile.cache.redis")
- `redis_host`: Redis server hostname (default: "localhost")
- `redis_port`: Redis server port (default: 6379)
- `redis_db`: Redis database number (default: 0)
- `redis_ssl`: Use SSL for Redis connection (default: False)
- `redis_distributed`: Use distributed locks for Redis (default: False)
- `tmpdir`: Directory for file-based caches (default: "/tmp")

## Usage

### Memory Cache

```python
from cache import memorycache

@memorycache(seconds=300).cache_on_arguments()
def expensive_operation(param):
    # ... expensive computation
    return result
```

### File Cache

```python
from cache import filecache

@filecache(seconds=3600).cache_on_arguments()
def load_data(filename):
    # ... load and process file
    return data
```

### Redis Cache

```python
from cache import rediscache

@rediscache(seconds=86400).cache_on_arguments()
def fetch_external_data(api_key):
    # ... call external API
    return response
```

### Namespaces

Namespaces allow you to organize cache keys into logical groups that can be selectively cleared without affecting other cached data. This is particularly useful when you need to invalidate related data together.

**Using namespaces with decorators:**

```python
from cache import memorycache, rediscache

# Group user-related caches
@memorycache(seconds=300).cache_on_arguments(namespace="users")
def get_user_profile(user_id):
    return fetch_user_from_db(user_id)

@memorycache(seconds=300).cache_on_arguments(namespace="users")
def get_user_permissions(user_id):
    return fetch_permissions_from_db(user_id)

# Group API data caches
@rediscache(seconds=3600).cache_on_arguments(namespace="api_data")
def fetch_weather(city):
    return call_weather_api(city)

@rediscache(seconds=3600).cache_on_arguments(namespace="api_data")
def fetch_stock_price(symbol):
    return call_stock_api(symbol)
```

**Clearing by namespace:**

```python
from cache import clear_memorycache, clear_rediscache

# Clear all user-related caches without affecting other data
clear_memorycache(seconds=300, namespace="users")

# Clear all API data caches
clear_rediscache(seconds=3600, namespace="api_data")

# Clear entire region (all namespaces)
clear_memorycache(seconds=300)
```

**Best practices:**

- Use descriptive namespace names that reflect the data domain (e.g., "users", "products", "reports")
- Group related functions under the same namespace for coordinated cache invalidation
- Keep namespace names consistent across your application
- Consider using hierarchical naming for complex applications (e.g., "api:weather", "api:stocks")

### Clearing Caches

```python
from cache import clear_memorycache, clear_filecache, clear_rediscache

# Clear entire region (all cached data for a given TTL)
clear_memorycache(seconds=300)
clear_filecache(seconds=3600)
clear_rediscache(seconds=86400)

# Clear specific namespace only
clear_memorycache(seconds=300, namespace="users")
clear_filecache(seconds=3600, namespace="reports")
clear_rediscache(seconds=86400, namespace="api_data")
```

## Features

- **Multiple backends**: Memory, file (DBM), and Redis
- **Flexible expiration**: Configure different TTLs for different use cases
- **Namespace support**: Organize cache keys and selectively clear regions
- **Database connection filtering**: Automatically excludes database connections from cache keys
- **Custom key generation**: Intelligent key generation based on function signatures
