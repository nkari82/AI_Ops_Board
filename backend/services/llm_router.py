import aiohttp
from typing import Optional, Dict, Any, List
from config import settings
import json


class LLMRouter:
    def __init__(self):
        self.providers = {
            "huggingface": self._call_huggingface,
            "groq": self._call_groq,
            "vllm": self._call_vllm,
            "openrouter": self._call_openrouter
        }
    
    async def generate(
        self, 
        prompt: str, 
        provider: str = "huggingface",
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> str:
        if provider not in self.providers:
            provider = "huggingface"
        
        try:
            return await self.providers[provider](prompt, max_tokens, temperature)
        except Exception as e:
            return f"LLM 생성 실패: {str(e)}"
    
    async def _call_huggingface(self, prompt: str, max_tokens: int, temperature: float) -> str:
        if not settings.HUGGINGFACE_TOKEN:
            return "Hugging Face API 토큰이 설정되지 않았습니다."
        
        url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
        headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_TOKEN}"}
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "return_full_text": False
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if isinstance(result, list) and len(result) > 0:
                        return result[0].get("generated_text", "")
                return f"API 오류: {resp.status}"
    
    async def _call_groq(self, prompt: str, max_tokens: int, temperature: float) -> str:
        if not settings.GROQ_API_KEY:
            return "Groq API 키가 설정되지 않았습니다."
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result["choices"][0]["message"]["content"]
                return f"API 오류: {resp.status}"
    
    async def _call_vllm(self, prompt: str, max_tokens: int, temperature: float) -> str:
        url = f"{settings.VLLM_ENDPOINT}/chat/completions"
        
        payload = {
            "model": "local-model",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result["choices"][0]["message"]["content"]
                return f"vLLM 오류: {resp.status}"
    
    async def embed(self, text: str) -> List[float]:
        # Using HuggingFace feature extraction
        url = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"
        headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_TOKEN}"}
        payload = {"inputs": text}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    return await resp.json()
        raise Exception("Embedding generation failed")

    async def _call_openrouter(self, prompt: str, max_tokens: int, temperature: float) -> str:
        if not settings.OPENROUTER_API_KEY:
            return "OpenRouter API 키가 설정되지 않았습니다."
        
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "meta-llama/llama-3.3-70b-instruct",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result["choices"][0]["message"]["content"]
                return f"API 오류: {resp.status}"
