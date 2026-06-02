from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from inference import engine, MODEL_VERSION

app = FastAPI(title="LLM Service", version="1.0.0")

from prometheus_client import Gauge, make_asgi_app

QUEUE_SIZE = Gauge("llm_pending_requests", "in-flight inference requests")
app.mount("/metrics", make_asgi_app())   # after app = FastAPI(...)

class PredictRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 64
    temperature: float = 1.0


class PredictResponse(BaseModel):
    text: str
    latency_ms: float
    model_version: str


@app.get("/v1/health/live")
def liveness():
    return {"status": "alive"}


@app.get("/v1/health/ready")
def readiness():
    if engine.is_ready():
        return {"status": "ready"}
    return JSONResponse(status_code=503, content={"status": "not ready"})


@app.post("/v1/generate", response_model=PredictResponse)
def generate(req: PredictRequest):
    QUEUE_SIZE.inc()
    try:
        text, latency = engine.generate(req.prompt, req.max_new_tokens, req.temperature)
        return PredictResponse(text=text, latency_ms=latency, model_version=MODEL_VERSION)
    finally:
        QUEUE_SIZE.dec()