from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from backend.services.analyzer import ContentAnalyzer
from scripts import smoke_api


def test_assess_risk_keyword_classification() -> None:
    analyzer = ContentAnalyzer()

    assert analyzer._assess_risk("This can cause memory leak under load", "") == "high"
    assert analyzer._assess_risk("", "deprecated api warning") == "medium"
    assert analyzer._assess_risk("safe update with no special issue", "") == "low"


def test_parse_json_or_none_behavior() -> None:
    assert smoke_api._parse_json_or_none('{"ok": true}') == {"ok": True}
    assert smoke_api._parse_json_or_none("not-json") is None


def test_deep_smoke_strict_mode_requires_success(monkeypatch) -> None:
    def fake_post_json(url: str, payload: dict[str, object], *, timeout: float) -> tuple[int, str]:
        _ = (url, payload, timeout)
        return 200, '{"task_id":"t-1","deduplicated":true}'

    def fake_get(url: str, *, timeout: float) -> tuple[int, str]:
        _ = (url, timeout)
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

    assert failures
    assert "strict mode requires SUCCESS" in failures[0]
