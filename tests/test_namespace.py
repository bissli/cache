"""Test key generation, namespace construction, and filtering logic.
"""
import cache
import pytest
from cache.cache import _create_namespace_filter, _normalize_namespace
from cache.cache import key_generator


@pytest.mark.parametrize(('input_ns', 'expected'), [
    ('users', '|users|'),
    ('api_data', '|api_data|'),
    ('reports', '|reports|'),
    ('|users|', '|users|'),
    ('|api_data|', '|api_data|'),
    ('user|admin', '|user.admin|'),
    ('api|weather|data', '|api.weather.data|'),
    ('|user|admin|', '|user.admin|'),
    ('|api|data|', '|api.data|'),
    ('', ''),
    (None, ''),
])
def test_normalize_namespace(input_ns, expected):
    """Verify namespace normalization handles various input formats correctly.
    """
    assert _normalize_namespace(input_ns) == expected


def test_namespace_filter_matches_correctly():
    """Verify namespace filter correctly identifies matching keys.
    """
    cache.configure(debug_key='v1:')

    matches_users = _create_namespace_filter('users')

    assert matches_users('v1:get_user||users||id=123') is True
    assert matches_users('v1:fetch_data||users||name=john') is True
    assert matches_users('v1:get_admin||admin||id=456') is False
    assert matches_users('v1:no_namespace||id=789') is False
    assert matches_users('wrong_prefix:get_user||users||id=123') is False


def test_namespace_filter_with_wrapped_input():
    """Verify namespace filter works when user passes pre-wrapped namespace.
    """
    cache.configure(debug_key='v1:')

    matches_users = _create_namespace_filter('|users|')

    assert matches_users('v1:get_user||users||id=123') is True
    assert matches_users('v1:get_admin||admin||id=456') is False


def test_namespace_filter_with_internal_pipes():
    """Verify namespace filter works with namespaces containing internal pipes.
    """
    cache.configure(debug_key='v1:')

    matches_complex = _create_namespace_filter('user|admin')

    assert matches_complex('v1:get_data||user.admin||id=123') is True
    assert matches_complex('v1:get_data||users||id=123') is False


def test_namespace_consistency_across_decorator_and_clear():
    """Verify namespace normalization is consistent between decoration and clearing.
    """
    test_cases = [
        'users',
        '|users|',
        'user|admin',
        '|api|data|',
    ]

    for namespace in test_cases:
        cache.configure(debug_key='v1:')
        normalized = _normalize_namespace(namespace)
        matches = _create_namespace_filter(namespace)

        test_key = f'v1:test_func|{normalized}|arg=value'

        assert matches(test_key) is True


def test_key_generator_basic():
    """Verify key generator creates keys from function arguments.
    """
    def sample_func(x: int, y: int) -> int:
        return x + y

    keygen = key_generator('users', sample_func)
    key = keygen(5, 10)

    assert 'sample_func' in key
    assert '|users|' in key
    assert 'x=5' in key
    assert 'y=10' in key


def test_key_generator_with_defaults():
    """Verify key generator handles default argument values.
    """
    def func_with_defaults(x: int, y: int = 10) -> int:
        return x + y

    keygen = key_generator('', func_with_defaults)
    key1 = keygen(5)
    key2 = keygen(5, 10)

    assert key1 == key2


def test_key_generator_filters_self():
    """Verify key generator excludes 'self' parameter from keys.
    """
    class Sample:
        def method(self, x: int) -> int:
            return x

    keygen = key_generator('', Sample.method)
    key = keygen(None, 5)

    assert 'self' not in key
    assert 'x=5' in key


def test_key_generator_filters_underscore_params():
    """Verify key generator excludes underscore-prefixed parameters.
    """
    def func(x: int, _internal: str = 'test') -> int:
        return x

    keygen = key_generator('', func)
    key = keygen(5, _internal='hidden')

    assert 'x=5' in key
    assert '_internal' not in key


def test_key_generator_filters_connection_objects():
    """Verify key generator excludes connection-like objects.
    """
    class MockConnection:
        def __init__(self):
            self.driver_connection = True

    def func_with_conn(conn, x: int) -> int:
        return x

    keygen = key_generator('', func_with_conn)
    mock_conn = MockConnection()
    key = keygen(mock_conn, 5)

    assert 'x=5' in key
    assert 'conn=' not in key
    assert 'MockConnection' not in key
