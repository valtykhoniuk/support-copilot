import os
from functools import lru_cache
from pathlib import Path

LABELS = ("billing", "bug", "how-to", "refund", "other")

MODEL_ID = "meta-llama/Llama-3.2-1B-Instruct"
INSTRUCTION = (
    "Classify this FoxSchool support ticket. "
    "Reply with only one label: billing, bug, how-to, refund, other."
)
PROMPT = """### Instruction:
{}
### Input:
{}
### Response:
"""
# ../finetune-vs-prompt/models/foxschool-intent-lora
_DEFAULT_ADAPTER = (
    Path(__file__).resolve().parent.parent.parent
    / "finetune-vs-prompt/models/foxschool-intent-lora"
)
def adapter_dir() -> Path:
    raw = os.getenv("LORA_ADAPTER_DIR", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _DEFAULT_ADAPTER.resolve()
def is_available() -> bool:
    return (adapter_dir() / "adapter_config.json").exists()
def is_enabled() -> bool:
    flag = os.getenv("USE_LORA_ROUTER", "").lower()
    return flag in {"1", "true", "yes"} and is_available()
@lru_cache(maxsize=1)
def _load_model():
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    dtype = torch.float16 if device != "cpu" else torch.float32
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    base = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, dtype=dtype, device_map=device,
    )
    model = PeftModel.from_pretrained(base, str(adapter_dir()))
    model.eval()
    return model, tokenizer, device
def predict_intent(text: str) -> str:
    import torch
    model, tokenizer, device = _load_model()
    prompt = PROMPT.format(INSTRUCTION, text)
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=8, do_sample=False)
    generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
    answer = generated.split("### Response:")[-1].strip().lower()
    for label in LABELS:
        if label in answer:
            return label
    return "other"