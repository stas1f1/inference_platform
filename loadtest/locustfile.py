from locust import HttpUser, task, between

class LLMUser(HttpUser):
    wait_time = between(0, 0.1)
    @task
    def generate(self):
        self.client.post("/v1/generate",
                         json={"prompt": "Hello!", "max_new_tokens": 32})