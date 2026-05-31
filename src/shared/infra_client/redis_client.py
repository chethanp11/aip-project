"""
Redis Reusable Infrastructure Client
Integrates natively with the externalized Redis container.
"""

import redis
from src.shared.config import config

class RedisClient:
    def __init__(self):
        self.host = config.REDIS_HOST
        self.port = config.REDIS_PORT
        self._pool = None

    def get_client(self):
        """Returns a thread-safe Redis client instance using a connection pool."""
        if self._pool is None:
            self._pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                decode_responses=True
            )
        return redis.Redis(connection_pool=self._pool)

    def ping(self) -> bool:
        """Pings the Redis server to verify connectivity."""
        return self.get_client().ping()
