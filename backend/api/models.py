from importlib import import_module
from typing import TYPE_CHECKING, Any, cast

from fastapi import APIRouter, HTTPException

if TYPE_CHECKING:
    from backend.models import Domain, LlmModel


def _load_backend_models() -> tuple[type[Any], type[Any]]:
    try:
        models_module = import_module("backend.models")
    except ModuleNotFoundError:
        models_module = import_module("models")
    return models_module.LlmModel, models_module.Domain


LlmModel, Domain = _load_backend_models()
LlmModel = cast(type[Any], LlmModel)
Domain = cast(type[Any], Domain)
DOMAIN_VALUES = [
    member.value
    for member in getattr(Domain, "__members__", {}).values()
    if hasattr(member, "value")
]

router = APIRouter(tags=["models"])


MOCK_MODELS: list[Any] = [
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
    LlmModel(
        id="codex-cli-subscription",
        name="Codex CLI",
        provider="Codex CLI",
        cost="subscription",
        role="구독형 고성능 코딩/리뷰",
        endpoint="local://codex-cli",
        enabled=True
    ),
]


@router.get("/models", response_model=list[LlmModel])
async def get_models() -> list[Any]:
    return MOCK_MODELS


@router.get("/domains", response_model=list[str])
async def get_domains() -> list[str]:
    return DOMAIN_VALUES


@router.post("/models/{model_id}/toggle", response_model=LlmModel)
async def toggle_model(model_id: str) -> Any:
    model = next((m for m in MOCK_MODELS if m.id == model_id), None)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    model.enabled = not model.enabled
    return model
