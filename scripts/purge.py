#!/usr/bin/env python3
"""Purge cached content through the Cloudflare API.

Akamai equivalent: Fast Purge (CCU v3) -
    POST /ccu/v3/invalidate/url/production  {"objects": [...]}
signed with EdgeGrid auth instead of a bearer token.

Usage:
    export CLOUDFLARE_API_TOKEN=...   # token needs Zone > Cache Purge permission
    python scripts/purge.py --zone-id <ZONE_ID> --url https://www.example.com/static/style.css
    python scripts/purge.py --zone-id <ZONE_ID> --everything
"""
from __future__ import annotations

import argparse
import os
import sys

import requests

API = "https://api.cloudflare.com/client/v4"
MAX_URLS_PER_CALL = 30  # free-plan limit per request; batch larger lists


def purge(zone_id: str, token: str, urls: list[str] | None = None,
          everything: bool = False) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    endpoint = f"{API}/zones/{zone_id}/purge_cache"

    if everything:
        payloads = [{"purge_everything": True}]
    else:
        payloads = [{"files": urls[i:i + MAX_URLS_PER_CALL]}
                    for i in range(0, len(urls), MAX_URLS_PER_CALL)]

    for body in payloads:
        resp = requests.post(endpoint, json=body, headers=headers, timeout=30)
        data = resp.json()
        if not resp.ok or not data.get("success"):
            raise RuntimeError(f"purge failed ({resp.status_code}): {data.get('errors')}")
        print(f"Purged {body.get('files', 'everything')} -> id {data['result']['id']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Purge CDN cache")
    parser.add_argument("--zone-id", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", action="append", help="URL to purge (repeatable)")
    group.add_argument("--everything", action="store_true")
    args = parser.parse_args()

    token = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not token:
        print("Set CLOUDFLARE_API_TOKEN first", file=sys.stderr)
        return 2

    try:
        purge(args.zone_id, token, urls=args.url, everything=args.everything)
    except (RuntimeError, requests.RequestException) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
