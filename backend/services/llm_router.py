import aiohttp
import logging
import time
from typing import List
from config import settings
from services.error_tracker import error_tracker

logger = logging.getLogger(__name__)
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=30, connect=10, sock_read=25)


def _join_url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


class LLMRouterError(Exception):
    def __init__(self, provider: str, message: str, status_code: int | None = None):
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.message = message


class LLMRouter:
    def __init__(self):
        self.providers = {
            "huggingface": self._call_huggingface,
            "groq": self._call_groq,
            "vllm": self._call_vllm,
            "openrouter": self._call_openrouter,
            "pollinations": self._call_pollinations,
            "gemini": self._call_gemini,
            "mistral": self._call_mistral,
            "deepseek": self._call_deepseek,
            "cerebras": self._call_cerebras,
            "sambanova": self._call_sambanova,
        }

    def _parse_failover_order(self) -> list[str]:
        raw = (getattr(settings, "LLM_FAILOVER_ORDER", "") or "").strip()
        if not raw:
            return ["gemini", "pollinations", "groq", "openrouter", "mistral", "deepseek", "cerebras", "sambanova", "huggingface", "vllm"]
        ordered = [item.strip() for item in raw.split(",") if item.strip()]
        return [item for item in ordered if item in self.providers]

    def _parse_failover_statuses(self) -> set[int]:
        raw = (getattr(settings, "LLM_FAILOVER_ON_STATUS", "") or "").strip()
        statuses: set[int] = set()
        for token in raw.split(","):
            token = token.strip()
            if not token:
                continue
            try:
                statuses.add(int(token))
            except ValueError:
                continue
        return statuses or {429, 503, 504}

    def _is_failover_candidate(self, err: LLMRouterError) -> bool:
        statuses = self._parse_failover_statuses()
        # Quota-aware 기본 + 인증 실패(401/403)도 fallback 허용
        if err.status_code in statuses or err.status_code in {401, 403}:
            return True
        msg = (err.message or "").lower()
        fallback_markers = [
            "quota",
            "resource_exhausted",
            "rate limit",
            "too many requests",
            "api 키가 설정되지 않았습니다",
            "토큰이 설정되지 않았습니다",
            "api 오류: 401",
            "api 오류: 403",
            "unauthorized",
            "forbidden",
        ]
        return any(marker in msg for marker in fallback_markers)

    async def _call_provider(self, provider: str, prompt: str, max_tokens: int, temperature: float) -> str:
        started = time.perf_counter()
        try:
            result = await self.providers[provider](prompt, max_tokens, temperature)
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info("LLM call success provider=%s elapsed_ms=%s prompt_len=%s", provider, elapsed_ms, len(prompt or ""))
            return result
        except LLMRouterError as e:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.error("LLM call failed provider=%s status=%s elapsed_ms=%s msg=%s", e.provider, e.status_code, elapsed_ms, e.message)
            error_tracker.log_error(
                "LLM_FAILURE",
                e.message,
                details={
                    "provider": e.provider,
                    "status_code": e.status_code,
                    "elapsed_ms": elapsed_ms,
                    "prompt_len": len(prompt or ""),
                },
            )
            raise
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.exception("LLM unexpected failure provider=%s elapsed_ms=%s", provider, elapsed_ms)
            error_tracker.log_error(
                "LLM_FAILURE",
                str(e),
                details={"provider": provider, "elapsed_ms": elapsed_ms, "prompt_len": len(prompt or "")},
            )
            raise LLMRouterError(provider=provider, message=f"LLM 생성 실패: {str(e)}") from e

    async def generate(
        self,
        prompt: str,
        provider: str = "huggingface",
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> str:
        preferred = provider if provider in self.providers else "huggingface"
        failover_enabled = bool(getattr(settings, "LLM_FAILOVER_ENABLED", True))

        if not failover_enabled:
            return await self._call_provider(preferred, prompt, max_tokens, temperature)

        order = self._parse_failover_order()
        attempts: list[str] = [preferred]
        attempts.extend([p for p in order if p != preferred])

        last_error: LLMRouterError | None = None
        for idx, candidate in enumerate(attempts, start=1):
            try:
                if idx > 1:
                    logger.warning("LLM failover attempt=%s provider=%s", idx, candidate)
                return await self._call_provider(candidate, prompt, max_tokens, temperature)
            except LLMRouterError as err:
                last_error = err
                if not self._is_failover_candidate(err):
                    raise
                continue

        if last_error:
            raise last_error
        raise LLMRouterError(provider=preferred, message="LLM 생성 실패: provider chain exhausted")
    
    async def _call_huggingface(self, prompt: str, max_tokens: int, temperature: float) -> str:
        if not settings.HUGGINGFACE_TOKEN:
            raise LLMRouterError("huggingface", "Hugging Face API 토큰이 설정되지 않았습니다.")
        
        url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
        headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_TOKEN}"}
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "return_full_text": False
            }
        }
        
        async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if isinstance(result, list) and len(result) > 0:
                        return result[0].get("generated_text", "")
                raise LLMRouterError("huggingface", f"API 오류: {resp.status}", status_code=resp.status)
    
    async def _call_groq(self, prompt: str, max_tokens: int, temperature: float) -> str:
        if not settings.GROQ_API_KEY:
            raise LLMRouterError("groq", "Groq API 키가 설정되지 않았습니다.")
        
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
        
        async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result["choices"][0]["message"]["content"]
                raise LLMRouterError("groq", f"API 오류: {resp.status}", status_code=resp.status)
    
    async def _call_vllm(self, prompt: str, max_tokens: int, temperature: float) -> str:
        url = f"{settings.VLLM_ENDPOINT}/chat/completions"
        
        payload = {
            "model": "local-model",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result["choices"][0]["message"]["content"]
                raise LLMRouterError("vllm", f"vLLM 오류: {resp.status}", status_code=resp.status)
    
    async def embed(self, text: str) -> List[float]:
        # Using HuggingFace feature extraction
        url = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"
        headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_TOKEN}"}
        payload = {"inputs": text}
        
        async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    return await resp.json()
        raise Exception("Embedding generation failed")

    async def _call_openrouter(self, prompt: str, max_tokens: int, temperature: float) -> str:
        if not settings.OPENROUTER_API_KEY:
            raise LLMRouterError("openrouter", "OpenRouter API 키가 설정되지 않았습니다.")
        
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
        
        async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result["choices"][0]["message"]["content"]
                raise LLMRouterError("openrouter", f"API 오류: {resp.status}", status_code=resp.status)

    async def _call_openai_compatible(
        self,
        *,
        provider: str,
        api_key: str | None,
        base_url: str,
        model: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        if not api_key:
            raise LLMRouterError(provider, f"{provider} API 키가 설정되지 않았습니다.")

        url = _join_url(base_url, "/chat/completions")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result["choices"][0]["message"]["content"]
                raise LLMRouterError(provider, f"API 오류: {resp.status}", status_code=resp.status)

    async def _call_mistral(self, prompt: str, max_tokens: int, temperature: float) -> str:
        return await self._call_openai_compatible(
            provider="mistral",
            api_key=settings.MISTRAL_API_KEY,
            base_url=settings.MISTRAL_BASE_URL,
            model=settings.MISTRAL_MODEL,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    async def _call_deepseek(self, prompt: str, max_tokens: int, temperature: float) -> str:
        return await self._call_openai_compatible(
            provider="deepseek",
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            model=settings.DEEPSEEK_MODEL,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    async def _call_cerebras(self, prompt: str, max_tokens: int, temperature: float) -> str:
        return await self._call_openai_compatible(
            provider="cerebras",
            api_key=settings.CEREBRAS_API_KEY,
            base_url=settings.CEREBRAS_BASE_URL,
            model=settings.CEREBRAS_MODEL,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    async def _call_sambanova(self, prompt: str, max_tokens: int, temperature: float) -> str:
        return await self._call_openai_compatible(
            provider="sambanova",
            api_key=settings.SAMBANOVA_API_KEY,
            base_url=settings.SAMBANOVA_BASE_URL,
            model=settings.SAMBANOVA_MODEL,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    async def _call_pollinations(self, prompt: str, max_tokens: int, temperature: float) -> str:
        if not settings.POLLINATIONS_API_KEY:
            raise LLMRouterError("pollinations", "Pollinations API 키가 설정되지 않았습니다.")

        url = _join_url(settings.POLLINATIONS_BASE_URL, "/v1/chat/completions")
        headers = {
            "Authorization": f"Bearer {settings.POLLINATIONS_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": settings.POLLINATIONS_TEXT_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result["choices"][0]["message"]["content"]
                raise LLMRouterError("pollinations", f"API 오류: {resp.status}", status_code=resp.status)

    async def _call_gemini(self, prompt: str, max_tokens: int, temperature: float) -> str:
        # Google AI Studio (Gemini) - Generative Language API
        if not settings.GOOGLE_AI_STUDIO_KEY:
            raise LLMRouterError("gemini", "Google AI Studio API 키가 설정되지 않았습니다.")

        base_url = settings.GEMINI_BASE_URL or "https://generativelanguage.googleapis.com"
        raw_model = (settings.GEMINI_MODEL or "gemini-flash-latest").strip()
        # Normalize common old names
        if raw_model in {"gemini-1.5-flash", "gemini-1.5-flash-latest"}:
            raw_model = "gemini-flash-latest"

        # API expects resource like "models/<name>"
        model_resource = raw_model if raw_model.startswith("models/") else f"models/{raw_model}"

        url = _join_url(
            base_url,
            f"/v1beta/{model_resource}:generateContent",
        )
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": settings.GOOGLE_AI_STUDIO_KEY,
        }

        payload: dict[str, object] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    candidates = result.get("candidates") or []
                    if candidates:
                        content = candidates[0].get("content") or {}
                        parts = content.get("parts") or []
                        if parts and isinstance(parts[0], dict) and "text" in parts[0]:
                            return str(parts[0]["text"])
                    return ""

                # If model not found, query ListModels and retry with best flash model.
                if resp.status == 404:
                    try:
                        list_url = _join_url(base_url, "/v1beta/models")
                        async with session.get(list_url, headers=headers) as list_resp:
                            if list_resp.status == 200:
                                data = await list_resp.json()
                                names = [m.get("name") for m in (data.get("models") or []) if isinstance(m, dict)]
                                names = [n for n in names if isinstance(n, str)]
                                preferred = None
                                for cand in (
                                    "models/gemini-flash-latest",
                                    "models/gemini-2.0-flash",
                                    "models/gemini-2.0-flash-001",
                                ):
                                    if cand in names:
                                        preferred = cand
                                        break
                                if not preferred:
                                    flash = [n for n in names if "gemini" in n and "flash" in n]
                                    preferred = flash[0] if flash else (names[0] if names else None)

                                if preferred and preferred != model_resource:
                                    retry_url = _join_url(
                                        base_url,
                                        f"/v1beta/{preferred}:generateContent",
                                    )
                                    async with session.post(retry_url, headers=headers, json=payload) as retry_resp:
                                        if retry_resp.status == 200:
                                            retry_result = await retry_resp.json()
                                            candidates = retry_result.get("candidates") or []
                                            if candidates:
                                                content = candidates[0].get("content") or {}
                                                parts = content.get("parts") or []
                                                if parts and isinstance(parts[0], dict) and "text" in parts[0]:
                                                    return str(parts[0]["text"])
                                            return ""
                    except Exception:
                        pass

                # Gemini returns JSON error details; best-effort include it
                try:
                    err = await resp.json()
                except Exception:
                    err = None
                raise LLMRouterError(
                    "gemini",
                    f"API 오류: {resp.status}" + (f" ({err})" if err else ""),
                    status_code=resp.status,
                )
