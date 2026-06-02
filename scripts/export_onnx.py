import torch
from transformers import AutoModelForImageClassification
import onnxruntime as rt

model = AutoModelForImageClassification.from_pretrained("./models/resnet-18").eval()
dummy = torch.randn(1, 3, 224, 224)

torch.onnx.export(
    model, dummy, "models/resnet18.onnx",
    input_names=["input"], output_names=["logits"],
    dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}},
    opset_version=17,
    dynamo=False,
)
print("ONNX export done")

sess = rt.InferenceSession("models/resnet18.onnx", providers=["CUDAExecutionProvider"])
out = sess.run(None, {"input": dummy.numpy()})
print("ONNX OK, logits shape:", out[0].shape)