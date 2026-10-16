"""Probe the running local Compose web, API, and worker health endpoints."""

from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _request(url: str, host: str | None = None):
    request = Request(url)
    if host:
        request.add_header("Host", host)
    return urlopen(request, timeout=5)


def _get_json(url: str, host: str | None = None) -> dict[str, object]:
    try:
        with _request(url, host) as response:
            if response.status != 200:
                raise RuntimeError(f"{url} returned HTTP {response.status}")
            data = json.loads(response.read())
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Health probe failed for {url}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"{url} did not return a JSON object")
    return data


def main() -> int:
    web_url = os.getenv("SMOKE_WEB_URL", "http://localhost:3000")
    api_url = os.getenv("SMOKE_API_URL", "http://localhost:8080")
    worker_url = os.getenv("SMOKE_WORKER_URL", "http://localhost:8081")
    web_host = os.getenv("SMOKE_WEB_HOST")

    try:
        with _request(web_url, web_host) as response:
            if response.status != 200:
                raise RuntimeError(f"{web_url} returned HTTP {response.status}")
            print(f"PASS web: HTTP {response.status}")

        web_health = _get_json(f"{web_url.rstrip('/')}/api/healthz", web_host)
        if web_health.get("status") != "ok":
            raise RuntimeError(f"Unexpected web proxy health response: {web_health}")
        print("PASS web-to-API proxy: status=ok")

        api_health = _get_json(f"{api_url.rstrip('/')}/readyz")
        if api_health.get("status") != "ready":
            raise RuntimeError(f"Unexpected API readiness response: {api_health}")
        print("PASS API readiness: status=ready")

        worker_health = _get_json(f"{worker_url.rstrip('/')}/health")
        if worker_health.get("status") != "ok":
            raise RuntimeError(f"Unexpected worker health response: {worker_health}")
        if worker_health.get("mode") == "placeholder":
            print("LIMITATION worker: health-only placeholder; no jobs are executed")
        else:
            print(f"PASS worker health: mode={worker_health.get('mode', 'unspecified')}")
    except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
        print(f"FAIL smoke: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
