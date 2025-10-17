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

Namespaces organize cache keys into logical groups that can be selectively cleared:

```python
from cache import memorycache, rediscache

# Group related caches by namespace
@memorycache(seconds=300).cache_on_arguments(namespace="users")
def get_user_profile(user_id):
    return fetch_user_from_db(user_id)

@rediscache(seconds=3600).cache_on_arguments(namespace="api_data")
def fetch_weather(city):
    return call_weather_api(city)

# Clear specific namespace without affecting other cached data
clear_memorycache(seconds=300, namespace="users")
clear_rediscache(seconds=3600, namespace="api_data")
```

### Clearing Caches

Clear caches using optional `seconds` and `namespace` parameters:

```python
from cache import clear_memorycache, clear_filecache, clear_rediscache

# Clear specific region
clear_memorycache(seconds=300)
clear_filecache(seconds=3600)
clear_rediscache(seconds=86400)

# Clear specific namespace in a region
clear_memorycache(seconds=300, namespace="users")

# Clear all regions
clear_memorycache()

# Clear namespace across all regions
clear_memorycache(namespace="users")
```

**Clearing behavior:**

| seconds   | namespace   | Behavior                                                    |
| --------- | ----------- | ----------                                                  |
| `300`     | `None`      | Clears all keys in the 300-second region                    |
| `300`     | `"users"`   | Clears only "users" namespace keys in the 300-second region |
| `None`    | `None`      | Clears all keys in all regions                              |
| `None`    | `"users"`   | Clears "users" namespace keys across all regions            |

## Intelligent Parameter Filtering

The library automatically filters out implementation details from cache keys, ensuring keys are based only on meaningful data parameters:

**Automatic filtering:**
- `self` and `cls` parameters (for instance and class methods)
- Database connection objects (detected by `database.isconnection()`)
- Parameters starting with underscore (`_`)

**Instance methods:**

```python
from cache import memorycache

class UserRepository:
    def __init__(self, db_connection):
        self.conn = db_connection

    @memorycache(seconds=300).cache_on_arguments()
    def get_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return cursor.fetchone()

# Both calls use the same cache entry (keyed only by user_id)
repo1 = UserRepository(connection1)
repo2 = UserRepository(connection2)
result = repo1.get_user(123)  # Cached
result = repo2.get_user(123)  # Cache hit
```

**Database connections:**

```python
@memorycache(seconds=300).cache_on_arguments()
def get_user_data(conn, user_id):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cursor.fetchone()

# Both calls use the same cache entry (keyed only by user_id)
result = get_user_data(connection1, 123)  # Cached
result = get_user_data(connection2, 123)  # Cache hit
```

## Features

- **Multiple backends**: Memory, file (DBM), and Redis support
- **Flexible expiration**: Configure different TTLs for different use cases
- **Namespace support**: Organize and selectively clear cache regions
- **Intelligent filtering**: Automatically excludes `self`, `cls`, database connections, and underscore-prefixed parameters
- **Custom key generation**: Smart key generation based on function signatures
