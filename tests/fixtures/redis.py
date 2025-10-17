import logging
import time

import docker
import pytest

logger = logging.getLogger(__name__)


@pytest.fixture(scope='session')
def redis_docker(request):
    """Start Redis container for testing.
    """
    client = docker.from_env()

    try:
        old_container = client.containers.get('test_redis')
        logger.info('Found existing test container, removing it')
        old_container.stop()
        old_container.remove()
    except docker.errors.NotFound:
        pass
    except Exception as e:
        logger.warning(f'Error when cleaning up container: {e}')

    try:
        container = client.containers.run(
            image='redis:7-alpine',
            auto_remove=True,
            name='test_redis',
            ports={'6379/tcp': ('127.0.0.1', 6379)},
            detach=True,
            remove=True,
        )

        def finalizer():
            try:
                container.stop()
            except Exception as e:
                logger.warning(f'Error stopping container during cleanup: {e}')

        request.addfinalizer(finalizer)

        try:
            import redis
        except ImportError:
            raise Exception('redis package not installed, cannot test Redis functionality')

        for i in range(30):
            try:
                r = redis.Redis(host='localhost', port=6379, db=0)
                r.ping()
                r.close()
                logger.debug('Redis container ready')
                break
            except Exception as e:
                logger.debug(e)
                time.sleep(1)
        else:
            raise Exception('Redis container failed to start in time')

        return container

    except Exception as e:
        logger.error(f'Error setting up Redis container: {e}')
        raise
