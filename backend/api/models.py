from fastapi import APIRouter, HTTPException
from typing import List
from models import LlmModel, Domain

router = APIRouter(tags=["models"])


MOCK_MODELS = [
    LlmModel(
        id="hf-mistral-7b",
        name="Mistral-7B-Instruct",
        provider="Hugging Face",
        cost="free",
        role="분석/요약",
        endpoint="https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2",
        enabled=True
    ),
    LlmModel(
        id="vllm-local",
        name="Local vLLM",
        provider="Local",
        cost="free",
        role="종합",
        endpoint="http://localhost:8000/v1",
        enabled=False
    ),
    LlmModel(
        id="groq-llama-70b",
        name="LLaMA 3 70B",
        provider="Groq",
        cost="free",
        role="고급분석",
        endpoint="https://api.groq.com/openai/v1",
        enabled=True
    ),
]


@router.get("/models", response_model=List[LlmModel])
async def get_models():
    return MOCK_MODELS


@router.get("/domains", response_model=List[str])
async def get_domains():
    return [domain.value for domain in Domain]


@router.post("/models/{model_id}/toggle", response_model=LlmModel)
async def toggle_model(model_id: str):
    model = next((m for m in MOCK_MODELS if m.id == model_id), None)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    model.enabled = not model.enabled
    return model
