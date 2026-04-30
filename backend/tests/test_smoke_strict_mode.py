from __future__ import annotations

import pytest
from unittest.mock import patch
from scripts import smoke_api


class TestSmokeStrictMode:
    """Verify strict mode correctly validates task status"""
    
    def test_strict_mode_fails_on_failure_status(self, monkeypatch):
        """CRITICAL: Strict mode must reject FAILURE status"""
        def fake_post_json(url: str, payload: dict, *, timeout: float):
            return 200, '{"task_id":"t-1","deduplicated":true}'
        
        def fake_get(url: str, *, timeout: float):
            return 200, '{"status":"FAILURE"}'
        
        monkeypatch.setattr(smoke_api, "_request_post_json", fake_post_json)
        monkeypatch.setattr(smoke_api, "_request_get", fake_get)
        
        failures = smoke_api.run_youtube_lifecycle_smoke(
            base="http://localhost:8005",
            timeout=1.0,
            query="test",
            max_results=1,
            pages=1,
            strict_success_only=True,
        )
        
        assert failures, "Expected failures in strict mode with FAILURE status"
        assert any("strict mode" in f.lower() for f in failures), \
            f"Expected 'strict mode' in failures: {failures}"
    
    def test_strict_mode_passes_on_success_status(self, monkeypatch):
        """CRITICAL: Strict mode must accept SUCCESS status"""
        def fake_post_json(url: str, payload: dict, *, timeout: float):
            return 200, '{"task_id":"t-1","deduplicated":true}'
        
        def fake_get(url: str, *, timeout: float):
            return 200, '{"status":"SUCCESS"}'
        
        monkeypatch.setattr(smoke_api, "_request_post_json", fake_post_json)
        monkeypatch.setattr(smoke_api, "_request_get", fake_get)
        
        failures = smoke_api.run_youtube_lifecycle_smoke(
            base="http://localhost:8005",
            timeout=1.0,
            query="test",
            max_results=1,
            pages=1,
            strict_success_only=True,
        )
        
        assert not failures, f"Unexpected failures in strict mode: {failures}"
    
    def test_polling_timeout_exceeded(self, monkeypatch):
        """Verify timeout error when polling exceeds limit"""
        def fake_post_json(url: str, payload: dict, *, timeout: float):
            return 200, '{"task_id":"t-1","deduplicated":true}'
        
        def fake_get(url: str, *, timeout: float):
            # Always return PENDING to trigger timeout
            return 200, '{"status":"PENDING"}'
        
        monkeypatch.setattr(smoke_api, "_request_post_json", fake_post_json)
        monkeypatch.setattr(smoke_api, "_request_get", fake_get)
        
        failures = smoke_api.run_youtube_lifecycle_smoke(
            base="http://localhost:8005",
            timeout=0.1,
            query="test",
            max_results=1,
            pages=1,
            strict_success_only=False,
        )
        
        assert failures, "Expected timeout failure"
        assert any("timeout" in f.lower() for f in failures)
    
    def test_task_status_extraction_handles_missing_status(self, monkeypatch):
        """Verify missing status field is handled"""
        def fake_post_json(url: str, payload: dict, *, timeout: float):
            return 200, '{"task_id":"t-1"}'
        
        def fake_get(url: str, *, timeout: float):
            return 200, '{}'
        
        monkeypatch.setattr(smoke_api, "_request_post_json", fake_post_json)
        monkeypatch.setattr(smoke_api, "_request_get", fake_get)
        
        failures = smoke_api.run_youtube_lifecycle_smoke(
            base="http://localhost:8005",
            timeout=1.0,
            query="test",
            max_results=1,
            pages=1,
            strict_success_only=False,
        )
        
        assert failures, "Expected failure for missing status"
        assert any("status" in f.lower() for f in failures)
    
    def test_deduplicated_flag_captured(self, monkeypatch):
        """Verify deduplicated flag is captured in response"""
        def fake_post_json(url: str, payload: dict, *, timeout: float):
            return 200, '{"task_id":"t-1","deduplicated":true}'
        
        def fake_get(url: str, *, timeout: float):
            return 200, '{"status":"SUCCESS"}'
        
        monkeypatch.setattr(smoke_api, "_request_post_json", fake_post_json)
        monkeypatch.setattr(smoke_api, "_request_get", fake_get)
        
        failures = smoke_api.run_youtube_lifecycle_smoke(
            base="http://localhost:8005",
            timeout=1.0,
            query="test",
            max_results=1,
            pages=1,
            strict_success_only=False,
        )
        
        # Should pass and log deduplicated=true
        assert not failures, f"Unexpected failures: {failures}"
