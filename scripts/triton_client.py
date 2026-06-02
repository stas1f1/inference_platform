import numpy as np, tritonclient.http as http
from PIL import Image
import torchvision.transforms as T

tf = T.Compose([T.Resize(256), T.CenterCrop(224), T.ToTensor(),
                T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
x = tf(Image.open("data/test_c.jpg").convert("RGB")).unsqueeze(0).numpy()

c = http.InferenceServerClient("localhost:8500")
inp = http.InferInput("input", x.shape, "FP32"); inp.set_data_from_numpy(x)
out = c.infer("resnet18", [inp], outputs=[http.InferRequestedOutput("logits")])
print("top class:", int(np.argmax(out.as_numpy("logits"))))