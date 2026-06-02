# Stage 1 — зависимости
FROM python:3.12-slim AS builder
WORKDIR /build
RUN pip install --no-cache-dir uv
COPY pyproject.toml .
RUN uv pip install --prefix=/install --no-cache .

# Stage 2 — рантайм
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY services/llm_service/ .
COPY proto/ ./proto/
# Модель монтируем через PVC, не копируем в образ
ENV MODEL_PATH=/models/qwen2.5-0.5b
EXPOSE 8000 50051
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8000 & python grpc_server.py"]
