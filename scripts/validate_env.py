from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
ENV_EXAMPLE_PATH = ROOT / ".env.example"

ALLOWED_PROVIDERS = {"gemini", "pollinations", "groq", "openrouter", "huggingface", "vllm"}
REQUIRED_BASE = [
    "DATABASE_URL",
    "CRAWL_ENABLED_SOURCES",
    "LLM_FAILOVER_ENABLED",
    "LLM_FAILOVER_ORDER",
    "LLM_FAILOVER_ON_STATUS",
    "MIN_CLASSIFIABLE_CONTENT_LEN",
    "MIN_CLASSIFIABLE_SIGNAL_LEN",
    "YOUTUBE_SEARCH_ENABLED",
    "YOUTUBE_SEARCH_MAX_RESULTS",
    "YOUTUBE_SEARCH_MAX_PAGES",
    "YOUTUBE_SEARCH_DEDUP_TTL_SECONDS",
    "YOUTUBE_SEARCH_RATE_LIMIT_WINDOW_SECONDS",
    "YOUTUBE_SEARCH_RATE_LIMIT_MAX_REQUESTS",
    "REDDIT_USE_RSS",
    "REDDIT_RSS_FEEDS",
    "REDDIT_RSS_MAX_CONTENT_CHUNKS",
    "REDDIT_RSS_MAX_LINKS_PER_ENTRY",
    "REDDIT_RSS_FETCH_LINK_CONTENT",
    "REDDIT_RSS_LINK_TIMEOUT_SECONDS",
    "REDDIT_RSS_MAX_LINK_CONTENT_CHARS",
    "REDDIT_RSS_SELFTEXT_MAX_CHARS",
    "REDDIT_RSS_LINK_MIN_TEXT_CHARS",
    "REDDIT_RSS_LINK_MAX_NOISE_RATIO",
    "REDDIT_RSS_LINK_MAX_SAME_LINE_RATIO",
]
REQUIRED_PROVIDER_BASE = [
    "GEMINI_MODEL",
    "GEMINI_BASE_URL",
    "POLLINATIONS_TEXT_MODEL",
    "POLLINATIONS_BASE_URL",
]


def parse_env_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def get_value(key: str, env_map: dict[str, str]) -> str:
    return os.getenv(key, env_map.get(key, "")).strip()


def as_bool(value: str, default: bool = False) -> bool:
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "y", "on"}


def as_int(value: str, default: int) -> int:
    try:
        return int(value)
    except ValueError:
        return default


def as_float(value: str, default: float) -> float:
    try:
        return float(value)
    except ValueError:
        return default


def validate() -> tuple[list[str], list[str]]:
    example_map = parse_env_file(ENV_EXAMPLE_PATH)
    local_map = parse_env_file(ENV_PATH)
    # precedence: OS env > .env > .env.example
    env_map = {**example_map, **local_map}
    errors: list[str] = []
    warnings: list[str] = []

    for key in REQUIRED_BASE + REQUIRED_PROVIDER_BASE:
        if not get_value(key, env_map):
            errors.append(f"Missing required env: {key}")

    database_url = get_value("DATABASE_URL", env_map)
    if database_url and "postgresql+asyncpg://" not in database_url:
        warnings.append("DATABASE_URL should typically use postgresql+asyncpg:// for backend async engine")

    min_content = as_int(get_value("MIN_CLASSIFIABLE_CONTENT_LEN", env_map), -1)
    min_signal = as_int(get_value("MIN_CLASSIFIABLE_SIGNAL_LEN", env_map), -1)
    youtube_search_max_results = as_int(get_value("YOUTUBE_SEARCH_MAX_RESULTS", env_map), -1)
    youtube_search_max_pages = as_int(get_value("YOUTUBE_SEARCH_MAX_PAGES", env_map), -1)
    youtube_search_dedup_ttl = as_int(get_value("YOUTUBE_SEARCH_DEDUP_TTL_SECONDS", env_map), -1)
    youtube_search_rate_window = as_int(get_value("YOUTUBE_SEARCH_RATE_LIMIT_WINDOW_SECONDS", env_map), -1)
    youtube_search_rate_max = as_int(get_value("YOUTUBE_SEARCH_RATE_LIMIT_MAX_REQUESTS", env_map), -1)
    reddit_rss_max_chunks = as_int(get_value("REDDIT_RSS_MAX_CONTENT_CHUNKS", env_map), -1)
    reddit_rss_max_links = as_int(get_value("REDDIT_RSS_MAX_LINKS_PER_ENTRY", env_map), -1)
    reddit_rss_link_timeout = as_int(get_value("REDDIT_RSS_LINK_TIMEOUT_SECONDS", env_map), -1)
    reddit_rss_link_chars = as_int(get_value("REDDIT_RSS_MAX_LINK_CONTENT_CHARS", env_map), -1)
    reddit_rss_selftext_chars = as_int(get_value("REDDIT_RSS_SELFTEXT_MAX_CHARS", env_map), -1)
    reddit_rss_link_min_chars = as_int(get_value("REDDIT_RSS_LINK_MIN_TEXT_CHARS", env_map), -1)
    reddit_rss_link_max_noise_ratio = as_float(get_value("REDDIT_RSS_LINK_MAX_NOISE_RATIO", env_map), -1)
    reddit_rss_link_max_same_line_ratio = as_float(get_value("REDDIT_RSS_LINK_MAX_SAME_LINE_RATIO", env_map), -1)
    if min_content <= 0:
        errors.append("MIN_CLASSIFIABLE_CONTENT_LEN must be a positive integer")
    if min_signal <= 0:
        errors.append("MIN_CLASSIFIABLE_SIGNAL_LEN must be a positive integer")
    if youtube_search_max_results <= 0:
        errors.append("YOUTUBE_SEARCH_MAX_RESULTS must be a positive integer")
    if youtube_search_max_pages <= 0:
        errors.append("YOUTUBE_SEARCH_MAX_PAGES must be a positive integer")
    if youtube_search_dedup_ttl <= 0:
        errors.append("YOUTUBE_SEARCH_DEDUP_TTL_SECONDS must be a positive integer")
    if youtube_search_rate_window <= 0:
        errors.append("YOUTUBE_SEARCH_RATE_LIMIT_WINDOW_SECONDS must be a positive integer")
    if youtube_search_rate_max <= 0:
        errors.append("YOUTUBE_SEARCH_RATE_LIMIT_MAX_REQUESTS must be a positive integer")
    if reddit_rss_max_chunks <= 0:
        errors.append("REDDIT_RSS_MAX_CONTENT_CHUNKS must be a positive integer")
    if reddit_rss_max_links <= 0:
        errors.append("REDDIT_RSS_MAX_LINKS_PER_ENTRY must be a positive integer")
    if reddit_rss_link_timeout <= 0:
        errors.append("REDDIT_RSS_LINK_TIMEOUT_SECONDS must be a positive integer")
    if reddit_rss_link_chars <= 0:
        errors.append("REDDIT_RSS_MAX_LINK_CONTENT_CHARS must be a positive integer")
    if reddit_rss_selftext_chars <= 0:
        errors.append("REDDIT_RSS_SELFTEXT_MAX_CHARS must be a positive integer")
    if reddit_rss_link_min_chars <= 0:
        errors.append("REDDIT_RSS_LINK_MIN_TEXT_CHARS must be a positive integer")
    if not (0 <= reddit_rss_link_max_noise_ratio <= 1):
        errors.append("REDDIT_RSS_LINK_MAX_NOISE_RATIO must be a float between 0 and 1")
    if not (0 <= reddit_rss_link_max_same_line_ratio <= 1):
        errors.append("REDDIT_RSS_LINK_MAX_SAME_LINE_RATIO must be a float between 0 and 1")

    sources_raw = get_value("CRAWL_ENABLED_SOURCES", env_map)
    allowed_sources = {"reddit", "github", "hn", "youtube"}
    parsed_sources = {x.strip() for x in sources_raw.split(",") if x.strip()}
    if not parsed_sources:
        errors.append("CRAWL_ENABLED_SOURCES must include at least one source")
    unknown_sources = parsed_sources - allowed_sources
    if unknown_sources:
        errors.append(f"Unknown crawl sources: {', '.join(sorted(unknown_sources))}")

    failover_enabled = as_bool(get_value("LLM_FAILOVER_ENABLED", env_map), True)
    order_raw = get_value("LLM_FAILOVER_ORDER", env_map)
    order = [x.strip() for x in order_raw.split(",") if x.strip()]
    if not order:
        errors.append("LLM_FAILOVER_ORDER must not be empty")
    else:
        unknown = [p for p in order if p not in ALLOWED_PROVIDERS]
        if unknown:
            errors.append(f"LLM_FAILOVER_ORDER has unknown providers: {', '.join(unknown)}")
        if len(set(order)) != len(order):
            errors.append("LLM_FAILOVER_ORDER contains duplicate providers")

    statuses_raw = get_value("LLM_FAILOVER_ON_STATUS", env_map)
    statuses = [x.strip() for x in statuses_raw.split(",") if x.strip()]
    if not statuses:
        errors.append("LLM_FAILOVER_ON_STATUS must not be empty")
    else:
        bad_statuses = [s for s in statuses if not s.isdigit()]
        if bad_statuses:
            errors.append(f"LLM_FAILOVER_ON_STATUS must be numeric CSV, got: {', '.join(bad_statuses)}")

    has_any_provider_key = any(
        get_value(k, env_map)
        for k in [
            "GOOGLE_AI_STUDIO_KEY",
            "POLLINATIONS_API_KEY",
            "GROQ_API_KEY",
            "OPENROUTER_API_KEY",
            "HUGGINGFACE_TOKEN",
        ]
    )
    if not has_any_provider_key:
        warnings.append("No provider API key configured. LLM endpoints will likely fail.")

    youtube_allow_all = as_bool(get_value("YOUTUBE_ALLOW_ALL_WHEN_TARGETS_EMPTY", env_map), False)
    youtube_targets = get_value("YOUTUBE_TARGET_URLS", env_map)
    if not youtube_allow_all and not youtube_targets:
        warnings.append(
            "YOUTUBE_TARGET_URLS is empty while strict mode is enabled. /api/crawl/youtube will be blocked (expected strict behavior)."
        )

    if failover_enabled and order and order[0] == "vllm" and not get_value("VLLM_ENDPOINT", env_map):
        warnings.append("vLLM is first in failover order but VLLM_ENDPOINT is not configured")

    return errors, warnings


def main() -> int:
    if not ENV_EXAMPLE_PATH.exists():
        print("[ERROR] .env.example file not found at project root")
        return 2

    if not ENV_PATH.exists():
        print("[WARN] .env file not found. Using .env.example defaults only.")

    errors, warnings = validate()

    print("=== Environment Validation Report ===")
    print(f"Project root: {ROOT}")
    print(f"Env example: {ENV_EXAMPLE_PATH}")
    print(f"Env file: {ENV_PATH}")

    if warnings:
        print("\n[WARNINGS]")
        for w in warnings:
            print(f"- {w}")

    if errors:
        print("\n[ERRORS]")
        for e in errors:
            print(f"- {e}")
        print("\nResult: FAILED")
        return 1

    print("\nResult: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
