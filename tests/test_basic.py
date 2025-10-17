"""Basic smoke test for cache.
"""
import cache


def test_configure():
    """Test that configuration works.
    """
    cache.configure(debug_key='test:', tmpdir='/tmp/test')
    config = cache.get_config()
    assert config.debug_key == 'test:'
    assert config.tmpdir == '/tmp/test'


def test_memorycache():
    """Test that memory cache can be created.
    """
    region = cache.memorycache(seconds=60)
    assert region is not None


if __name__ == '__main__':
    test_configure()
    test_memorycache()
    print('✓ Basic tests passed')
