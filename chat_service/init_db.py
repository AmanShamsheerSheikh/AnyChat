import asyncpg
from fastapi import FastAPI
from settings import pg_settings, redis_settings
import redis.asyncio as redis
from redis.retry import Retry
from redis.backoff import ExponentialBackoff

async def initialize_db(app: FastAPI):
    app.state.db_pool = await asyncpg.create_pool(
        user=pg_settings.POSTGRES_USER,
        password=pg_settings.POSTGRES_PASSWORD,
        host=pg_settings.POSTGRES_HOST,
        port=pg_settings.PGBOUNCER_PORT,
        database=pg_settings.POSTGRES_DB,
        min_size=pg_settings.PGBOUNCER_MIN_CONNECTIONS,
        max_size=pg_settings.PGBOUNCER_MAX_CONNECTIONS,
        statement_cache_size=0
    )

    retry_strategy = Retry(backoff=ExponentialBackoff(cap=0.5, base=0.1), retries=3)
    redis_pool = redis.ConnectionPool(
        host=redis_settings.REDIS_HOST,
        port=redis_settings.REDIS_PORT,
        db=redis_settings.REDIS_DB,
        password=redis_settings.REDIS_PASSWORD,
        decode_responses=redis_settings.REDIS_DECODE_RESPONSES,
        socket_timeout=1.0,
        socket_connect_timeout=1.0,
        retry=retry_strategy,
        retry_on_timeout=True,
        retry_on_error=[ConnectionError, TimeoutError],
    )
    app.state.redis = redis.Redis(connection_pool=redis_pool)