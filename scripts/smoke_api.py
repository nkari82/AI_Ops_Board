from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


TERMINAL_TASK_STATUSES = {"SUCCESS", "FAILURE", "REVOKED"}


@dataclass
class SmokeCase:
    name: str
    path: str
    expected_statuses: tuple[int, ...] = (200,)


def _base_url() -> str:
    return (os.getenv("API_BASE_URL") or os.getenv("BACKEND_BASE_URL") or "http://localhost:8005").rstrip("/")


def _request_get(url: str, timeout: float) -> tuple[int, str]:
    req = urllib.request.Request(url=url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310 - internal smoke usage
        return int(resp.status), resp.read().decode("utf-8", errors="replace")


def _request_post_json(url: str, payload: dict[str, Any], timeout: float) -> tuple[int, str]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        method="POST",
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310 - internal smoke usage
        return int(resp.status), resp.read().decode("utf-8", errors="replace")


def _trim(text: str, limit: int = 240) -> str:
    stripped = " ".join((text or "").split())
    return stripped if len(stripped) <= limit else stripped[: limit - 3] + "..."


def _parse_json_or_none(text: str) -> Any | None:
    try:
        return json.loads(text)
    except Exception:
        return None


def _extract_task_status(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    status = payload.get("status")
    return status if isinstance(status, str) else None


def run_basic_smoke(base: str, timeout: float) -> list[str]:
    cases = [
        SmokeCase("health_basic", "/health"),
        SmokeCase("health_detailed", "/api/health/detailed"),
        SmokeCase("admin_metrics", "/api/admin/metrics"),
        SmokeCase("admin_errors", "/api/admin/errors"),
        SmokeCase("recommendations", "/api/recommendations"),
    ]

    failures: list[str] = []
    for case in cases:
        url = f"{base}{case.path}"
        try:
            status, body = _request_get(url, timeout=timeout)
            if status not in case.expected_statuses:
                failures.append(
                    f"[{case.name}] unexpected status={status}, expected={case.expected_statuses}, body={_trim(body)}"
                )
                print(f"[FAIL] {case.name}: status={status}")
                continue

            parsed = _parse_json_or_none(body)
            if parsed is None:
                failures.append(f"[{case.name}] response is not valid JSON: {_trim(body)}")
                print(f"[FAIL] {case.name}: invalid json")
                continue

            print(f"[PASS] {case.name}: status={status}")

        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
            failures.append(f"[{case.name}] http error status={e.code}, body={_trim(body)}")
            print(f"[FAIL] {case.name}: http {e.code}")
        except Exception as e:
            failures.append(f"[{case.name}] request failed: {e}")
            print(f"[FAIL] {case.name}: exception")

    return failures


def run_youtube_lifecycle_smoke(base: str, timeout: float, query: str, max_results: int, pages: int) -> list[str]:
    failures: list[str] = []
    print("\n=== Deep Smoke: YouTube lifecycle ===")

    search_url = f"{base}/api/crawl/youtube/search"
    payload = {"query": query, "max_results": max_results, "pages": pages}

    try:
        status, body = _request_post_json(search_url, payload, timeout=timeout)
        if status != 200:
            failures.append(f"[youtube_search_start] unexpected status={status}, body={_trim(body)}")
            print(f"[FAIL] youtube_search_start: status={status}")
            return failures

        parsed = _parse_json_or_none(body)
        if not isinstance(parsed, dict):
            failures.append(f"[youtube_search_start] invalid JSON body={_trim(body)}")
            print("[FAIL] youtube_search_start: invalid json")
            return failures

        task_id = parsed.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip():
            failures.append(f"[youtube_search_start] missing task_id in payload={parsed}")
            print("[FAIL] youtube_search_start: missing task_id")
            return failures

        deduplicated = bool(parsed.get("deduplicated"))
        print(f"[PASS] youtube_search_start: task_id={task_id}, deduplicated={deduplicated}")

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        if e.code == 404:
            print("[WARN] youtube_search_start: endpoint not available on current server; deep lifecycle smoke skipped")
            return failures
        failures.append(f"[youtube_search_start] http error status={e.code}, body={_trim(body)}")
        print(f"[FAIL] youtube_search_start: http {e.code}")
        return failures
    except Exception as e:
        failures.append(f"[youtube_search_start] request failed: {e}")
        print("[FAIL] youtube_search_start: exception")
        return failures

    poll_timeout = float(os.getenv("SMOKE_TASK_POLL_TIMEOUT_SECONDS") or "45")
    poll_interval = float(os.getenv("SMOKE_TASK_POLL_INTERVAL_SECONDS") or "3")
    deadline = time.monotonic() + max(5.0, poll_timeout)

    last_status: str | None = None
    while time.monotonic() < deadline:
        try:
            status_url = f"{base}/api/crawl/status/{task_id}"
            s_status, s_body = _request_get(status_url, timeout=timeout)
            if s_status != 200:
                failures.append(f"[youtube_task_poll] unexpected status={s_status}, body={_trim(s_body)}")
                print(f"[FAIL] youtube_task_poll: status={s_status}")
                return failures

            s_parsed = _parse_json_or_none(s_body)
            if not isinstance(s_parsed, dict):
                failures.append(f"[youtube_task_poll] invalid JSON body={_trim(s_body)}")
                print("[FAIL] youtube_task_poll: invalid json")
                return failures

            task_status = _extract_task_status(s_parsed)
            if not task_status:
                failures.append(f"[youtube_task_poll] missing status field payload={s_parsed}")
                print("[FAIL] youtube_task_poll: missing status")
                return failures

            last_status = task_status
            print(f"[INFO] youtube_task_poll: status={task_status}")

            if task_status in TERMINAL_TASK_STATUSES:
                print(f"[PASS] youtube_task_terminal: status={task_status}")
                return failures

        except Exception as e:
            failures.append(f"[youtube_task_poll] exception: {e}")
            print("[FAIL] youtube_task_poll: exception")
            return failures

        time.sleep(max(0.5, poll_interval))

    failures.append(
        f"[youtube_task_poll] timeout waiting terminal status. last_status={last_status}, timeout={poll_timeout}s"
    )
    print("[FAIL] youtube_task_poll: timeout")
    return failures


def run(deep: bool, deep_only: bool, deep_query: str, deep_max_results: int, deep_pages: int) -> int:
    timeout = float(os.getenv("SMOKE_TIMEOUT_SECONDS") or "8")
    base = _base_url()

    print("=== API Smoke Check ===")
    print(f"Base URL: {base}")
    print(f"Timeout: {timeout}s")

    failures: list[str] = []

    if not deep_only:
        failures.extend(run_basic_smoke(base, timeout))

    if deep:
        failures.extend(
            run_youtube_lifecycle_smoke(
                base=base,
                timeout=timeout,
                query=deep_query,
                max_results=deep_max_results,
                pages=deep_pages,
            )
        )

    if failures:
        print("\n=== FAILURES ===")
        for item in failures:
            print(f"- {item}")
        print("\nResult: FAILED")
        return 1

    print("\nResult: PASSED")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Ops Board API smoke tests")
    parser.add_argument("--deep", action="store_true", help="Run deep smoke including YouTube task lifecycle")
    parser.add_argument("--deep-only", action="store_true", help="Run only deep lifecycle checks (skip baseline GET smoke)")
    parser.add_argument("--query", default=os.getenv("SMOKE_YT_QUERY") or "ai ops automation", help="YouTube deep smoke query")
    parser.add_argument("--max-results", type=int, default=int(os.getenv("SMOKE_YT_MAX_RESULTS") or "2"))
    parser.add_argument("--pages", type=int, default=int(os.getenv("SMOKE_YT_PAGES") or "1"))
    args = parser.parse_args()

    return run(
        deep=bool(args.deep),
        deep_only=bool(args.deep_only),
        deep_query=(args.query or "ai ops automation").strip(),
        deep_max_results=max(1, min(5, int(args.max_results))),
        deep_pages=max(1, min(2, int(args.pages))),
    )


if __name__ == "__main__":
    sys.exit(main())
