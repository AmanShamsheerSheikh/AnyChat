import asyncpg

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