from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
import modal

from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up: Initializing modal")
    global gpu_worker
    gpu_worker = modal.Cls.from_name("anychat-gpu-worker", "GPUWorker")()
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class GenerateRequest(BaseModel):
    prompt: str

@app.post("/generate")
def generate(request: GenerateRequest):
    return StreamingResponse(
        gpu_worker.generate_tokens.remote_gen(request.prompt),
        media_type="text/event-stream"
    )
