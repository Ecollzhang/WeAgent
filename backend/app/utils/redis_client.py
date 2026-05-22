import redis
from flask import current_app


class RedisClient:
    """Redis connection pool manager."""

    def __init__(self, app=None):
        self._client = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        pool = redis.ConnectionPool(
            host=app.config.get('REDIS_HOST', 'localhost'),
            port=app.config.get('REDIS_PORT', 6379),
            db=app.config.get('REDIS_DB', 0),
            password=app.config.get('REDIS_PASSWORD', None),
            decode_responses=True,
        )
        self._client = redis.Redis(connection_pool=pool)

    def get_client(self):
        if self._client is None:
            raise RuntimeError('RedisClient not initialized. Call init_app() first.')
        return self._client

    def get(self, key):
        return self.get_client().get(key)

    def set(self, key, value, ex=None):
        return self.get_client().set(key, value, ex=ex)

    def delete(self, key):
        return self.get_client().delete(key)

    def exists(self, key):
        return self.get_client().exists(key)

    def expire(self, key, time):
        return self.get_client().expire(key, time)


redis_client = RedisClient()
