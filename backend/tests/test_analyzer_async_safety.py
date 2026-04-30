from __future__ import annotations

import asyncio

import pytest

from backend.services.analyzer import ContentAnalyzer


class TestAnalyzerAsyncSafety:
    """Verify async/sync boundaries are correctly implemented."""

    def test_assess_risk_returns_string_not_coroutine(self):
        """_assess_risk is sync and must return string immediately."""
        analyzer = ContentAnalyzer()

        result = analyzer._assess_risk("memory leak under load", "")

        assert isinstance(result, str), f"Expected str, got {type(result)}"
        assert result in {"high", "medium", "low"}, f"Invalid risk level: {result}"

    @pytest.mark.asyncio
    async def test_analyze_risk_field_is_string(self):
        """analyze() result must have string risk, not coroutine."""
        analyzer = ContentAnalyzer()

        result = await analyzer.analyze(
            "This can cause memory leak under load",
            "http://example.com",
        )

        assert "risk" in result
        assert isinstance(result["risk"], str), f"Risk field is {type(result['risk'])}, expected str"
        assert result["risk"] in {"high", "medium", "low"}

    def test_assess_risk_keyword_classification(self):
        """Verify risk classification by keywords."""
        analyzer = ContentAnalyzer()

        high_risk = analyzer._assess_risk("memory leak under load", "")
        assert high_risk == "high"

        medium_risk = analyzer._assess_risk("", "deprecated api warning")
        assert medium_risk == "medium"

        low_risk = analyzer._assess_risk("safe update with no special issue", "")
        assert low_risk == "low"

    @pytest.mark.asyncio
    async def test_no_coroutine_objects_in_output(self):
        """Verify no coroutine objects leak into output payload."""
        analyzer = ContentAnalyzer()

        result = await analyzer.analyze(
            "Test content with potential issues",
            "http://example.com",
        )

        for key, value in result.items():
            assert not asyncio.iscoroutine(value), f"Field '{key}' contains coroutine object"

    @pytest.mark.asyncio
    async def test_concurrent_analyze_calls(self):
        """Verify concurrent analyze calls work correctly."""
        analyzer = ContentAnalyzer()

        tasks = [
            analyzer.analyze(f"Content {i}", f"http://example.com/{i}")
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for result in results:
            assert isinstance(result["risk"], str)
            assert result["risk"] in {"high", "medium", "low"}
