"""
Единый модуль генерации.

Здесь — единственное место, где грузится модель и описана логика генерации.
И FastAPI (main.py), и gRPC-сервер (grpc_server.py) импортируют отсюда Engine,
чтобы не дублировать код и не держать модель в памяти в двух копиях.
"""

import os, time
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_PATH = os.environ.get("MODEL_PATH", "/models/qwen2.5-0.5b")
MODEL_VERSION = "v1"


class Engine:
    """Обёртка над моделью: загрузка один раз, генерация — много раз."""

    def __init__(self, model_path: str = MODEL_PATH):
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path, torch_dtype=torch.bfloat16
        )
        self.model.eval()

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 64,
        temperature: float = 1.0,
    ) -> tuple[str, float]:
        """
        Возвращает (сгенерированный_текст, latency_ms).
        Единая логика для REST и gRPC — менять параметры теперь нужно только тут.
        """
        t0 = time.perf_counter()
        inputs = self.tokenizer(prompt, return_tensors="pt")
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=temperature != 1.0,
            )
        # Отрезаем токены промпта, оставляем только то, что сгенерировано
        generated_ids = outputs[0][inputs["input_ids"].shape[1]:]
        text = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
        latency_ms = (time.perf_counter() - t0) * 1000
        return text, latency_ms

    def is_ready(self) -> bool:
        """Лёгкая проверка готовности: токенизатор отвечает."""
        try:
            _ = self.tokenizer("test", return_tensors="pt")
            return True
        except Exception:
            return False

# Один общий инстанс на процесс.
# Импортируя `engine`, и FastAPI, и gRPC работают с одной и той же загруженной моделью.
engine = Engine()