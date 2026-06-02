CLUSTER_NAME ?= inference-platform
NAMESPACE    ?= inference

.PHONY: build load apply deploy up down cluster-up cluster-down

build:
	docker build -f docker/llm_service.Dockerfile -t llm_service:v1 .
	docker build -f docker/classifier_service.Dockerfile -t classifier_service:v1 .

cluster-up:
	kind create cluster --name $(CLUSTER_NAME) --config kind-config.yaml

cluster-down:
	kind delete cluster --name $(CLUSTER_NAME)

load:
	kind load docker-image llm_service:v1 --name $(CLUSTER_NAME)
	kind load docker-image classifier_service:v1 --name $(CLUSTER_NAME)

apply:
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f k8s/
	kubectl rollout status deployment/llm-service deployment/classifier-service -n $(NAMESPACE) --timeout=5m

deploy: load apply

up: cluster-up load apply

down: cluster-down
