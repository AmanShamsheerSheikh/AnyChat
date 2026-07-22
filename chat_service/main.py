from contextlib import asynccontextmanager
import asyncpg
from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
import modal
from fastapi.middleware.cors import CORSMiddleware
from middleware.api_auth import AuthMiddleWare
from middleware.rate_limiter import RateLimitMiddleWare
from queries import register_user
from init_db import initialize_db

async def get_db_connection(request: Request):
    async with request.app.state.db_pool.acquire() as conn:
        yield conn

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up: Initializing database pools...")
    await initialize_db(app)
    print("Starting up: Initializing modal")
    global gpu_worker
    gpu_worker = modal.Cls.from_name("anychat-gpu-worker", "GPUWorker")()
    yield
    print("Shutting down: Closing database pools...")
    await app.state.db_pool.close()
    await app.state.redis.aclose()

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(AuthMiddleWare)
app.add_middleware(RateLimitMiddleWare)

class GenerateRequest(BaseModel):
    prompt: str

class RegisterRequest(BaseModel):
    user_name: str

@app.post("/generate")
def generate(request: GenerateRequest):
    return StreamingResponse(
        gpu_worker.generate_tokens.remote_gen(request.prompt),
        media_type="text/event-stream"
    )

@app.post("/register_user")
async def registerUser(request: RegisterRequest, conn: asyncpg.Connection = Depends(get_db_connection)):
    api_key = await register_user(conn, request.user_name)
    return {
        "api_key": api_key
    }