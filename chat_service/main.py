from contextlib import asynccontextmanager
import asyncpg
from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
import modal
from fastapi.middleware.cors import CORSMiddleware
from middleware.api_auth import AuthMiddleWare
from middleware.rate_limiter import RateLimitMiddleWare
from queries import register_user, add_job, get_user, update_job
from init_db import initialize_db
from constants import JobStatus

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

@app.get("/health")
def check():
    return {"status": "working"}

async def stream_and_track(prompt: str, job_id: str, db_pool):
    full_response = ""
    try:
        async for token in gpu_worker.generate_tokens.remote_gen(prompt):
            full_response += token
            yield token
        async with db_pool.acquire() as conn:
            await update_job(conn, job_id, JobStatus.DONE.value, result=full_response)
    except Exception as e:
        async with db_pool.acquire() as conn:
            await update_job(conn, job_id, JobStatus.FAILED.value, None, error=str(e))
        raise

@app.post("/generate")
async def generate(request: GenerateRequest, conn: asyncpg.Connection = Depends(get_db_connection)):
    api_key = request.headers.get("X-API-Key")
    user_id = await get_user(conn, api_key)
    job_ib = await add_job(conn, user_id, JobStatus.PENDING.value,request.prompt)
    return StreamingResponse(
        stream_and_track(request.prompt, job_ib, request.app.state.db_pool),
        media_type="text/event-stream"
    )

@app.post("/register_user")
async def registerUser(request: RegisterRequest, conn: asyncpg.Connection = Depends(get_db_connection)):
    api_key = await register_user(conn, request.user_name)
    return {
        "api_key": api_key
    }