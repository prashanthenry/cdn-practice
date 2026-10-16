#!/usr/bin/env python3
"""Post-deployment validation for the CDN configuration.

Reads a list of checks from a JSON file, sends real HTTP requests, and verifies
status codes, redirect targets, cache behavior and response headers.

Exit code 0 = all checks passed, 1 = at least one failed. That exit code is what
lets a CI/CD pipeline stop a bad rollout automatically.

Akamai equivalent: same script, but send the Pragma debug header
("akamai-x-cache-on, akamai-x-check-cacheable, ...") and read X-Cache /
X-Check-Cacheable instead of cf-cache-status.

Usage:
    python scripts/validate.py --config scripts/checks.json --domain example.com
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field

import requests

CACHE_HIT_VALUES = {"HIT", "STALE", "REVALIDATED", "UPDATING"}


@dataclass
class Result:
    url: str
    passed: bool
    status: int | None = None
    cache_status: str | None = None
    problems: list[str] = field(default_factory=list)


def fetch(session: requests.Session, url: str, timeout: float = 10.0,
          retries: int = 3) -> requests.Response:
    """GET without following redirects, retrying on network errors."""
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return session.get(url, allow_redirects=False, timeout=timeout)
        except requests.RequestException as exc:
            last_error = exc
            time.sleep(2 ** (attempt - 1))  # 1s, 2s, 4s backoff
    raise RuntimeError(f"request failed after {retries} attempts: {last_error}")


def evaluate(check: dict, status: int, headers: dict[str, str]) -> list[str]:
    """Compare one response against one check. Returns a list of problems (empty = pass).

    Kept free of network calls so it can be unit tested.
    """
    problems: list[str] = []
    h = {k.lower(): v for k, v in headers.items()}

    expected_status = check.get("status")
    if expected_status is not None and status != expected_status:
        problems.append(f"status {status}, expected {expected_status}")

    expected_location = check.get("location")
    if expected_location is not None and h.get("location") != expected_location:
        problems.append(f"Location {h.get('location')!r}, expected {expected_location!r}")

    cache_status = h.get("cf-cache-status", "").upper()
    if check.get("expect_cache_hit") and cache_status not in CACHE_HIT_VALUES:
        problems.append(f"cf-cache-status {cache_status or 'missing'}, expected a cache HIT")
    if check.get("expect_not_cached") and cache_status in CACHE_HIT_VALUES:
        problems.append(f"cf-cache-status {cache_status}, expected the response NOT to be cached")

    for name, expected in check.get("headers", {}).items():
        actual = h.get(name.lower())
        if actual is None:
            problems.append(f"missing header {name}")
        elif expected != "*" and actual != expected:
            problems.append(f"header {name}={actual!r}, expected {expected!r}")

    return problems


def run(checks: list[dict], domain: str) -> list[Result]:
    session = requests.Session()
    session.headers["User-Agent"] = "cdn-validate/1.0"
    results: list[Result] = []

    for check in checks:
        url = check["url"].replace("{domain}", domain)
        if check.get("location"):
            check = {**check, "location": check["location"].replace("{domain}", domain)}
        try:
            # To test a cache HIT, warm the cache with a first request.
            if check.get("expect_cache_hit"):
                fetch(session, url)
            resp = fetch(session, url)
        except RuntimeError as exc:
            results.append(Result(url, False, problems=[str(exc)]))
            continue

        problems = evaluate(check, resp.status_code, dict(resp.headers))
        results.append(Result(url, not problems, resp.status_code,
                              resp.headers.get("cf-cache-status"), problems))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CDN behavior after a deployment")
    parser.add_argument("--config", default="scripts/checks.json")
    parser.add_argument("--domain", required=True, help="apex domain, e.g. example.com")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        checks = json.load(f)

    results = run(checks, args.domain)
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        print(f"{mark}  {r.url}  status={r.status}  cache={r.cache_status}")
        for p in r.problems:
            print(f"        - {p}")

    failed = sum(not r.passed for r in results)
    print(f"\n{len(results) - failed}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
