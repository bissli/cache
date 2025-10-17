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

## Class-Friendly Caching

The library automatically handles caching for instance methods, class methods, and static methods by intelligently filtering out method-specific parameters like `self` and `cls`.

**Instance Methods:**

```python
from cache import memorycache

class UserRepository:
    def __init__(self, db_connection):
        self.conn = db_connection
    
    @memorycache(seconds=300).cache_on_arguments()
    def get_user(self, user_id):
        """Fetch user by ID.
        
        The 'self' parameter is automatically excluded from the cache key,
        so the cache key will only be based on 'user_id'.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return cursor.fetchone()

# These calls will use the same cache entry (keyed only by user_id=123)
# even though they are called on different instances
repo1 = UserRepository(connection1)
repo2 = UserRepository(connection2)

result1 = repo1.get_user(123)
result2 = repo2.get_user(123)  # Returns cached result from result1
```

**Class Methods:**

```python
from cache import memorycache

class ConfigManager:
    @classmethod
    @memorycache(seconds=600).cache_on_arguments()
    def get_setting(cls, setting_name):
        """Fetch configuration setting.
        
        The 'cls' parameter is automatically excluded from the cache key,
        so the cache key will only be based on 'setting_name'.
        """
        return load_setting_from_file(setting_name)

# These calls will use the same cache entry
setting1 = ConfigManager.get_setting('timeout')
setting2 = ConfigManager.get_setting('timeout')  # Returns cached result
```

**Static Methods:**

```python
from cache import memorycache

class DataProcessor:
    @staticmethod
    @memorycache(seconds=3600).cache_on_arguments()
    def transform_data(data_format, data):
        """Transform data based on format.
        
        Cache key is based on both 'data_format' and 'data' parameters.
        """
        return apply_transformation(data_format, data)

# Standard static method caching
result = DataProcessor.transform_data('json', raw_data)
```

**What gets automatically filtered from cache keys:**

- `self` parameter (for instance methods)
- `cls` parameter (for class methods)
- Database connection objects (detected by `database.isconnection()`)
- Any parameter starting with underscore (`_`)

This ensures cache keys are based only on the meaningful data parameters, not on implementation details like instance references or class references.

## Database Connection Handling

The library automatically detects and excludes database connection objects from cache keys. This prevents connection objects from being serialized or included in cache key generation, which would cause caching to fail or produce incorrect keys.

**How it works:**

When generating cache keys, the library uses the `database.isconnection()` function to identify database connection objects among function arguments. Any detected connections are automatically filtered out before key generation.

**Example:**

```python
from cache import memorycache

@memorycache(seconds=300).cache_on_arguments()
def get_user_data(conn, user_id):
    """Fetch user data from database.
    
    The 'conn' parameter will be automatically excluded from the cache key,
    so the cache key will only be based on 'user_id'.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cursor.fetchone()

# These calls will use the same cache entry (keyed only by user_id=123)
# even though they use different connection objects
result1 = get_user_data(connection1, 123)
result2 = get_user_data(connection2, 123)  # Returns cached result from result1
```

**What gets filtered:**

- Database connection objects (detected by `database.isconnection()`)
- `self` and `cls` parameters (for instance and class methods)
- Any parameter starting with underscore (`_`)

This ensures cache keys are based only on the meaningful data parameters, not on implementation details like connection objects.

## Features

- **Multiple backends**: Memory, file (DBM), and Redis
- **Flexible expiration**: Configure different TTLs for different use cases
- **Namespace support**: Organize cache keys and selectively clear regions
- **Database connection filtering**: Automatically excludes database connections from cache keys
- **Custom key generation**: Intelligent key generation based on function signatures
