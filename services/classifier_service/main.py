from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from transformers import AutoImageProcessor, AutoModelForImageClassification
from PIL import Image
import torch, io, time, os

app = FastAPI(title="Classifier Service", version="1.0.0")

MODEL_PATH = os.environ.get("MODEL_PATH", "/models/resnet-18")
extractor = AutoImageProcessor.from_pretrained(MODEL_PATH)
model = AutoModelForImageClassification.from_pretrained(MODEL_PATH)
model.eval()

class ClassifyResponse(BaseModel):
    label: str
    score: float
    latency_ms: float
    model_version: str = "v1"

@app.get("/v1/health/live")
def liveness():
    return {"status": "alive"}

@app.get("/v1/health/ready")
def readiness():
    return {"status": "ready"}

@app.post("/v1/classify", response_model=ClassifyResponse)
async def classify(file: UploadFile = File(...)):
    t0 = time.perf_counter()
    image = Image.open(io.BytesIO(await file.read())).convert("RGB")
    inputs = extractor(images=image, return_tensors="pt")
    with torch.no_grad():
        logits = model(**inputs).logits
    pred = logits.argmax(-1).item()
    score = torch.softmax(logits, dim=-1)[0][pred].item()
    label = model.config.id2label[pred]
    return ClassifyResponse(label=label, score=score, 
                            latency_ms=(time.perf_counter() - t0) * 1000)