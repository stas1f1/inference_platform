# Собери образы
docker build -f docker/llm_service.Dockerfile -t llm_service:v1 .
docker build -f docker/classifier_service.Dockerfile -t classifier_service:v1 .

# Загрузи в kind (kind не имеет доступа к локальному docker registry)
kind load docker-image llm_service:v1 --name inference-platform
kind load docker-image classifier_service:v1 --name inference-platform

# Проверь что образы доступны
docker exec -it inference-platform-worker crictl images | grep -E "llm|classifier"