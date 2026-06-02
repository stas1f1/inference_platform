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
COPY services/classifier_service/ .
ENV MODEL_PATH=/models/resnet-18
EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]