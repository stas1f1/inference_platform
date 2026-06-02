# ── Config ───────────────────────────────────────────────
CLUSTER_NAME   ?= inference-platform
NAMESPACE      ?= inference
MONITORING_NS  ?= monitoring
REGISTRY_NAME  ?= registry
REGISTRY_PORT  ?= 5001
TAG            ?= v1
LLM_IMG        ?= localhost:$(REGISTRY_PORT)/llm_service:$(TAG)
CLF_IMG        ?= localhost:$(REGISTRY_PORT)/classifier_service:$(TAG)

.PHONY: models proto build push registry-up registry-down cluster-up cluster-down \
        namespace apply wait monitoring adapter deploy up down clean \
        pf-llm pf-clf pf-grafana pf-prom smoke \
		gpu-deps onnx trt triton vllm gpu-up

# ── Phase 0: workspace ───────────────────────────────────
models:
	@if [ -z "$$(ls -A models 2>/dev/null)" ]; then \
		echo ">> downloading models"; uv run python scripts/download_models.py; \
	else echo ">> models present"; fi
curl localhost:8000/v1/health/ready

# ── Phase 1: gRPC stubs ──────────────────────────────────
proto:
	uv run python -m grpc_tools.protoc -I proto \
		--python_out=services/llm_service \
		--grpc_python_out=services/llm_service \
		proto/inference.proto

# ── Phase 2.1: images ──────────────────────────────────────
build:
	docker build -f docker/llm_service.Dockerfile        -t $(LLM_IMG) .
	docker build -f docker/classifier_service.Dockerfile -t $(CLF_IMG) .

push:
	docker push $(LLM_IMG)
	docker push $(CLF_IMG)

# ── Phase 2.2: local cluster + registry ────────────────────
registry-up:
	@docker ps -q -f name=$(REGISTRY_NAME) | grep -q . || \
		docker run -d -p $(REGISTRY_PORT):5000 --name $(REGISTRY_NAME) registry:2

registry-down:
	-docker rm -f $(REGISTRY_NAME)

cluster-up: registry-up models
	@kind get clusters | grep -qx $(CLUSTER_NAME) || \
		kind create cluster --name $(CLUSTER_NAME) --config kind-config.yaml
	-@docker network connect kind $(REGISTRY_NAME) 2>/dev/null || true

cluster-down:
	-kind delete cluster --name $(CLUSTER_NAME)

# ── Phase 2.3: deploy (grows as you add files to k8s/) ─────
namespace:
	kubectl apply -f k8s/namespace.yaml

apply: namespace
	kubectl apply -f k8s/

wait:
	kubectl rollout status deploy/llm-service        -n $(NAMESPACE) --timeout=10m
	kubectl rollout status deploy/classifier-service -n $(NAMESPACE) --timeout=10m

# ── Phase 2.4: observability (helm, idempotent) ────────────
monitoring:
	helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
	helm repo update
	helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
		-n $(MONITORING_NS) --create-namespace \
		--set prometheus.prometheusSpec.podMonitorSelectorNilUsesHelmValues=false \
		--set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false

adapter:
	helm upgrade --install prometheus-adapter prometheus-community/prometheus-adapter \
		-n $(MONITORING_NS) -f helm/prometheus-adapter-values.yaml
	kubectl rollout status deploy/prometheus-adapter -n $(MONITORING_NS) --timeout=5m


# ── Phase 3: GPU server (run on the rented box) ──────────
gpu-deps:
	uv sync --extra gpu --extra loadtest

onnx:
	uv run python scripts/export_onnx.py

trt:
	mkdir -p triton_model_repo/resnet18/1
	trtexec --onnx=models/resnet18.onnx \
		--saveEngine=triton_model_repo/resnet18/1/model.plan --fp16 \
		--minShapes=input:1x3x224x224 \
		--optShapes=input:8x3x224x224 \
		--maxShapes=input:32x3x224x224

triton:
	docker run --gpus all --rm -p8500:8000 -p8501:8001 -p8502:8002 \
		-v $$(pwd)/triton_model_repo:/models nvcr.io/nvidia/tritonserver:24.05-py3 \
		tritonserver --model-repository=/models

vllm:
	uv run python -m vllm.entrypoints.openai.api_server \
		--model ./models/qwen2.5-0.5b --host 0.0.0.0 --port 8000 --max-model-len 2048

# one-shot prep: deps + artifacts. Then run `make vllm` and `make triton`.
gpu-up: models gpu-deps onnx trt
	@echo ">> artifacts ready. now run 'make vllm' and 'make triton' in separate shells"

# ── End-to-end (local CPU) ───────────────────────────────
deploy: build push apply wait
up: cluster-up build push apply monitoring adapter wait
	@echo ">> platform up:  kubectl get pods -A"
down: cluster-down #registry-down
clean:
	-kubectl delete -f k8s/ --ignore-not-found

# ── Port-forwards / smoke ────────────────────────────────
pf-llm:     ; kubectl port-forward -n $(NAMESPACE) svc/llm-service 8000:8000
pf-clf:     ; kubectl port-forward -n $(NAMESPACE) svc/classifier-service 8001:8001
pf-grafana: ; kubectl port-forward -n $(MONITORING_NS) svc/kube-prometheus-stack-grafana 3000:80
pf-prom:    ; kubectl port-forward -n $(MONITORING_NS) svc/kube-prometheus-stack-prometheus 9090:9090
smoke:
	curl -s localhost:8000/v1/health/ready; echo
	curl -s -X POST localhost:8000/v1/generate -H 'Content-Type: application/json' \
		-d '{"prompt":"Hello","max_new_tokens":16}'; echo