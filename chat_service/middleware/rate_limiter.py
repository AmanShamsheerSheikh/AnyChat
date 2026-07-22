from fastapi import Request
import redis.asyncio as redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class RateLimitMiddleWare(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.limit = 5
        self.duration = 60
        self.register_user_duration = 3600
        with open("middleware/fixed_window.lua", "r") as file:
            self.lua_script = file.read()

    async def check_if_allowed(self, redis: redis.Redis, key: str, duration: int):
        try:
            execute_lua = redis.register_script(self.lua_script)
            result = await execute_lua(keys=[key], args=[self.limit, duration])
            return result
        except Exception as e:
            print(f"Rate limiter Redis check failed, failing open: {e}")
            return True

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/register_user":
            allowed = await self.check_if_allowed(
                request.app.state.redis, 
                request.client.host,
                self.register_user_duration
            )
            if not allowed:
                return Response(content="Too many requests", status_code=429)
            return await call_next(request)
        api_key = request.headers.get("X-API-Key")
        ip = request.client.host
        redis = request.app.state.redis
        key = f"{api_key}_{ip}"
        if api_key:
            allowed = await self.check_if_allowed(redis, key, self.duration)
            if not allowed:
                return Response(content="Too many requests", status_code=429)
        
        return await call_next(request)