#!/usr/bin/env python3
"""Cruza uma lista de domínios e/ou IPs contra os datasets públicos do FortiBleed.

Datasets (uma entrada por linha):
    https://github.com/kkroth0/fortibleed-dataset-lookup
    - fortibleed-public-dataset.txt   (domínios)
    - fortibleed-ips.txt              (IPs)

Uso:
    python3 fortibleed_lookup.py meus_alvos.txt
    python3 fortibleed_lookup.py meus_alvos.txt --subdomains
    python3 fortibleed_lookup.py meus_alvos.txt --json resultado.json
    python3 fortibleed_lookup.py meus_alvos.txt --domains dom.txt --ips ips.txt

Cada linha da entrada é classificada como IP ou domínio e comparada contra o
dataset correspondente. Saída: as entradas que aparecem (HIT) nos datasets.
Código de saída 1 se houve pelo menos um HIT, 0 caso contrário (útil em pipelines).
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import sys


def normalize_domain(raw: str) -> str:
    """Reduz uma linha a um domínio comparável (minúsculo, sem esquema/porta/www/path)."""
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
    """Retorna o IP canônico se a linha for um IP válido (com ou sem porta), senão None."""
    s = raw.strip().lstrip("﻿").strip()
    if not s or s.startswith("#"):
        return None
    if "://" in s:
        s = s.split("://", 1)[1]
    # remove porta de IPv4 (1.2.3.4:443) — não mexe em IPv6 cru
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
    """Lê a entrada e separa em (ips, domínios, linhas_lidas)."""
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
    """Gera os domínios-pai: a.b.c.com -> b.c.com -> c.com."""
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
        description="Cruza a SUA lista de domínios/IPs contra os datasets FortiBleed.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "exemplos:\n"
            "  python3 fortibleed_lookup.py alvos-exemplo.txt\n"
            "  python3 fortibleed_lookup.py meus_alvos.txt --subdomains\n"
            "  python3 fortibleed_lookup.py meus_alvos.txt -q --json saida.json\n\n"
            "o ARQUIVO posicional é a SUA lista (um domínio ou IP por linha).\n"
            "os datasets do FortiBleed são detectados automaticamente ao lado do\n"
            "script; só use --domains-db / --ips-db se eles estiverem em outro lugar."
        ),
    )
    ap.add_argument("input", metavar="ARQUIVO",
                    help="Sua lista de domínios e/ou IPs a verificar (um por linha).")
    ap.add_argument("--domains-db", dest="domains_db", default=None, metavar="PATH",
                    help="Caminho do dataset de domínios (default: fortibleed-public-dataset.txt ao lado do script).")
    ap.add_argument("--ips-db", dest="ips_db", default=None, metavar="PATH",
                    help="Caminho do dataset de IPs (default: fortibleed-ips.txt ao lado do script).")
    ap.add_argument("--subdomains", action="store_true",
                    help="Conta HIT se um domínio-pai estiver no dataset (vpn.acme.com casa acme.com).")
    ap.add_argument("--json", metavar="ARQUIVO", help="Grava o resultado completo em JSON.")
    ap.add_argument("-q", "--quiet", action="store_true", help="Mostra só os HITs.")
    args = ap.parse_args()

    if not os.path.isfile(args.input):
        print(f"ERRO: arquivo de entrada não encontrado: {args.input}", file=sys.stderr)
        return 2

    in_ips, in_domains, in_lines = classify_input(args.input)

    domain_dataset_path = args.domains_db or find_default("fortibleed-public-dataset.txt")
    ip_dataset_path = args.ips_db or find_default("fortibleed-ips.txt")

    domain_dataset = load_domains(domain_dataset_path) if domain_dataset_path else set()
    ip_dataset = load_ips(ip_dataset_path) if ip_dataset_path else set()

    # cruzamento de domínios
    dom_hits = []   # (consultado, casou)
    for d in sorted(in_domains):
        if d in domain_dataset:
            dom_hits.append((d, d))
        elif args.subdomains:
            matched = next((p for p in parent_domains(d) if p in domain_dataset), None)
            if matched:
                dom_hits.append((d, matched))

    # cruzamento de IPs
    ip_hits = sorted(ip for ip in in_ips if ip in ip_dataset)

    if not args.quiet:
        print(f"Dataset domínios: {domain_dataset_path or '(ausente)'}  ({len(domain_dataset)} únicos)")
        print(f"Dataset IPs:      {ip_dataset_path or '(ausente)'}  ({len(ip_dataset)} únicos)")
        print(f"Entrada:          {args.input}  ({len(in_domains)} domínios + {len(in_ips)} IPs / {in_lines} linhas)")
        print(f"Modo subdomínio:  {'on' if args.subdomains else 'off'}")
        print("-" * 64)

    total_hits = len(dom_hits) + len(ip_hits)

    if dom_hits:
        print(f"[!] {len(dom_hits)} domínio(s) no dataset:")
        for queried, matched in dom_hits:
            print(f"    {queried}" if queried == matched else f"    {queried}  (via {matched})")
    if ip_hits:
        print(f"[!] {len(ip_hits)} IP(s) no dataset:")
        for ip in ip_hits:
            print(f"    {ip}")
    if total_hits == 0:
        print("[ok] Nenhuma entrada está nos datasets.")

    if not args.quiet:
        miss_dom = len(in_domains) - len(dom_hits)
        miss_ip = len(in_ips) - len(ip_hits)
        if miss_dom or miss_ip:
            print(f"\n[-] Sem correspondência: {miss_dom} domínio(s), {miss_ip} IP(s).")

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
            print(f"\nJSON gravado em {args.json}")

    return 1 if total_hits else 0


if __name__ == "__main__":
    sys.exit(main())
