CLUSTER_NAME  ?= inference-platform
NAMESPACE     ?= inference
REGISTRY_NAME ?= registry
REGISTRY_PORT ?= 5001

.PHONY: build push apply deploy up down cluster-up cluster-down registry-up registry-down

build:
	docker build -f docker/llm_service.Dockerfile -t localhost:$(REGISTRY_PORT)/llm_service:v1 .
	docker build -f docker/classifier_service.Dockerfile -t localhost:$(REGISTRY_PORT)/classifier_service:v1 .

registry-up:
	@if ! docker ps -q -f name=$(REGISTRY_NAME) | grep -q .; then \
		docker run -d -p $(REGISTRY_PORT):5000 --name $(REGISTRY_NAME) registry:2; \
	fi

registry-down:
	docker rm -f $(REGISTRY_NAME) 2>/dev/null || true

cluster-up: registry-up
	kind create cluster --name $(CLUSTER_NAME) --config kind-config.yaml
	docker network connect kind $(REGISTRY_NAME) 2>/dev/null || true

cluster-down:
	kind delete cluster --name $(CLUSTER_NAME)

push:
	docker push localhost:$(REGISTRY_PORT)/llm_service:v1
	docker push localhost:$(REGISTRY_PORT)/classifier_service:v1

apply:
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f k8s/
	kubectl rollout status deployment/llm-service deployment/classifier-service -n $(NAMESPACE) --timeout=5m

deploy: push apply

up: cluster-up push apply

down: cluster-down registry-down
