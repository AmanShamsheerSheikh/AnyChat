import asyncpg

async def add_job(conn: asyncpg.Connection, user_id: str, status: str, prompt: str) -> int:
    query = """
        INSERT INTO jobs (user_id, status, prompt)
        VALUES ($1, $2, $3)
        RETURNING id
    """
    return await conn.fetchval(query, user_id, status, prompt)

async def update_job(conn: asyncpg.Connection, job_id: str, status: str, result: str = None, error: str = None):
    query = """
        UPDATE jobs
        SET status = $1, result = $2, error = $3, updated_at = CURRENT_TIMESTAMP
        WHERE id = $4
    """
    return await conn.execute(query, status, result, error, job_id)


async def get_user(conn: asyncpg.Connection, api_key: str):
    return await conn.fetchval(
        "Select user_id from users where api_key = $1",
        api_key
    )

async def register_user(conn: asyncpg.Connection, user_name: str):
    query = """
        INSERT INTO users (user_name)
        VALUES ($1)
        RETURNING api_key
    """
    return await conn.fetchval(query, user_name)