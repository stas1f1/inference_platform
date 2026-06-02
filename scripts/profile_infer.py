import torch
from torch.profiler import profile, record_function, ProfilerActivity
from transformers import AutoModelForImageClassification

model = AutoModelForImageClassification.from_pretrained("./models/resnet-18").eval().cuda()
x = torch.randn(8, 3, 224, 224).cuda()

with profile(activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA],
             record_shapes=True) as prof:
    with record_function("infer"), torch.no_grad():
        _ = model(x)

print(prof.key_averages().table(sort_by="cuda_time_total", row_limit=10))
prof.export_chrome_trace("trace.json")   # open in chrome://tracing