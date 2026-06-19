#!/usr/bin/env python3
"""Cross-check a list of domains and/or IPs against the public FortiBleed datasets.

Datasets (one entry per line):
    https://github.com/kkroth0/fortibleed-dataset-lookup
    - fortibleed-public-dataset.txt   (domains)
    - fortibleed-ips.txt              (IPs)

Usage:
    python3 fortibleed_lookup.py my_targets.txt
    python3 fortibleed_lookup.py my_targets.txt --subdomains
    python3 fortibleed_lookup.py my_targets.txt --json result.json
    python3 fortibleed_lookup.py my_targets.txt --domains-db dom.txt --ips-db ips.txt

Each input line is classified as an IP or a domain and compared against the
matching dataset. Output: the entries that show up (HIT) in the datasets.
Exit code 1 if there was at least one HIT, 0 otherwise (handy in pipelines).
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import sys


def normalize_domain(raw: str) -> str:
    """Reduce a line to a comparable domain (lowercase, no scheme/port/www/path)."""
    d = raw.strip().lstrip("﻿").strip()
    if not d or d.startswith("#"):
        return ""
    if "://" in d:
        d = d.split("://", 1)[1]
    if "@" in d:
        d = d.rsplit("@", 1)[1]
    for sep in ("/", "?", "#"):
        if sep in d:
            d = d.split(sep, 1)[0]
    if ":" in d:
        d = d.split(":", 1)[0]
    d = d.strip().rstrip(".").lower()
    if d.startswith("www."):
        d = d[4:]
    return d


def normalize_ip(raw: str) -> str | None:
    """Return the canonical IP if the line is a valid IP (with or without port), else None."""
    s = raw.strip().lstrip("﻿").strip()
    if not s or s.startswith("#"):
        return None
    if "://" in s:
        s = s.split("://", 1)[1]
    # strip port from IPv4 (1.2.3.4:443) — leave raw IPv6 untouched
    if s.count(":") == 1 and "." in s:
        s = s.split(":", 1)[0]
    try:
        return str(ipaddress.ip_address(s))
    except ValueError:
        return None


def load_ips(path: str) -> set[str]:
    ips: set[str] = set()
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            n = normalize_ip(line)
            if n:
                ips.add(n)
    return ips


def load_domains(path: str) -> set[str]:
    domains: set[str] = set()
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            n = normalize_domain(line)
            if n:
                domains.add(n)
    return domains


def classify_input(path: str) -> tuple[set[str], set[str], int]:
    """Read the input and split into (ips, domains, lines_read)."""
    ips: set[str] = set()
    domains: set[str] = set()
    lines = 0
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            lines += 1
            ip = normalize_ip(line)
            if ip:
                ips.add(ip)
                continue
            dom = normalize_domain(line)
            if dom:
                domains.add(dom)
    return ips, domains, lines


def parent_domains(domain: str):
    """Yield the parent domains: a.b.c.com -> b.c.com -> c.com."""
    parts = domain.split(".")
    for i in range(len(parts) - 1):
        yield ".".join(parts[i:])


def find_default(name: str) -> str | None:
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), name),
        os.path.join(os.getcwd(), name),
        os.path.expanduser(os.path.join("~", "Downloads", name)),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Cross-check YOUR list of domains/IPs against the FortiBleed datasets.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python3 fortibleed_lookup.py example-targets.txt\n"
            "  python3 fortibleed_lookup.py my_targets.txt --subdomains\n"
            "  python3 fortibleed_lookup.py my_targets.txt -q --json out.json\n\n"
            "the positional FILE is YOUR list (one domain or IP per line).\n"
            "the FortiBleed datasets are auto-detected next to the script; only\n"
            "use --domains-db / --ips-db if they live somewhere else."
        ),
    )
    ap.add_argument("input", metavar="FILE",
                    help="Your list of domains and/or IPs to check (one per line).")
    ap.add_argument("--domains-db", dest="domains_db", default=None, metavar="PATH",
                    help="Path to the domain dataset (default: fortibleed-public-dataset.txt next to the script).")
    ap.add_argument("--ips-db", dest="ips_db", default=None, metavar="PATH",
                    help="Path to the IP dataset (default: fortibleed-ips.txt next to the script).")
    ap.add_argument("--subdomains", action="store_true",
                    help="Count a HIT if a parent domain is in the dataset (vpn.acme.com matches acme.com).")
    ap.add_argument("--json", metavar="FILE", help="Write the full result to JSON.")
    ap.add_argument("-q", "--quiet", action="store_true", help="Show only the HITs.")
    args = ap.parse_args()

    if not os.path.isfile(args.input):
        print(f"ERROR: input file not found: {args.input}", file=sys.stderr)
        return 2

    in_ips, in_domains, in_lines = classify_input(args.input)

    domain_dataset_path = args.domains_db or find_default("fortibleed-public-dataset.txt")
    ip_dataset_path = args.ips_db or find_default("fortibleed-ips.txt")

    domain_dataset = load_domains(domain_dataset_path) if domain_dataset_path else set()
    ip_dataset = load_ips(ip_dataset_path) if ip_dataset_path else set()

    # domain cross-check
    dom_hits = []   # (queried, matched)
    for d in sorted(in_domains):
        if d in domain_dataset:
            dom_hits.append((d, d))
        elif args.subdomains:
            matched = next((p for p in parent_domains(d) if p in domain_dataset), None)
            if matched:
                dom_hits.append((d, matched))

    # IP cross-check
    ip_hits = sorted(ip for ip in in_ips if ip in ip_dataset)

    if not args.quiet:
        print(f"Domain dataset: {domain_dataset_path or '(missing)'}  ({len(domain_dataset)} unique)")
        print(f"IP dataset:     {ip_dataset_path or '(missing)'}  ({len(ip_dataset)} unique)")
        print(f"Input:          {args.input}  ({len(in_domains)} domains + {len(in_ips)} IPs / {in_lines} lines)")
        print(f"Subdomain mode: {'on' if args.subdomains else 'off'}")
        print("-" * 64)

    total_hits = len(dom_hits) + len(ip_hits)

    if dom_hits:
        print(f"[!] {len(dom_hits)} domain(s) in dataset:")
        for queried, matched in dom_hits:
            print(f"    {queried}" if queried == matched else f"    {queried}  (via {matched})")
    if ip_hits:
        print(f"[!] {len(ip_hits)} IP(s) in dataset:")
        for ip in ip_hits:
            print(f"    {ip}")
    if total_hits == 0:
        print("[ok] No entry is in the datasets.")

    if not args.quiet:
        miss_dom = len(in_domains) - len(dom_hits)
        miss_ip = len(in_ips) - len(ip_hits)
        if miss_dom or miss_ip:
            print(f"\n[-] No match: {miss_dom} domain(s), {miss_ip} IP(s).")

    if args.json:
        payload = {
            "domain_dataset": domain_dataset_path,
            "domain_dataset_count": len(domain_dataset),
            "ip_dataset": ip_dataset_path,
            "ip_dataset_count": len(ip_dataset),
            "input": args.input,
            "input_domains": len(in_domains),
            "input_ips": len(in_ips),
            "subdomain_match": args.subdomains,
            "domain_hits": [{"queried": q, "matched": m} for q, m in dom_hits],
            "ip_hits": ip_hits,
        }
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        if not args.quiet:
            print(f"\nJSON written to {args.json}")

    return 1 if total_hits else 0


if __name__ == "__main__":
    sys.exit(main())
