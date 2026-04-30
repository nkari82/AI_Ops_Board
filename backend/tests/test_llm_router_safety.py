from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.services.llm_router import LLMRouter, LLMRouterError


class TestLLMRouterErrorHandling:
    """Verify error strings are raised, not returned as data."""

    @pytest.mark.asyncio
    async def test_provider_error_raises_after_failover_exhausted(self):
        """CRITICAL: provider errors must surface when all candidates fail."""
        router = LLMRouter()

        async def always_fail(_provider, _prompt, _max_tokens, _temperature):
            raise LLMRouterError("gemini", "API 오류: 401", 401)

        with patch.object(router, "_call_provider", side_effect=always_fail):
            with pytest.raises(LLMRouterError):
                await router.generate("test prompt", provider="gemini")

    @pytest.mark.asyncio
    async def test_failover_on_error_string_triggers(self):
        """CRITICAL: Failover activates when provider returns error marker."""
        router = LLMRouter()

        call_count = 0

        async def mock_call_provider(provider, prompt, max_tokens, temperature):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise LLMRouterError("gemini", "API 오류: 429", 429)
            return "valid response"

        with patch.object(router, "_call_provider", side_effect=mock_call_provider):
            result = await router.generate("test", max_tokens=100)
            assert result == "valid response"
            assert call_count == 2  # Failover occurred

    @pytest.mark.asyncio
    async def test_no_error_string_in_final_output(self):
        """CRITICAL: Final output must not contain error markers."""
        router = LLMRouter()
        error_markers = ["API 오류", "에러", "failed", "error", "exception"]

        with patch.object(router, "_call_provider", return_value="Successfully analyzed"):
            result = await router.generate("test prompt", provider="gemini")

            for marker in error_markers:
                assert marker.lower() not in result.lower(), f"Error marker '{marker}' found in output: {result}"

    def test_failover_order_respected(self):
        """Verify failover follows configured order."""
        router = LLMRouter()
        order = router._parse_failover_order()

        assert len(order) > 0
        assert "gemini" in order or "pollinations" in order
        assert order[0] in ["gemini", "pollinations", "groq"]

    def test_failover_status_codes_configured(self):
        """Verify failover triggers on configured status codes."""
        router = LLMRouter()
        statuses = router._parse_failover_statuses()

        assert 429 in statuses
        assert 503 in statuses
        assert 504 in statuses


class TestLLMRouterQuotaHandling:
    """Verify quota exhaustion is handled correctly."""

    def test_quota_error_triggers_failover(self):
        """Verify 'quota' in error message triggers failover."""
        router = LLMRouter()
        error = LLMRouterError("gemini", "Quota exceeded", 429)

        assert router._is_failover_candidate(error)

    def test_unauthorized_triggers_failover(self):
        """Verify 401/403 trigger failover."""
        router = LLMRouter()

        error_401 = LLMRouterError("gemini", "Unauthorized", 401)
        error_403 = LLMRouterError("gemini", "Forbidden", 403)

        assert router._is_failover_candidate(error_401)
        assert router._is_failover_candidate(error_403)
