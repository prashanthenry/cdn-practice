#!/usr/bin/env python3
"""Check that DNS for your hostnames looks right.

For proxied (CDN) records, public DNS returns the CDN's anycast IPs, not your
origin - that proves traffic goes through the edge. With Akamai you'd instead
check the CNAME chain ends in .edgekey.net / .edgesuite.net.

Usage:
    python scripts/dns_check.py example.com www.example.com origin.example.com
"""
from __future__ import annotations

import sys

import dns.resolver  # pip install dnspython


def describe(hostname: str) -> None:
    print(f"\n{hostname}")
    for rtype in ("CNAME", "A", "AAAA"):
        try:
            answers = dns.resolver.resolve(hostname, rtype)
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            continue
        except dns.exception.DNSException as exc:
            print(f"  {rtype:5} error: {exc}")
            continue
        ttl = answers.rrset.ttl
        for rdata in answers:
            print(f"  {rtype:5} {rdata.to_text():40} ttl={ttl}")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    for host in sys.argv[1:]:
        describe(host)
    return 0


if __name__ == "__main__":
    sys.exit(main())
