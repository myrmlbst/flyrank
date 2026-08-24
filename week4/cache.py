import os

import redis

REDIS_URL = os.environ["REDIS_URL"]


def get_redis():
    return redis.Redis.from_url(REDIS_URL)


def ping() -> bool:
    return get_redis().ping()
