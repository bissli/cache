"""Test namespace construction and filtering logic.
"""
import cache
from cache.cache import _create_namespace_filter, _normalize_namespace


def test_normalize_namespace_simple():
    """Verify simple namespace strings are wrapped correctly.
    """
    assert _normalize_namespace('users') == '|users|'
    assert _normalize_namespace('api_data') == '|api_data|'
    assert _normalize_namespace('reports') == '|reports|'


def test_normalize_namespace_already_wrapped():
    """Verify already-wrapped namespaces remain unchanged.
    """
    assert _normalize_namespace('|users|') == '|users|'
    assert _normalize_namespace('|api_data|') == '|api_data|'


def test_normalize_namespace_with_internal_pipes():
    """Verify internal pipes are replaced with periods.
    """
    assert _normalize_namespace('user|admin') == '|user.admin|'
    assert _normalize_namespace('api|weather|data') == '|api.weather.data|'


def test_normalize_namespace_with_leading_trailing_pipes():
    """Verify leading/trailing pipes are stripped before internal pipe replacement.
    """
    assert _normalize_namespace('|user|admin|') == '|user.admin|'
    assert _normalize_namespace('|api|data|') == '|api.data|'


def test_normalize_namespace_empty():
    """Verify empty namespace returns empty string.
    """
    assert _normalize_namespace('') == ''
    assert _normalize_namespace(None) == ''


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
        normalized = _normalize_namespace(namespace)
        matches = _create_namespace_filter(namespace)

        cache.configure(debug_key='v1:')
        test_key = f'v1:test_func|{normalized}|arg=value'

        assert matches(test_key) is True


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
