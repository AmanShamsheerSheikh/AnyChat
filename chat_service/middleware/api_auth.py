from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from queries import get_user

AUTH_ROUTES = ["/generate"]

class AuthMiddleWare(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        if request.url.path not in AUTH_ROUTES:
            return await call_next(request)
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return Response(content="API key required", status_code=401)
        async with request.app.state.db_pool.acquire() as conn:
            user_name = await get_user(conn, api_key)
        if not user_name:
            return Response(content="Invalid Api key", status_code=401)
        
        return await call_next(request)