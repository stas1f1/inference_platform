from dotenv import load_dotenv
load_dotenv()   

from huggingface_hub import snapshot_download
snapshot_download("Qwen/Qwen2.5-0.5B", local_dir="./models/qwen2.5-0.5b")
snapshot_download("microsoft/resnet-18", local_dir="./models/resnet-18")