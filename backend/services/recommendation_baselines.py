from __future__ import annotations

from typing import Any

_DEFAULT_BASELINE: dict[str, Any] = {
    "modelRouting": [
        "Gemini Flash",
        "Pollinations mistral",
        "Codex CLI (subscription)",
        "Groq fallback",
    ],
    "workflow": [
        "수집 → 분류 → 요약",
        "카드 검수",
        "템플릿 생성",
    ],
    "rules": [
        "실전 운용",
        "주의/함정",
        "깨알팁",
        "실전 사례",
    ],
    "mcp": [
        "Knowledge Sync",
        "MCP Router",
    ],
    # bump this when you change baseline semantics so signatures change deterministically
    "baselineVersion": 1,
}

_DOMAIN_BASELINES: dict[str, dict[str, Any]] = {
    "게임 클라이언트": {
        "workflow": [
            "로그/크래시 수집",
            "재현/분류",
            "핫픽스/릴리즈 하네스",
        ],
        "rules": [
            "주의/함정",
            "실전 운용",
            "아키텍처",
        ],
        "mcp": [
            "Crashlytics",
            "Release Notes",
            "Symbol/Mapping",
        ],
    },
    "게임 서버": {
        "workflow": [
            "지표/알람 수집",
            "장애 분류",
            "롤백/핫픽스",
        ],
        "rules": [
            "실전 운용",
            "주의/함정",
            "아키텍처",
        ],
        "mcp": [
            "APM",
            "Log Search",
            "Incident Timeline",
        ],
    },
    "프론트엔드": {
        "workflow": [
            "에러 바운더리/관측",
            "성능/번들 체크",
            "릴리즈/회귀 검증",
        ],
        "rules": [
            "주의/함정",
            "실전 사례",
            "깨알팁",
        ],
        "mcp": [
            "Sentry",
            "Lighthouse",
            "Bundle Analyzer",
        ],
    },
    "백엔드": {
        "workflow": [
            "health/smoke gate",
            "DB/큐/캐시 점검",
            "롤링 배포/롤백",
        ],
        "rules": [
            "실전 운용",
            "주의/함정",
            "아키텍처",
        ],
        "mcp": [
            "DB Admin",
            "Redis",
            "Job Queue",
        ],
    },
    "Unity": {
        "workflow": [
            "플랫폼별 빌드/심볼",
            "성능/메모리 점검",
            "QA/배포",
        ],
        "rules": [
            "실전 운용",
            "주의/함정",
            "깨알팁",
        ],
        "mcp": [
            "Unity Profiler",
            "Addressables",
            "IL2CPP",
        ],
    },
    "Unreal": {
        "workflow": [
            "빌드/패키징",
            "크래시/덤프",
            "QA/배포",
        ],
        "rules": [
            "실전 운용",
            "주의/함정",
            "깨알팁",
        ],
        "mcp": [
            "Unreal Insights",
            "Crash Reporter",
            "Pak/IoStore",
        ],
    },
    "로컬 LLM": {
        "modelRouting": [
            "Local vLLM",
            "Pollinations mistral",
            "Groq fallback",
        ],
        "workflow": [
            "로컬/오프라인 우선",
            "프롬프트/템플릿 재사용",
            "필요 시 클라우드 fallback",
        ],
        "rules": [
            "주의/함정",
            "깨알팁",
        ],
        "mcp": [
            "vLLM",
            "Vector Cache",
        ],
    },
    "Agent/MCP": {
        "workflow": [
            "권한/툴 제한",
            "워크트리/샌드박스",
            "리뷰/게이트",
        ],
        "rules": [
            "주의/함정",
            "아키텍처",
            "플러그인/MCP",
        ],
        "mcp": [
            "MCP Registry",
            "OAuth",
            "Tool Policy",
        ],
    },
}


def get_domain_baseline(domain: str) -> dict[str, Any]:
    base: dict[str, Any] = dict(_DEFAULT_BASELINE)
    override = _DOMAIN_BASELINES.get(domain)
    if override:
        base.update(override)
    return base


def merge_unique(items: list[str], extras: list[str], *, limit: int) -> list[str]:
    result: list[str] = []
    for value in items + extras:
        text = (value or "").strip()
        if not text or text in result:
            continue
        result.append(text)
        if len(result) >= limit:
            break
    return result
