import os, time
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_PATH = os.environ.get("MODEL_PATH", "/models/qwen2.5-0.5b")
MODEL_VERSION = "v1"


class Engine:
    """Load the model once, generate many times. Imported by REST and gRPC."""

    def __init__(self, model_path: str = MODEL_PATH):
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path, torch_dtype=torch.bfloat16
        )
        self.model.eval()

    def generate(self, prompt: str, max_new_tokens: int = 64,
                 temperature: float = 1.0) -> tuple[str, float]:
        t0 = time.perf_counter()
        inputs = self.tokenizer(prompt, return_tensors="pt")
        with torch.no_grad():
            out = self.model.generate(
                **inputs, max_new_tokens=max_new_tokens,
                temperature=temperature, do_sample=temperature != 1.0,
            )
        gen_ids = out[0][inputs["input_ids"].shape[1]:]   # drop the prompt
        text = self.tokenizer.decode(gen_ids, skip_special_tokens=True)
        return text, (time.perf_counter() - t0) * 1000

    def is_ready(self) -> bool:
        try:
            _ = self.tokenizer("test", return_tensors="pt")
            return True
        except Exception:
            return False


engine = Engine()   # one instance per process